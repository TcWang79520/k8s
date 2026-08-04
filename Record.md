
# Overview

本筆記記錄 Kubernetes 學習歷程，目前包含以下章節：

- [Day 5](#day5) - Pod 與 Container 互動、Service 網路曝露
- [Day 6](#day-6) - Node 概念與 Kubernetes 內部運作
- [Day 7](#day-7) - Replication Controller 與 Pod 橫向擴展
- [Day 8](#day-8) - Replica Set 與 Deployment（Rollout / Rollback）
- [Day 9](#day-9) - Service 的類型與運作原理
- [Day 10](#day-10) - Labels、Annotations 與 nodeSelector
- [Day 11](#day-11) - Health Checks（Liveness Probe）
- [Day 12](#day-12) - Secrets（敏感資料管理）
- [Day 13](#day-13) - Demo：在 minikube 上架設 Stateless Wordpress
- [CKAD TEST](#ckad-test) - CKAD 考綱知識點與筆記進度對照

## 學習內容關鍵字

- **Metadata**：`name` / `labels` / `annotations`
- **Pod 互動方式**：`kubectl port-forward`（本機 Port 對應 Pod Port）、`kubectl exec`、`kubectl attach`
- **Service**：`kubectl expose`、`NodePort` 類型、Cluster IP、Port Mapping 架構
- **Labels 管理**：`kubectl label`、`--show-labels`
- **常用 kubectl 指令**：`get pods`、`describe pod`、`expose`、`port-forward`、`attach`、`exec`
- **Node**：`kubectl get nodes`、`kubectl describe nodes`、`Ready` / `Not Ready`
- **內部運作元件**：`kubelet`（node agent）、`kube-proxy`、`iptables`、`Load Balancer`
- **Request 流程**：Load Balancer → Node → iptables → Pod
- **Stateless vs Stateful**：無狀態 vs 有狀態應用
- **Replication Controller**：`replicas`、`selector`、Pod 自我修復、`kubectl scale`、`--cascade=false`
- **Replica Set**：`matchLabels`、`matchExpressions`（`In`/`NotIn`/`Exists`/`DoesNotExist`）
- **Deployment**：`kubectl set image`、`kubectl rollout status/history/undo`、`maxSurge`、`maxUnavailable`、zero downtime deployment
- **Service**：`ClusterIP`（預設）/ `NodePort` / `LoadBalancer`、`targetPort`、Dynamic Cluster IP、NodePort Range（30000~32767）
- **Labels / Annotations**：Labels 可被 Selector 篩選，Annotations 僅供人員備註不參與篩選
- **nodeSelector**：Pod 綁定特定 Node、`Pending` 狀態排查
- **Health Checks**：`livenessProbe`、`httpGet`（`path`/`port`）、`initialDelaySeconds`、`periodSeconds`、`successThreshold`、`failureThreshold`
- **Secrets**：`kubectl create secret generic`（`--from-file` / `--from-literal`）、YAML + base64、`secretKeyRef`（環境變數）、`volumes.secret`（掛載檔案）
- **Demo（Wordpress）**：單一 Pod 內多 container 協作（wordpress + mysql）、`localhost` 溝通、Secret 同時被兩個 container 引用


# Day5

## Metadata

Pod 的 metadata 有三種重要的 Key：`name`、`labels`、`annotations`。

## 如何與 Pod 中的 Container 互動

### 方法 1：kubectl port-forward

透過 `kubectl port-forward` 可以將 Pod 中的某個 port，與本機端的 port 做 mapping：

```bash
$ kubectl port-forward <pod> <local-port>:<pod-port>
$ kubectl port-forward my-pod 8000:3000   # 8000: 本機 Port, 3000: Pod Port
```

執行後在本機瀏覽器打開 `http://127.0.0.1:8000`，就能看到 Pod 內 API Server 回應的 `Hello World!`。

### 方法 2：建立一個 Service（NodePort）

```bash
$ kubectl expose pod my-pod --type=NodePort --name=my-pod-service
```

```
$ kubectl get service
NAME             TYPE       CLUSTER-IP      EXTERNAL-IP   PORT(S)          AGE
my-pod-service   NodePort   10.96.103.235   <none>        3000:30648/TCP   9s
```

my-pod 的 port 3000 會與 minikube-vm 上的 port 30648 做 mapping，接著可用 `minikube service` 指令快速取得 URL：`http://192.168.49.2:30648`。

**`--type=NodePort` 說明**

Kubernetes 的 Service 有幾種類型：`ClusterIP`、`NodePort`、`LoadBalancer`。`NodePort` 會在 K8s 節點（此環境為 Minikube VM）上，隨機開啟一個高位元的實體 Port（預設範圍 30000 - 32767）。

架構圖如下：

```
[Ubuntu 主機 / 瀏覽器]
         │
         │  1. 連線至 http://<minikube-ip>:31234
         ▼
 ┌──────────────────────────────────────────────┐
 │ Minikube (Node)                               │
 │   └─ Port 31234 (NodePort 隨機配發)            │
 │           │                                   │
 │           ▼                                   │
 │   ┌──────────────────────────────────────┐    │
 │   │ Service: my-pod-service               │    │
 │   └──────────────────────────────────────┘    │
 │           │                                   │
 │           ▼ (轉發流量)                         │
 │   ┌──────────────────────────────────────┐    │
 │   │ Pod: my-pod                          │    │
 │   └──────────────────────────────────────┘    │
 └──────────────────────────────────────────────┘
```

## Pod Labels 管理

新增 Pod 的 Labels：

```bash
$ kubectl label pods <pod> <label-key>=<label-value>
```

```
$ kubectl get pods --show-labels
NAME                              READY   STATUS    RESTARTS   AGE    LABELS
hello-minikube-8685946b45-74d88   1/1     Running   0          4d1h   app=hello-minikube,pod-template-hash=8685946b45
my-pod                            1/1     Running   0          10m    app=webserver

$ kubectl label pods my-pod version=latest
pod/my-pod labeled

$ kubectl get pods --show-labels
NAME                              READY   STATUS    RESTARTS   AGE    LABELS
hello-minikube-8685946b45-74d88   1/1     Running   0          4d1h   app=hello-minikube,pod-template-hash=8685946b45
my-pod                            1/1     Running   0          11m    app=webserver,version=latest
```

## 常見的 kubectl 指令

| 說明 | 指令 |
| --- | --- |
| 取得 Cluster 中所有正在運行的 Pods | `kubectl get pods` |
| 顯示所有 Pods（含未運行） | `kubectl get pods --show-all` |
| 取得某個 Pod 的詳細資料 | `kubectl describe pod <pod>` |
| 將 Pod 中指定 port expose 出來，建立新的 Service | `kubectl expose pod <pod> --port=<port> --name=<service-name>` |
| 將 Pod 中指定 port mapping 到本機端 port | `kubectl port-forward <pod> <external-port>:<pod-port>` |
| 進入 container 內部查看 logs | `kubectl attach <pod> -i` |
| 對 Pod 下一個內部指令 | `kubectl exec <pod> -- <command>`，例如 `kubectl exec my-pod -- ls /app` |


# Day 6

> 參考來源：[[Day 6] Kubernetes 的 Node 元件與內部運作概觀](https://ithelp.ithome.com.tw/articles/10193248)

## Node 是什麼

- Node 泛指實體機或虛擬機（AWS EC2、GCP Compute Engine、筆電、Raspberry Pi 等），只要裝有 Container Engine（如 Docker）並能跑起 Pod，就能加入 Kubernetes Cluster。
- 加入 Cluster 後，Kubernetes 會建立對應的 Node 物件，並檢查網路連線、Pod 是否能正常啟動；通過則狀態為 `Ready`，否則為 `Not Ready`。

```bash
$ kubectl get nodes
$ kubectl describe nodes <node-name>
```

**用 Kubernetes 管理 Node 的好處**：傳統上一台機器只跑一個服務容易浪費資源，混跑多服務又需要人工盯資源使用狀況。Kubernetes 會依 Pod 的設定檔自動決定部署到哪個 Node，達到資源調度自動化。

## Kubernetes 內部運作概觀

簡化架構重點：

- Cluster 由多個 Node 組成（Node 1 ~ Node N）。
- 每個 Node 都需跑起 Container Engine 才能運行 Pods。
- 一個 Pod 可以包含一或多個 container（例如某 Pod 內有 3 個 containers，另一 Pod 只有 1 個）。
- 每個 Node 都有自己的 `iptables`（Linux 防火牆），負責篩選連線並決定收到的 request 要轉給哪個 Pod。

### 1. 同一 Pod 內 containers 的溝通

同一個 Pod 共享網路，內部 containers 可透過 `localhost:<port>` 互相溝通，因此可把相依性高的服務（如 API service 與認證 service）放進同一個 Pod。

### 2. kubelet 與 kube-proxy

- **kubelet**：相當於 node agent，負責管理該 Node 上所有 Pods，並與 Master Node 即時溝通。
- **kube-proxy**：把該 Node 上所有 Pods 的最新狀態同步給 `iptables`（例如新 Pod 建立完成時通知 iptables，確保該 Pod 能被 Cluster 中其他物件存取）。
- **Load Balancer**：外部 request 會先送到 Load Balancer（由 Node 供應商提供，如 AWS ELB，或自架 Nginx / HAProxy），再由其決定轉發給哪個 Node。

### 3. 建立 Pod 後，Request 的完整流程

1. Master Node 指示 kubelet 建立 Pod；建立完成後 kube-proxy 通知 iptables 該 Pod 已可用。
2. 使用者 request 經 Load Balancer 決定送往哪個 Node，該 Node 再透過 iptables 決定轉給哪個 Pod。
3. 若收到 request 的 Node 沒有對應可處理的 Pod，會透過 iptables 把 request 轉給其他有對應 Pod 的 Node。

## 小結

- 關鍵元件：`Node`、`kubelet`、`kube-proxy`、`iptables`、`Load Balancer`。
- 下一篇（Day 7）主題：`Replication Controller`。

# Day 7

> 參考來源：[[Day 7] 如何擴展我的 pods?! - Replication Controller](https://ithelp.ithome.com.tw/articles/10193856)

## Stateless vs Stateful

- **Stateless**：服務的回傳結果不受時間、資料寫入、request 次數等狀態影響（例如純粹的加法函式）。Web application 應盡量設計成 stateless。
- **Stateful**：會記錄並保存資料狀態，即使服務重啟資料仍應存在（例如 MySQL、PostgreSQL，或是有計數器的函式）。
- Container 本身不會保存資料，container 消失資料就跟著消失，因此 stateful 的資料需要交給外部資源儲存。
- Scaling 分兩種：**Horizontal scaling**（增加更多機器節點分擔工作）與 **Vertical scaling**（在單一節點上增加 CPU / RAM）。

## 什麼是 Replication Controller

Replication Controller（RC）是 Kubernetes 用來管理 Pod 數量與狀態的物件，主要功能：

- 透過自己的 YAML 設定檔，指定同時要運行 `幾個相同的 Pods`。
- 當某個 Pod crash 或 failed 而終止時，RC 會自動偵測並建立新的 Pod，確保運行數量與設定值一致。
- 機器重開機時，RC 也會自動重新建立，確保 Pod 持續運行。

```yaml
apiVersion: v1
kind: ReplicationController
metadata:
  name: my-replication-controller
spec:
  replicas: 3
  selector:
    app: hello-pod-v1
  template:
    metadata:
      labels:
        app: hello-pod-v1
    spec:
      containers:
      - name: my-pod
        image: zxcvbnius/docker-demo
        ports:
        - containerPort: 3000
```

- **`spec.replicas` / `spec.selector`**：定義 Pod 數量，以及要選擇管理的 Pod 條件（labels）。
- **`spec.template`**：定義 Pod 本身的資訊，包含 labels 與要運行的 container。
- **`spec.template.metadata.labels`**：必須被包含在 `selector` 中，否則建立 RC 時會發生 error。
- **`spec.template.spec`**：定義 container 設定，與 Pod 的 YAML 檔寫法相同。

上述範例代表：確保帶有 `app=hello-pod-v1` label 的 Pod，在 Cluster 中隨時維持 3 個。

## 實作：透過 kubectl 操作 Replication Controller

```bash
# 建立前先確認 Node 是 Ready 狀態
$ kubectl get nodes

# 建立 Replication Controller
$ kubectl create -f my-replication-controller.yaml

# 查看 RC 狀態（可看到目前管理幾個 Pod）
$ kubectl get rc

# 查看 RC 建立的 Pods（名稱皆為 unique）
$ kubectl get pods

# 查看某個 Pod 詳細資料，會看到是由 RC 建立
$ kubectl describe pod <pod-name>
# Created By / Controlled By: ReplicationController/my-replication-controller
```

**Pod 自我修復（Self-healing）**：手動刪除其中一個 Pod 後，RC 會偵測到數量不足，自動建立新 Pod 補上。

```bash
$ kubectl delete pod <pod-name>
```

**調整 Pod 數量（Scaling）**：

```bash
$ kubectl scale --replicas=4 -f ./my-replication-controller.yaml
$ kubectl get rc
# DESIRED / CURRENT / READY 皆會顯示更新後的數量
```

**刪除 Replication Controller**：預設會連同其建立的 Pod 一併刪除；若想保留 Pod，可加上 `--cascade=false`：

```bash
$ kubectl delete rc <rc-name>
$ kubectl delete rc <rc-name> --cascade=false   # 保留已建立的 Pod
$ kubectl delete pods <pod> --grace-period=0 --force   # 強迫立即刪除 Pod
```

## 小結

- Replication Controller 能確保 Pod 數量與狀態符合設定，但 rollout / rollback 情境下仍需許多手動操作。
- 下一篇（Day 8）主題：`Deployment`，能大幅簡化手動操作並讓 rollout / rollback 更容易。

# Day 8

> 參考來源：[[Day 8] 還在用 Replication Controller 嗎？不妨考慮 Deployment](https://ithelp.ithome.com.tw/articles/10194152)

## Replica Set

Replica Set（RS）是進化版的 Replication Controller，最大差異在於提供**更彈性的 selector**：

- **`apiVersion`**：`kubectl` 版本 >= 1.9 用 `apps/v1`；1.9 以前用 `apps/v1beta2`（可用 `kubectl version` 查詢版本）。
- **`spec.selector.matchLabels`**：代表「等於（equivalent）」，Pod 的 labels 必須與指定值完全相同才符合條件。
- **`spec.selector.matchExpressions`**：更彈性的條件寫法，每筆條件由 `key`、`operator`、`value` 組成，`operator` 支援 `In`、`NotIn`、`Exists`、`DoesNotExist` 四種。

官方文件建議：雖然 Replica Set 提供更彈性的 selector，但**不建議**直接用 `kubectl create` 建立 Replica Set 物件，而是透過 **Deployment** 來間接建立與管理。

## 介紹 Deployment

Deployment 能幫我們做到：

- 部署一個應用服務（application）
- 協助 application 升級到特定版本（Rollout）
- 服務升級過程達到 **zero downtime deployment**（無停機服務遷移）
- 可以 **Rollback** 到先前版本

```yaml
apiVersion: apps/v1beta2 # kubectl >= 1.9.0 用 apps/v1
kind: Deployment
metadata:
  name: hello-deployment
spec:
  replicas: 3
  selector:
    matchLabels:
      app: my-deployment
  template:
    metadata:
      labels:
        app: my-deployment
    spec:
      containers:
      - name: my-pod
        image: zxcvbnius/docker-demo:latest
        ports:
        - containerPort: 3000
```

建立 Deployment 後，Deployment 會自動幫我們建立 Pod，同時也會自動建立一個 **Replica Set** 來管理這些 Pod：

```bash
$ kubectl create -f ./my-deployment.yaml

$ kubectl get rs
NAME                          DESIRED   CURRENT   READY     AGE
hello-deployment-6577d8cc46   3         3         3         22m
```

## 常用 Deployment 指令

| 指令 | 功能 |
| --- | --- |
| `kubectl get deployments` | 取得目前 Cluster 中 Deployments 的資訊 |
| `kubectl get rs` | 取得目前 Cluster 中 Replica Set 的資訊 |
| `kubectl get all` | 一次取得 Cluster 中所有已建立物件的資訊 |
| `kubectl describe deploy <name>` | 取得特定 Deployment 的詳細資料 |
| `kubectl set image deploy/<name> <container>=<image>:<version>` | 將 Deployment 管理的 Pod 升級到特定 image 版本 |
| `kubectl edit deploy <name>` | 編輯特定 Deployment 物件 |
| `kubectl rollout status deploy <name>` | 查詢目前升級狀況 |
| `kubectl rollout history deploy <name>` | 查詢過去 rollout 的歷史紀錄 |
| `kubectl rollout undo deploy <name>` | 回滾到上一個版本 |
| `kubectl rollout undo deploy <name> --to-revision=n` | 回滾到指定版本 |

## 實作：Rollout 與 Rollback

先建立 Service 讓外部能存取 web app（回傳 `Hello World!`）：

```bash
$ kubectl expose deploy hello-deployment --type=NodePort --name=my-deployment-service
$ minikube service my-deployment-service --url
```

**升級（Rollout）**：把 image 換成 v2 版本（回傳 `Hello World! v2`）：

```bash
$ kubectl set image deploy/hello-deployment my-pod=zxcvbnius/docker-demo:v2.0.0
$ kubectl rollout status deploy hello-deployment
deployment "hello-deployment" successfully rolled out
```

升級過程中，Deployment **不會直接砍掉舊 Pod**，而是另外建立新 Pod 取代舊 Pod，達到 zero downtime——升級期間 Cluster 中會同時存在新舊兩批 Pod。

**控制升級節奏**：透過 `kubectl edit deploy <name>` 可以看到 `strategy` 相關欄位：

- **`strategy.rollingUpdate.maxSurge`**：升級過程中，最多可以比原本設定的 Pod 數量多出多少（可為數字或百分比）。例如 `replicas: 3`、`maxSurge: 1`，升級中最多會多產生 1 個 Pod。
- **`strategy.rollingUpdate.maxUnavailable`**：升級過程中可容忍多少 Pod 無法使用；若 `maxSurge` 非 0，`maxUnavailable` 也不能為 0。

**紀錄升級原因**：在 `kubectl set image` 後加上 `--record`，可以把該次指令記錄到 `CHANGE-CAUSE`：

```bash
$ kubectl set image deploy/hello-deployment my-pod=zxcvbnius/docker-demo --record
$ kubectl rollout history deploy hello-deployment
REVISION  CHANGE-CAUSE
1         <none>
3         kubectl set image deploy/hello-deployment my-pod=zxcvbnius/docker-demo --record=true
4         <none>
```

**回滾（Rollback）**：

```bash
$ kubectl rollout undo deployment hello-deployment          # 回滾到上一版
$ kubectl rollout undo deploy hello-deployment --to-revision=3   # 回滾到指定版本
```

## 小結

- Replica Set 是 Replication Controller 的進化版（更彈性的 selector），但應透過 Deployment 間接管理，不直接手動建立。
- Deployment = Replica Set + Rollout/Rollback 能力，是實務上管理 Pod 的建議做法。
- 下一篇（Day 9）主題：`Service`。

# Day 9

> 參考來源：[[Day 9] 建立外部服務與 Pods 的溝通管道 - Services](https://ithelp.ithome.com.tw/articles/10194344)

## 為什麼需要 Service

Deployment 做 rollout 時，會不斷用新 Pod 取代舊 Pod（[Day 8](#day-8)），Pod 的 IP 是**動態、會消失重生**的。因此需要一個穩定的中間層，讓外部使用者或其他服務不必關心背後 Pod 是誰、有幾個、換過幾輪，永遠都能連到「目前可用的 Pod」——這就是 Service 的角色。

Service 主要提供三種存取方式：

- **ClusterIP**：Kubernetes 會分配一組虛擬 IP，讓 Cluster 內其他物件可以透過這組 IP 存取 Pod（未指定 `type` 時的預設值）。
- **NodePort**：讓 Cluster 外、但同一台 Node 上的服務，可透過 Node 的實體 port 存取 Cluster 內的 Pod。
- **LoadBalancer**：架在雲端服務（AWS、GCP 等）時可指定 `--type=LoadBalancer`，由 cloud provider 自動建立對應的 Load Balancer 來分流量給各個 Node。

## Service YAML 範例

```yaml
apiVersion: v1
kind: Service
metadata:
  name: hello-service
spec:
  type: NodePort
  ports:
  - port: 3000
    nodePort: 30390
    protocol: TCP
    targetPort: 3000
  selector:
    app: my-deployment
```

- **`spec.type`**：`ClusterIP`（預設）、`NodePort`、`LoadBalancer`。
- **`spec.ports.port`**：Service 自己（ClusterIP）對外的 port number。
- **`spec.ports.targetPort`**：實際轉發到 Pod 內部 container 的 port number。
- **`spec.ports.nodePort`**：Node 上對外開放的 port number；不指定的話 Kubernetes 會隨機分配。
- **`spec.ports.protocol`**：支援 `TCP` / `UDP`，預設 `TCP`。
- **`spec.selector`**：決定這個 Service 要把流量導向哪些 labels 符合條件的 Pod。

> ⚠️ **原文小提醒**：部落格內文寫「導向標籤為 `app=my-pod` 的 Pods」，但範例 yaml 裡 `selector` 其實是 `app: my-deployment`，兩者對不上——這應該只是原文筆誤，真正生效的是 yaml 裡的 `selector` 值，`Pod` 是否被選中永遠以 `selector` 跟 Pod 自己的 `labels` 是否相符為準，跟文字敘述無關。

## Service 存取流程圖：NodePort / port / targetPort / ClusterIP / LoadBalancer

```
                        [雲端 LoadBalancer]   ← 只有 type=LoadBalancer 才會有這一層
                                │                  （由 Cloud Provider 建立，如 AWS ELB）
                                │  統一對外入口
                                ▼
        ┌───────────────────────────────────────────────────────┐
        │ Node (VM)                                              │
        │                                                        │
        │   NodePort: 30390 ◄── 叢集外部可直接打 <NodeIP>:30390    │
        │        │              （type=NodePort 才會開這個 port）  │
        │        ▼                                                │
        │  ┌────────────────────────────────────────────────┐    │
        │  │ Service: hello-service                          │    │
        │  │   ClusterIP: 10.97.167.45                        │    │
        │  │   port: 3000  ◄── 叢集內部（其他 Pod）打這個 port   │    │
        │  └────────────────────────────────────────────────┘    │
        │        │                                                │
        │        ▼ targetPort: 3000                               │
        │        （Service 轉發流量到 Pod 實際監聽的 port）          │
        │  ┌────────────────────────────────────────────────┐    │
        │  │ Pod: my-deployment-xxxx                         │    │
        │  │   container port: 3000                          │    │
        │  └────────────────────────────────────────────────┘    │
        └───────────────────────────────────────────────────────┘
```

**存取路徑對照表**

| 存取者 | 存取方式 | 用到的 port |
| --- | --- | --- |
| Cluster 內其他 Pod | `<ClusterIP>:port` | `port`（3000） |
| Cluster 外部、同一 Node | `<NodeIP>:nodePort` | `nodePort`（30390），僅 `NodePort`/`LoadBalancer` 類型才有 |
| Cluster 外部、雲端環境 | `<LoadBalancer-IP>:port` | LoadBalancer 對外統一入口，內部仍會轉給每個 Node 的 `nodePort` |
| Service → Pod（一律自動） | 內部轉發 | `targetPort`（3000），對應 container 實際監聽的 port |

**三種 Service type 一句話差異**：

- **ClusterIP**（預設）：只給「叢集內部」互相存取，是其他兩種類型的基礎。
- **NodePort**：在 ClusterIP 之上，額外於每個 Node 開一個實體 `nodePort`（30000~32767），讓叢集外部也能連進來。
- **LoadBalancer**：在 NodePort 之上，再由 Cloud Provider 建立一個對外統一的 Load Balancer，自動把流量分散到各個 Node 的 `nodePort`，是三者中最外層、最貼近終端使用者的入口。

## 實作重點

```bash
$ kubectl create -f ./my-deployment.yaml     # 先確保有 Pod 可以被 Service 選中
$ kubectl create -f ./my-service.yaml
$ kubectl get svc                            # 或 kubectl get services
```

進到 Cluster 內部（例如用一個 alpine Pod）驗證 Service 是否正常運作：
- port 是「別人要連你（Service）打哪個 port」
- targetPort 是「你（Service）要轉給 Pod 的哪個 port」
```bash
$ kubectl run -i --tty alpine --image=alpine --restart=Never -- sh
/ # curl <cluster-ip>:3000
Hello World!
```

外部存取則可用 `minikube service` 取得對應的 NodePort URL：

```bash
$ minikube service hello-service --url
http://192.168.99.100:30390
```

**Dynamic Cluster IP**：如果刪掉 Service 再重新建立，只要沒有在 yaml 明確指定 IP，Cluster IP 每次都會被系統重新隨機分配，跟前一次不會相同：

```bash
$ kubectl delete svc/hello-service && kubectl create -f ./my-service.yaml
```

## NodePort 的限制

Service 可指定的 `nodePort` 預設範圍是 **30000 ~ 32767**。如果需要調整範圍，要在啟動 Node 時指定，以 minikube 為例：

```bash
$ minikube stop && minikube start --extra-config=apiserver.ServiceNodePortRange=1-50000
```

啟動後即可用 `kubectl edit svc/<name>` 把既有 Service 的 `nodePort` 改到新範圍內的值。

> ⚠️ **原文另一處疑似筆誤**：原文寫 nodePort 預設範圍是「3000~32767」，但根據 Kubernetes 官方文件與 [Day 5](#day5) 筆記中的紀錄，正確預設範圍應該是 **30000～32767**（少打一個 0），這裡以正確數字為準。

## 我的想法

- Service 的本質是「把 Pod 的動態性，轉換成一個穩定的存取入口」，這跟 [Day 6](#day-6) 提到的 `kube-proxy` 持續把最新的 Pod 清單同步給 `iptables` 是同一件事的兩面：Service/Selector 決定「誰是合法後端」，`kube-proxy`/`iptables` 負責把新連線動態導向這些後端。
- 也因此可以理解，前面在 [Day 8](#day-8) 討論過的「rollout 後網頁還是舊內容」情境：只要 Service 的 `selector` 沒變，Service 這一層的角色從頭到尾沒變過——真正變動的是 `iptables` 背後那份「目前有效 Pod」清單，以及既有 TCP 連線是否被沿用。
- Cluster IP 是動態的這件事，也直接點出下一步的真正痛點：如果服務之間（例如 web app 要連 database）都要手動查 IP，一旦 Service 重建 IP 就變了，設定檔就得跟著改。這正是為什麼 Kubernetes 需要 **DNS-based Service Discovery**（用穩定的 Service name 取代易變的 IP），也是原文預告會在 Day 17 深入介紹的主題。

## 小結

- Service 有 `ClusterIP` / `NodePort` / `LoadBalancer` 三種類型，各自解決「誰能存取 Pod」的不同範圍問題。
- Cluster IP 預設是動態分配的，重建 Service 就會改變；NodePort 預設範圍是 30000~32767，可透過啟動參數調整。
- 下一篇（Day 10）主題：`Labels`。

# Day 10

> 參考來源：[[Day 10] Kubernetes 世界不可缺少的 - Labels](https://ithelp.ithome.com.tw/articles/10194613)

## Labels 是什麼

Labels 就是一組**具有辨識度的 key/value**，貼在物件上用來標示屬性、分群管理，例如：

- `release: stable` / `release: qa`
- `environment: dev` / `environment: production`
- `tier: backend` / `tier: frontend`

特點：

- 一個物件可以同時擁有多個 labels（multiple labels）。
- 可以透過 **Selector** 篩選、縮小要操作的物件範圍。
- 除了 `key=value` 的等於關係（Equality-based），也能用 `matchExpressions` 做更彈性的篩選（跟 [Day 8](#day-8) Replica Set 提到的 `In`/`NotIn`/`Exists`/`DoesNotExist` 是同一套機制）。

## Annotations 是什麼

Annotations 是**沒有識別用途**的標籤，用來記錄給人看、給工具看的輔助資訊（例如發行時間、版本、聯絡人 email），**Kubernetes 本身不會拿 Annotations 來做篩選或排程**，純粹是方便開發者與維運人員管理。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: my-pod
  labels:
    app: webserver
    tier: backend
  annotations:
    version: latest
    release_date: 2017/12/28
    contact: zxcvbnius@gmail.com
spec:
  containers:
  - name: pod-demo
    image: zxcvbnius/docker-demo
    ports:
    - containerPort: 3000
```

```bash
$ kubectl create -f ./my-pod.yaml
$ kubectl get pods --show-labels        # 看 labels
$ kubectl describe pods my-pod          # 看 annotations
```

**動態新增 Labels**：

```bash
$ kubectl label pods my-pod env=production
$ kubectl get pods my-pod --show-labels
# LABELS: app=webserver,env=production,tier=backend
```

## 實作：將 Pod 部署到特定的 Node（nodeSelector）

Labels 的概念同樣可以套用在 **Node** 上：先幫 Node 貼標籤，再讓 Pod 用 `nodeSelector` 指定「只想被排程到帶有特定 label 的 Node」。

```yaml
# my-pod-with-node-selector.yaml（節錄）
spec:
  nodeSelector:
    hardware: high-memory
  containers:
  - ...
```

```bash
$ kubectl create -f ./my-pod-with-node-selector.yaml
$ kubectl get pods
# my-pod   0/1   Pending   0   ...
```

因為 Cluster 裡還沒有任何 Node 帶有 `hardware=high-memory` 這個 label，Pod 會卡在 **`Pending`** 狀態，`kubectl describe pod` 會看到排程失敗、找不到符合條件的 Node。幫 Node 補上對應 label 後，Pod 就會立刻被排程成功：

```bash
$ kubectl label node minikube hardware=high-memory
$ kubectl get pods
# my-pod   1/1   Running   0   ...
```

> 實務情境：如果有兩種 Pod，一種吃記憶體、一種吃 CPU，就能透過幫 Node 貼上不同 label + Pod 設定對應 `nodeSelector`，讓資源分配更有效率。原文也提到 `nodeSelector` 之外還有更彈性的 **Affinity / anti-affinity**（當時仍是 beta 版本）。

## 我的想法

- 這一天其實是把前幾天看過的東西「打回原形」：[Day 7](#day-7) RC 的 `selector`、[Day 8](#day-8) RS 的 `matchLabels`/`matchExpressions`、[Day 9](#day-9) Service 的 `selector`，全部都是同一套 **Labels + Selector** 機制的不同應用場景而已，只是「被選中的對象」分別是 Pod（給 RC/RS/Deployment 管理）跟 Pod（給 Service 導流）。理解了 Day 10 這個底層機制，回頭看前幾天的 yaml 會更有「原來都是同一招」的感覺。
- **Labels 可以拿來 selector，Annotations 不行**——這是很容易搞混、也是 CKAD 考試常見的細節陷阱：如果考題要求「用某個 key/value 篩選/選取物件」，答案一定是改 `labels`，改 `annotations` 是沒有作用的。
- `nodeSelector` 嚴格來說是 **Node 排程**的範疇，在目前官方 CKAD 考綱（見下方 CKAD TEST）裡其實沒有被明確列為考點，比較偏向 CKA（Cluster Admin）在管理多節點 Cluster 時才需要深入的技能。對準備 CKAD 的人來說，這天真正該內化的重點是 **Labels/Selector 的通用概念**，而不是 `nodeSelector` 本身的排程細節——考試時間有限，優先度可以放在 Selector 怎麼被 Service、Deployment 等物件使用上。

## 小結

- Labels 用於分類、篩選（Selector 用得到）；Annotations 只是給人看的備註（Selector 用不到）。
- `nodeSelector` 讓 Pod 只被排程到帶有特定 label 的 Node，沒有符合的 Node 時 Pod 會卡在 `Pending`。
- 下一篇（Day 11）主題：`Health Checks`。

# Day 11

> 參考來源：[[Day 11] 服務中斷了？該怎麼透過 Kubernetes 檢測服務 - Health Checks](https://ithelp.ithome.com.tw/articles/10194846)

## 為什麼需要 Health Checks

Pod 還在 `Running` 不代表裡面的 container 一定正常：container 內的 web app 可能因故停止回應、或資源被其他 container 佔用，導致 request 無法正常處理。Kubernetes 提供 **Health Checks（Probe）** 機制，定期偵測 container 是否還正常運作，異常時自動 restart container。

兩種常見的 health check 方式：

- 定期**透過指令**去訪問 container（exec）
- 定期**發送一個 HTTP request** 給 container（httpGet）

## 實作：在 Deployment 中加入 livenessProbe

```yaml
apiVersion: apps/v1beta2 # for kubectl versions >= 1.9.0 use apps/v1
kind: Deployment
metadata:
  name: hello-deployment
spec:
  replicas: 3
  selector:
    matchLabels:
      app: my-deployment
  template:
    metadata:
      labels:
        app: my-deployment
    spec:
      containers:
      - name: webapp
        image: zxcvbnius/docker-demo
        ports:
        - name: webapp-port
          containerPort: 3000
        livenessProbe:
          httpGet:
            path: /
            port: webapp-port
          initialDelaySeconds: 15
          periodSeconds: 15
          timeoutSeconds: 30
          successThreshold: 1
          failureThreshold: 3
```

**`livenessProbe` 欄位說明**：

| 欄位 | 說明 |
| --- | --- |
| `httpGet.path` | health check 要訪問的路徑 |
| `httpGet.port` | 要訪問的 port（可用 containerPort 的 `name`，這裡是 `webapp-port` = 3000） |
| `initialDelaySeconds` | container 啟動後，延遲幾秒才開始做 health check |
| `periodSeconds` | 每隔幾秒訪問一次，預設 `10` 秒 |
| `successThreshold` | 連續訪問成功幾次，才視為目前 service 正常 |
| `failureThreshold` | 連續失敗幾次後才判定 container 異常並 restart，預設 `3` 次 |

> 實務上（Production）通常會準備一個專門回應 health check 的 endpoint，例如 `/health`，而不是直接打首頁路徑。

建立並檢查：

```bash
$ kubectl create -f ./my-deployment-with-health-checks.yaml
deployment "hello-deployment" created

$ kubectl get deploy
NAME               DESIRED   CURRENT   UP-TO-DATE   AVAILABLE   AGE
hello-deployment   3         3         3            3           23s

$ kubectl describe pod <pod-name>
# 詳細資料中的 Liveness 欄位，可看到目前 health check 的設定與狀態
```

當 container 無法正常回應 health check 時，Kubernetes 會視為該 container 失去功能，並自動重啟它。

## 小結

- Health Check（Probe）確保「Pod 狀態正常」跟「裡面的服務真的還在正常回應」是兩回事，前者靠 Kubernetes 排程機制，後者要靠 `livenessProbe` 主動偵測。
- 本篇示範的是 `httpGet` 方式；另外還有**透過指令（exec）**、**TCP** 定期檢查等方式，屬於同一套機制的不同偵測手段。
- 下一篇（Day 12）主題：`Secrets`（如何在 Kubernetes 中存放機敏資料）。

# Day 12

> 參考來源：[[Day 12] 敏感的資料怎麼存在k8s?! - Secrets](https://ithelp.ithome.com.tw/articles/10195094)

## 什麼是 Secret

`Secret` 讓開發者能以**非明碼（opaque）**的方式，在 Kubernetes 中存放敏感資訊，例如資料庫帳密、Access Token、SSH Key。Kubernetes 自己也用同一套機制存放 access token，藉此限制外部服務對 API 的存取權限。

存取敏感資料常見的三種方式（今天示範前兩種）：

- 當成**環境變數（environment variables）**使用
- 掛載（mount）成 Pod 內某個路徑下的檔案
- 把敏感資料統一包進**私有 Image Registry** 的 image 裡，由 Pod pull image 取得

## 建立 Secret 物件的三種方式

**1. 從檔案匯入**

```bash
$ echo -n "root" > ./username.txt
$ echo -n "rootpass" > ./password.txt
$ kubectl create secret generic demo-secret-from-file \
  --from-file=./username.txt --from-file=./password.txt
```

> 若 Secret 是用 `--from-file` 建立，Kubernetes 會把**檔案名稱當成 key、檔案內容當成 value**。

**2. 從指令直接輸入（`--from-literal`）**

```bash
$ kubectl create secret generic demo-secret-from-literal \
  --from-literal=username=root \
  --from-literal=password=rootpass
```

**3. 透過 YAML 建立**（`data` 底下的值須先用 base64 編碼）

```bash
$ echo -n "root" | base64        # cm9vdA==
$ echo -n "rootpass" | base64    # cm9vdHBhc3M=
```

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: demo-secret-from-yaml
type: Opaque
data:
  username: cm9vdA==
  password: cm9vdHBhc3M=
```

```bash
$ kubectl create -f ./my-secret.yaml
```

`kubectl get secrets` 除了看到自己建立的 Secret，還會看到 Kubernetes 內建的 `default-token-xxxxx`，裡面存放的 token 是開發者操控 Kubernetes API 用的存取憑證。

## 如何在 Pod 中使用 Secret

**1. 當成環境變數**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: my-pod
  labels:
    app: webserver
spec:
  containers:
  - name: demo-pod
    image: zxcvbnius/docker-demo
    ports:
    - containerPort: 3000
    env:
    - name: SECRET_USERNAME
      valueFrom:
        secretKeyRef:
          name: demo-secret-from-yaml
          key: username
    - name: SECRET_PASSWORD
      valueFrom:
        secretKeyRef:
          name: demo-secret-from-yaml
          key: password
```

**2. 掛載成檔案**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: my-pod-with-mounting-secret
  labels:
    app: webserver
spec:
  containers:
  - name: demo-pod
    image: zxcvbnius/docker-demo
    ports:
    - containerPort: 3000
    volumeMounts:
    - name: secret-volume
      mountPath: /etc/creds
      readOnly: true
  volumes:
  - name: secret-volume
    secret:
      secretName: demo-secret-from-yaml
```

### Secret 與 Volume Mount 的關係圖（`demo-secret/my-pod-with-mounting-secret.yaml`）

掛載成檔案的寫法，中間其實經過兩層「同名連結」：先靠 `secretName` 找到是哪一個 Secret，再靠 `volumes` 與 `volumeMounts` 的 `name` 欄位互相對應，才能決定這個 Volume 要接到 container 裡的哪個路徑。

```
Secret: demo-secret-from-yaml   (demo-secret/my-secret.yaml)
  data:
    username: cm9vdA==        ← base64 解碼後 = root
    password: cm9vdHBhc3M=    ← base64 解碼後 = rootpass
        │
        │ ① spec.volumes[].secret.secretName
        │   指定這個 volume 要對應哪一個 Secret 物件
        ▼
Pod: my-pod-with-mounting-secret
  spec.volumes:
    - name: secret-volume              ← Volume 在這個 Pod 裡的代稱
      secret:
        secretName: demo-secret-from-yaml
        │
        │ ② spec.containers[].volumeMounts[].name
        │   必須與上面 volumes[].name 相同，才能找到同一個 volume
        ▼
  spec.containers[0].volumeMounts:
    - name: secret-volume              ← 對應 volumes 裡的 secret-volume
      mountPath: /etc/creds            ← 掛載到 container 內的路徑
      readOnly: true
        │
        │ ③ Secret data 底下每個 key，會各自變成 mountPath 下的一個檔案
        ▼
  Container: demo-pod
    /etc/creds/username  →  root       （來自 Secret 的 username）
    /etc/creds/password  →  rootpass   （來自 Secret 的 password）
```

**關係摘要**

| 連結 | 欄位 | 說明 |
| --- | --- | --- |
| Secret ↔ Volume | `volumes[].secret.secretName` = Secret 的 `metadata.name` | 決定這個 volume 內容來自哪一個 Secret |
| Volume ↔ Container Mount | `volumeMounts[].name` = `volumes[].name` | 決定 container 要掛載哪一個 volume（純粹是 Pod 內部的名稱對應，跟 Secret 名稱無關） |
| Secret data ↔ 檔案 | `mountPath` + Secret 的每個 `key` | Secret 裡有幾個 key，`mountPath` 底下就會出現幾個同名檔案，內容是 base64 解碼後的原始值 |

> 對照 [Day 12](#day-12) 「當成環境變數」的寫法會用 `secretKeyRef.key` 只取單一 key；而掛載成檔案這種寫法預設是把整個 Secret 的所有 key 都掛出來，各自變成一個檔案。

建立後可用 `kubectl exec -it <pod> -- /bin/bash` 進入容器，分別用 `echo $SECRET_USERNAME` 或查看 `/etc/creds` 底下的檔案，確認取得的值跟 `demo-secret-from-yaml` 一致。

## 小結

- Secret 建立後，Cluster 內其他有權限的使用者／物件也能存取其中的敏感資料，因此需要搭配 **Service Account** 限制存取範圍（Day 28 `Namespaces` 會再介紹更完整的專案隔離方式）。
- **勘誤**：base64 只是一種**編碼（encoding）**方式，不是**加密（encryption）**，不能單靠它保護敏感資料的安全性。
- 下一篇（Day 13）主題：`Demo`——在 minikube 上架設 Stateless Wordpress。

# Day 13

> 參考來源：[[Day 13] 如何在Kubernetes上架設Wordpress？](https://ithelp.ithome.com.tw/articles/10195192)

## 前言

前面幾天（[Day 7](#day-7) Replication Controller、[Day 8](#day-8) Deployment、[Day 9](#day-9) Service、[Day 12](#day-12) Secrets）已經介紹過常用元件，今天把這些元件組合起來，在 minikube 上實際架設一個 **Stateless Wordpress**。

## Wordpress 是什麼

Wordpress 是開源、以 **PHP + MySQL** 為主要架構的建站軟體，官方在 Docker Hub 上提供了 [Wordpress Image](https://hub.docker.com/_/wordpress/) 與 [MySQL Image](https://hub.docker.com/_/mysql/)，兩個 Image 頁面都有列出可設定的環境變數，稍後會透過 Secret 把這些變數傳給 container。

## 實作：在 minikube 上架設 Wordpress

**1. 建立 Secret 存放 DB 密碼**

```yaml
# wordpress-secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: wordpress-secret
type: Opaque
data:
  # echo -n "rootpass" | base64
  db-password: cm9vdHBhc3M=
```

```bash
$ kubectl create -f ./wordpress-secret.yaml
```

**2. 建立 Deployment，一個 Pod 內放兩個 container（wordpress + mysql）**

```yaml
# my-wordpress-deploy.yaml
apiVersion: apps/v1beta2
kind: Deployment
metadata:
  name: wordpress-app
spec:
  replicas: 1
  selector:
    matchLabels:
      app: wordpress-deployment
  template:
    metadata:
      labels:
        app: wordpress-deployment
    spec:
      containers:
      - name: wordpress
        image: wordpress:4-php7.0
        ports:
        - name: wordpress-port
          containerPort: 80
        env:
        - name: WORDPRESS_DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: wordpress-secret
              key: db-password
        - name: WORDPRESS_DB_HOST
          value: 127.0.0.1
      - name: mysql
        image: mysql:5.7
        ports:
        - name: mysql-port
          containerPort: 3306
        env:
        - name: MYSQL_ROOT_PASSWORD
          valueFrom:
            secretKeyRef:
              name: wordpress-secret
              key: db-password
```

重點整理：

- `wordpress` 沒指定 `WORDPRESS_DB_USER` 時，預設以 `root` 帳號連線 MySQL；`mysql` 則用 `MYSQL_ROOT_PASSWORD` 設定 `root` 密碼——只要兩邊密碼一致（都引用同一個 `wordpress-secret` 的 `db-password`），wordpress container 就能以 root 身份連進 mysql container。
- 兩個 container 在**同一個 Pod** 內，依照 [Day 6](#day-6) 提過的機制共用網路，因此 wordpress 直接用 `WORDPRESS_DB_HOST: 127.0.0.1`（即 `localhost:3306`）就能連到同 Pod 內的 mysql，不需要另外建立 Service。
- 同一份 Secret（`wordpress-secret`）被兩個 container 分別以 `secretKeyRef` 引用同一個 `key: db-password`，是 Secret 可以「一份多處使用」的實例。

**3. 建立 Service 讓外部瀏覽器能存取**

```yaml
# wordpress-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: wordpress-service
spec:
  ports:
  - port: 3000
    nodePort: 30300
    protocol: TCP
    targetPort: wordpress-port
  selector:
    app: wordpress-deployment
  type: NodePort
```

```bash
$ kubectl create -f ./wordpress-service.yaml
$ kubectl get all                              # 確認所有物件都 READY
$ minikube service wordpress-service --url     # 取得存取網址
```

用瀏覽器打開該網址，即可看到 Wordpress 安裝精靈；依序設定語言、網站名稱、使用者帳密後即可登入後台，完成 Blog 架設。

## 關係圖：Pod 內 Secret / Container 溝通

```
Secret: wordpress-secret
  data.db-password = "rootpass"（base64 解碼後）
        │
        ├── secretKeyRef ──────────────┐
        │                              │
        ▼                              ▼
Pod: wordpress-app-xxxx（同一個 Pod，共用 network / localhost）
  ┌────────────────────────┐   ┌────────────────────────┐
  │ container: wordpress   │   │ container: mysql        │
  │  WORDPRESS_DB_PASSWORD │   │  MYSQL_ROOT_PASSWORD     │
  │  = db-password         │   │  = db-password           │
  │  WORDPRESS_DB_HOST     │──▶│  containerPort: 3306     │
  │  = 127.0.0.1           │   │                          │
  └────────────────────────┘   └────────────────────────┘
        ▲
        │ targetPort: wordpress-port (80)
        │
Service: wordpress-service (NodePort 30300)
        ▲
        │
   瀏覽器 http://<minikube-ip>:30300
```

## 待補足的坑：資料持久化

MySQL 的資料目前存在 container 裡，一旦 Pod crash 或被刪除，後台編輯過的資料會全部遺失——這是本篇示範刻意稱作「**Stateless** Wordpress」的原因。之後 Day 20（`Volumes`）會補上資料持久化的做法。

## 小結

- 這天是把前 12 天學到的元件（Deployment、multi-container Pod、Secret、Service）第一次組合成一個完整可用的應用，練習「元件如何互相配合」而不是學新概念。
- 重點技巧：**同 Pod 內多 container 靠 `localhost` 溝通**（不需要 Service），以及**同一個 Secret 可以被多個 container 分別引用**。
- 目前的架設方式資料不會持久化，下一篇（Day 14）主題：`Kubernetes Dashboard` 介紹。

# CKAD TEST

> 資料來源：CNCF 官方 [CKAD Exam Curriculum](https://github.com/cncf/curriculum)（目前版本 v1.35，對應 Kubernetes 1.35，2026-03-14 發布）

**CKAD（Certified Kubernetes Application Developer）** 是 CNCF / Linux Foundation 提供的認證考試，考核重點是「以 Kubernetes 開發、部署、維運應用程式」的實作能力（2 小時、15-20 題實作題，及格門檻 66%）。目前官方考綱分為 5 大 Domain：

| Domain | 佔比 |
| --- | --- |
| Application Design and Build | 20% |
| Application Deployment | 20% |
| Application Observability and Maintenance | 15% |
| Application Environment, Configuration and Security | 25% |
| Services and Networking | 20% |

以下依 Domain 整理每個知識點內容，並標註目前筆記對應到哪一天（Day），方便掌握讀書進度。

## 20% - Application Design and Build

| 知識點 | 內容 | 對應 Day |
| --- | --- | --- |
| Define, build and modify container images | 建立/修改 container image（Docker 等） | 尚未涉及 |
| Choose and use the right workload resource（Deployment、DaemonSet、CronJob 等） | 依需求選擇合適的 workload 物件來管理 Pod | [Day 7](#day-7)（Replication Controller）、[Day 8](#day-8)（Replica Set、Deployment，皆透過 `selector`／`matchLabels` 篩選管理對象，原理見 [Day 10](#day-10)） |
| Multi-container Pod design patterns（sidecar、init 等） | 同一 Pod 內多個 container 協作的設計模式 | [Day 6](#day-6)（提到同 Pod 內 container 可用 `localhost` 溝通）、[Day 13](#day-13)（實際範例：wordpress + mysql 兩個 container 放同一 Pod，靠 `localhost` 溝通，但尚未介紹 sidecar / init pattern 這種正式分類） |
| Utilize persistent and ephemeral volumes | Volume 的使用 | 尚未涉及 |

## 20% - Application Deployment

| 知識點 | 內容 | 對應 Day |
| --- | --- | --- |
| 部署策略（blue/green、canary） | 使用 K8s 原生機制實作部署策略 | 尚未涉及 |
| Deployment 與 rolling update | 管理 Pod 版本更新 | [Day 8](#day-8)（`kubectl set image`、`rollout status/history/undo`、`maxSurge`、`maxUnavailable`） |
| Helm | 套件管理工具 | 尚未涉及 |
| Kustomize | 設定檔管理工具 | 尚未涉及 |

## 15% - Application Observability and Maintenance

| 知識點 | 內容 | 對應 Day |
| --- | --- | --- |
| API deprecations | API 版本淘汰規則 | 尚未涉及 |
| Probes / health checks | liveness、readiness、startup probe | [Day 11](#day-11)（`livenessProbe`／`httpGet`，尚未涉及 readiness／startup probe） |
| 使用內建 CLI 工具監控應用 | `kubectl get` / `describe` 等 | [Day 5](#day5)、[Day 6](#day-6)（`kubectl get pods`、`describe pod`、`get nodes` 等） |
| Container logs | 取得 container log | [Day 5](#day5)（`kubectl attach` 進入 container 查看，非正式 `kubectl logs`） |
| Debugging in Kubernetes | 除錯技巧 | 尚未涉及 |

## 25% - Application Environment, Configuration and Security

| 知識點 | 內容 | 對應 Day |
| --- | --- | --- |
| CRD / Operators | 擴充 Kubernetes 資源 | 尚未涉及 |
| Authentication / Authorization / Admission Control | 認證授權機制 | 尚未涉及 |
| Requests / limits / quotas | 資源請求與限制 | 尚未涉及 |
| 定義資源需求（resource requirements） | container resource requirements | 尚未涉及 |
| ConfigMaps | 設定值管理 | 尚未涉及 |
| Secrets | 機敏資料管理 | [Day 12](#day-12)（`kubectl create secret`、YAML+base64、環境變數／volume 掛載，尚未涉及搭配 Service Account 限制存取） |
| ServiceAccounts | 服務帳號 | 尚未涉及 |
| SecurityContexts / Capabilities | 安全性設定 | 尚未涉及 |

## 20% - Services and Networking

| 知識點 | 內容 | 對應 Day |
| --- | --- | --- |
| NetworkPolicies | 網路流量控管規則 | 尚未涉及 |
| 建立與除錯 Service 存取 | 透過 Service 曝露應用、排除連線問題 | [Day 5](#day5)（`kubectl expose`、NodePort、Port Mapping 架構圖）、[Day 6](#day-6)（kube-proxy / iptables 如何決定流量轉發）、[Day 9](#day-9)（Service YAML 完整欄位、`ClusterIP`/`NodePort`/`LoadBalancer` 三種類型、Dynamic Cluster IP、NodePort Range 限制）、[Day 10](#day-10)（Service 的 `selector` 底層就是 Labels 篩選機制） |
| Ingress | 對外路由規則 | 尚未涉及 |

## 小結

- 已涵蓋：workload resource 概念（Day 7 Replication Controller、Day 8 Replica Set / Deployment）、Deployment 的 rollout / rollback（Day 8）、Service 完整概念與三種類型（Day 5、Day 6、Day 9）、基本 CLI 監控指令、Probes / health checks 的 `livenessProbe`（Day 11，尚缺 readiness／startup probe）、Secrets 基本建立與掛載方式（Day 12，尚缺 Service Account 限制存取）。
- Services and Networking 這個 Domain（20%）目前只剩 `NetworkPolicies` 與 `Ingress` 尚未涉及，其餘知識點已有不錯的覆蓋。
- **Day 10 補充說明**：Labels / Selector 是貫穿多個考點的底層機制（workload resource 的 `selector`、Service 的 `selector` 都靠它），本身不是獨立的考綱條目，但值得作為理解其他考點的基礎；而 `nodeSelector`（Pod 排程到特定 Node）**不在目前 CKAD 官方考綱的 5 大 Domain 內**，比較屬於 CKA 的範疇，準備 CKAD 可以降低這部分的優先度。
- 佔分最重（25%）的 Environment/Config/Security 幾乎完全尚未涉及，加上部署策略（blue/green、canary）、Helm、Kustomize、Probes 等，是 Day 11 之後應優先加強的重點。
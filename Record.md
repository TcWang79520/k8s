
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
- [Day 17](#day-17) - DNS Service Discovery（kube-dns）
- [Day 18](#day-18) - ConfigMap（配置與程式碼分離）
- [Day 19](#day-19) - Ingress 與 Ingress Controller（負載平衡）
- [Day 20](#day-20) - Volumes（資料持久化：emptyDir / hostPath / Cloud Storage / NFS）
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
- **DNS / kube-dns**：`kube-dns` 讓 Pod 之間可透過 Service 名稱（而非動態 Cluster IP）互相溝通、`/etc/resolv.conf` 自動注入 nameserver
- **ConfigMap**：`kubectl create configmap`（`--from-file` / `--from-literal`）、非機密的部署配置（與 Secret 的機密資料互補）、以 `volumes.configMap` 掛載成檔案供 container 使用
- **Ingress / Ingress Controller**：統一對外 port、以路徑（path）或 domain name 導流到不同 Service、SSL termination、Ingress Controller（Nginx/GCE）才是真正實現負載平衡的元件
- **Volumes**：讓 container 資料持久化（stateless → stateful）、四種常用類型 `emptyDir`（隨 Pod 生滅）/ `hostPath`（隨 Node 生滅）/ Cloud Storage（AWS EBS 等）/ `NFS`、`volumes` + `volumeMounts` 掛載機制


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

## 疊層關係圖：ClusterIP / NodePort / LoadBalancer / port

三種 type 不是三個獨立機制，而是**一層包一層**：`LoadBalancer` 其實也會自動建立 `NodePort`，`NodePort` 也會自動建立 `ClusterIP`——`ClusterIP` 才是所有 Service 都一定會有的最基礎層。每一層各自的 `port` 意義都不同：

```
外部使用者（瀏覽器 / 手機 App）
        │
        │ 只有雲端環境、type=LoadBalancer 才有這一層
        ▼
┌────────────────────────────────────────────────┐
│ LoadBalancer                                     │
│   對外統一入口： <LB-IP>:port                       │  ← 由 Cloud Provider 建立（如 AWS ELB）
└─────────────────────┬────────────────────────────┘
                       │ 自動轉發給叢集內每個 Node 的 nodePort
                       ▼
┌────────────────────────────────────────────────┐
│ NodePort（建立在 ClusterIP 之上）                    │
│   叢集外部、同一 Node： <NodeIP>:nodePort            │  ← type=NodePort / LoadBalancer 才會開
└─────────────────────┬────────────────────────────┘
                       │ 轉發給 Service 自己的 ClusterIP:port
                       ▼
┌────────────────────────────────────────────────┐
│ ClusterIP（三種 type 都一定會有的基礎層）              │
│   叢集內部： <ClusterIP>:port                       │  ← 未指定 type 時的預設值
└─────────────────────┬────────────────────────────┘
                       │ targetPort（轉發到 Pod 實際監聽的 port）
                       ▼
┌────────────────────────────────────────────────┐
│ Pod：container port（例如 3000）                    │
└────────────────────────────────────────────────┘
```

看這張圖時，抓住兩個重點：

- **由下往上是「疊加」關係，不是「三選一」**：選 `NodePort` 代表你同時擁有 ClusterIP + NodePort 這兩層；選 `LoadBalancer` 則三層都有。
- **同一個字「`port`」在不同層代表不同東西**：ClusterIP 那層的 `port` 是叢集內部存取用的埠；LoadBalancer 那層的 `port` 是外部對外統一入口的埠；只有 `nodePort` 跟 `targetPort` 才有自己專屬的欄位名稱，容易搞混的反而是這兩個地方都用 `port` 這個字。

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
- Cluster IP 是動態的這件事，也直接點出下一步的真正痛點：如果服務之間（例如 web app 要連 database）都要手動查 IP，一旦 Service 重建 IP 就變了，設定檔就得跟著改。這正是為什麼 Kubernetes 需要 **DNS-based Service Discovery**（用穩定的 Service name 取代易變的 IP），這正是 [Day 17](#day-17) 深入介紹的主題。

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

# Day 17

> 參考來源：[[Day 17] Pod 之間是如何找到彼此呢 - DNS Service Discovery](https://ithelp.ithome.com.tw/articles/10195786)

## 前言：為什麼需要 DNS Service Discovery

在 [Day 9](#day-9) 提過，**Service 每次被建立時，Kubernetes Cluster 都會動態給予一組新的 Cluster IP**。當 Cluster 中有多個 Pod 同時運行，各自有自己的 Service，且彼此之間都要靠 Service 互相溝通時，該如何確保在 Cluster IP 動態變動的情況下，Service 之間仍能找到彼此？

Kubernetes 內建一個 `kube-dns` 插件解決了這個問題：**不需要知道 Service 的 Cluster IP，只要透過 Service 的名稱，就能找到相對應的 Pod**。

今天筆記涵蓋：

- DNS 是什麼
- Kubernetes 內部插件 `kube-dns` 如何運作
- 實作：把 [Day 13](#day-13) 同一 Pod 內的 wordpress + mysql 拆成兩個獨立 Pod，改用 Service 名稱互相溝通

> 範例程式碼可參考原文附的 [demo-dns](https://github.com/zxcvbnius/k8s-30-day-sharing/blob/master/Day17/demo-dns)。

## DNS 是什麼

DNS，全名 **Domain Name System**。DNS 內部維護一張表格，紀錄每個 domain name 對應的 IP 位址，讓使用者不需要記住服務的 IP，而是透過網域名稱就能連上服務（例如瀏覽器輸入 `www.google.com.tw` 時，DNS 會找到對應 IP 並完成連線）。若想查詢某個網域對應的 IP，可在終端機使用 `host` 指令。

## kube-dns 如何運作

Kubernetes 本身提供 DNS 套件 `kube-dns`，讓**同一個 Kubernetes Cluster 中的所有 Pod，都能透過 Service 的名稱找到彼此**。透過 `kubectl get` 可以看到 `kube-dns` 本身也是 Cluster 中運行的一個服務，Cluster 建立後就會自動運行。

- `kube-dns` 的相關設定檔放在 **master node 的 `/etc/kubernetes/addons`** 資料夾底下；以 minikube 為例，minikube 的 VM 本身就是 master node，可用 `minikube ssh` 登入查看。
- `kube-dns` 是運行在 Cluster 中的一個 Pod，也有對應的 Service 物件。
- **Kubernetes 在每個 Pod 建立時，都會自動在該 Pod 的 `/etc/resolv.conf` 中加入 `kube-dns` Service 的 domain name 與對應 IP**。因此其他 Pod 可以透過名為 `kube-dns` 的 Service 物件，找到正在運行的 `kube-dns`。

```bash
# 進入 alpine Pod 的 shell 後查看
$ cat /etc/resolv.conf
# nameserver 指向的 IP，就是 kube-dns 這個 Service 的 Cluster IP
```

> 若對 `alpine` Pod 操作不熟悉，可參考 [Day 5](#day5) 常用 kubectl 指令。

## 實作：把 Wordpress 拆成兩個 Pod，透過 Service 名稱溝通

[Day 13](#day-13) 是把 wordpress 與 mysql 放在**同一個** Pod 裡，靠 `localhost` 溝通。這次改成拆成**兩個獨立 Pod**，各自建立 Service，wordpress 改用 mysql Service 的**名稱**（而非 IP）連線，驗證 `kube-dns` 是否真的能讓兩個 Pod 找到彼此。

會用到 5 個設定檔：`mysql-secret.yaml`、`mysql-server-pod.yaml`、`mysql-server-service.yaml`、`wordpress-pod.yaml`、`wordpress-service.yaml`。

### 1. 建立 Secret（存放 DB 密碼）

```yaml
# mysql-secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: mysql-secret
type: Opaque
data:
  # echo -n "rootpass" | base64
  db-root-password: cm9vdHBhc3M=
```

```bash
$ kubectl create -f ./mysql-secret.yaml
secret "mysql-secret" created
```

### 2. 建立 MySQL Server（獨立 Pod + Service）

```yaml
# mysql-server-pod.yaml
apiVersion: v1
kind: Pod
metadata:
  name: mysql-server
  labels:
    app: mysql-server
spec:
  containers:
  - name: mysql-server
    image: mysql:5.7
    ports:
    - name: mysql-port
      containerPort: 3306
    env:
    - name: MYSQL_ROOT_PASSWORD
      valueFrom:
        secretKeyRef:
          name: mysql-secret
          key: db-root-password
```

```yaml
# mysql-server-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: mysql-server-service
spec:
  ports:
  - port: 3306
    protocol: TCP
  selector:
    app: mysql-server
  type: NodePort
```

```bash
$ kubectl create -f ./mysql-server-pod.yaml
pod "mysql-server" created

$ kubectl create -f ./mysql-server-service.yaml
service "mysql-server-service" created
```

### 3. 建立 Wordpress App（獨立 Pod + Service）

```yaml
# wordpress-pod.yaml
apiVersion: v1
kind: Pod
metadata:
  name: wordpress
  labels:
    app: wordpress
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
          name: mysql-secret
          key: db-root-password
    - name: WORDPRESS_DB_HOST
      value: mysql-server-service
```

關鍵在 `WORDPRESS_DB_HOST` 這裡，值直接填 **`mysql-server-service`（Service 名稱）**，而不是任何 IP——這就是 `kube-dns` 實際發揮作用的地方。

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
    app: wordpress
  type: NodePort
```

```bash
$ kubectl create -f wordpress-pod.yaml && \
  kubectl create -f wordpress-service.yaml
pod "wordpress" created
service "wordpress-service" created

$ kubectl get all   # 確認所有物件都是 Ready 狀態

$ minikube service wordpress-service --url
http://192.168.99.100:30300
```

瀏覽器打開該網址即可看到 Wordpress 歡迎頁面；設定好帳密進入後台編輯內容，再進 mysql server 查看，可以看到 database 內容確實同步更新，證明兩個獨立 Pod 之間透過 Service 名稱成功溝通。

> **原文備註**：讀者 @iming0319 曾勘誤原文一處筆誤——建立物件應為 `kubectl create` 而非 `kubectl get`（`kubectl get` 是查詢，不會建立物件）。

## 關係圖：兩個獨立 Pod 如何透過 kube-dns 找到彼此

```
Pod: wordpress                              Pod: mysql-server
  container: wordpress                        container: mysql-server
  env.WORDPRESS_DB_HOST                        containerPort: 3306
    = "mysql-server-service"  ──┐
                                 │  ① wordpress 不用 IP，直接用 Service 名稱
                                 ▼
                    Service: mysql-server-service
                    (selector: app=mysql-server)
                                 ▲
                                 │  ② kube-dns 把 Service 名稱解析成
                                 │     mysql-server-service 目前的 Cluster IP
                    ┌────────────────────────────┐
                    │ kube-dns（Cluster 內建服務）   │
                    │  - 建立 Pod 時自動寫入該 Pod 的 │
                    │    /etc/resolv.conf          │
                    └────────────────────────────┘
```

## 補充：搞懂 Service Port / Pod Port / targetPort / nodePort

這幾個「port」很容易搞混，因為**四個都叫 port，卻是四個不同層級的東西**。用專案裡實際的 [`demo-wordpress-diff-pods/wordpress-pod.yaml`](demo-wordpress-diff-pods/wordpress-pod.yaml) 跟 [`demo-wordpress-diff-pods/wordpress-service.yaml`](demo-wordpress-diff-pods/wordpress-service.yaml) 這兩個檔案來對照最清楚：

```yaml
# wordpress-pod.yaml（節錄）
spec:
  containers:
  - name: wordpress
    image: wordpress:4-php7.0
    ports:
    - name: wordpress-port     # ← 幫這個 port 取名字，讓 Service 可以用名字引用它
      containerPort: 80        # ← ① Pod Port：container 裡的 wordpress 實際監聽的 port
```

```yaml
# wordpress-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: wordpress-service-diff
spec:
  ports:
  - port: 3000                 # ← ③ Service Port：Service 自己（ClusterIP）對外的 port
    nodePort: 30301             # ← ④ nodePort：開在每個 Node 實體 IP 上的 port
    protocol: TCP
    targetPort: wordpress-port # ← ② targetPort：Service 要把流量轉給 Pod 的哪個 port
  selector:
    app: wordpress             # ← 靠這個 label 找到 wordpress Pod
  type: NodePort
```

**逐一拆解**

| # | 欄位 | 這個範例的值 | 定義在哪 | 意義 |
| --- | --- | --- | --- | --- |
| ① | **Pod Port**（`containerPort`） | `80` | Pod 的 yaml，`containers[].ports[].containerPort` | container 裡的應用程式**實際監聽**的 port。這是唯一「真正在跑」的 port，其他三個都只是**轉發規則**，指向這個 port。 |
| ② | **targetPort** | `wordpress-port`（= 80） | Service 的 yaml，`spec.ports[].targetPort` | Service 要把流量轉給 Pod 的哪個 port。可以直接寫數字 `80`，也可以像這個範例一樣寫 container port 的**名字**（`wordpress-port`），Kubernetes 會自動查表對應回 `80`。這個值**必須**跟 Pod 實際監聽的 port 一致，否則轉發過去 Pod 也不會回應。 |
| ③ | **Service Port**（`port`） | `3000` | Service 的 yaml，`spec.ports[].port` | Service 自己對外的 port——Cluster 內其他 Pod 要打 `<ClusterIP>:3000` 才能連到這個 Service。注意這裡故意跟 `targetPort` 的 `80` 不同數字，就是要凸顯**這兩個是完全獨立的欄位**，`port` 給「叫用 Service 的人」用，`targetPort` 給「Service 轉發給 Pod」用，彼此不必相同。 |
| ④ | **nodePort** | `30301` | Service 的 yaml，`spec.ports[].nodePort` | 因為 `type: NodePort`，Kubernetes 額外在**每個 Node 的實體 IP** 上開一個 port（範圍 30000~32767，見 [Day 9](#day-9)），讓叢集外部（例如你的瀏覽器）能直接打 `<NodeIP>:30301` 連進來。 |

**完整流量路徑圖（帶入實際數值）**

```
瀏覽器（叢集外部）
        │
        │  打 http://<NodeIP>:30301
        ▼
┌───────────────────────────────────────────────────────────┐
│ Node (minikube VM)                                         │
│                                                             │
│   nodePort: 30301  ◄── ④ type=NodePort 才會開這個實體 port    │
│        │                                                    │
│        ▼                                                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Service: wordpress-service-diff                       │   │
│  │   ClusterIP: 10.x.x.x                                  │   │
│  │   port: 3000        ◄── ③ 叢集內部打這個 port找到 Service │   │
│  │   selector: app=wordpress  ◄── 靠 label 選中下面的 Pod   │   │
│  └─────────────────────────────────────────────────────┘   │
│        │                                                     │
│        ▼ targetPort: wordpress-port（= 80）                   │
│        （② Service 轉發流量到 Pod 實際監聽的 port）              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Pod: wordpress                                         │   │
│  │   container: wordpress                                 │   │
│  │   containerPort: 80  ◄── ① 唯一「真正在跑」的 port         │   │
│  └─────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────┘
```

**一句話總結**：只有 **①`containerPort`（Pod Port）** 是應用程式真正監聽的 port，其餘 **②`targetPort`、③`port`、④`nodePort`** 都只是不同層級（Service→Pod、叢集內部、叢集外部）的「轉發規則」，各自可以取完全不同的數字，只要 `targetPort` 對得上 `containerPort` 即可正常運作。這張圖跟 [Day 9](#day-9) 的存取路徑對照表是同一件事，只是這裡換成專案裡 `demo-wordpress-diff-pods` 的真實數值，方便直接對照 yaml 檔案理解。

## 我的想法

- 這一天把 [Day 9](#day-9) 留下的痛點（Cluster IP 動態分配、服務間溝通要手動查 IP）直接解決掉：只要 Service 名稱不變，背後 Cluster IP 怎麼變都不影響 Pod 之間的溝通，這正是 Service 名稱 + `kube-dns` 組合出的「穩定服務發現」。
- 跟 [Day 13](#day-13) 對照最能感受差異：同一個 Pod 內用 `localhost` 溝通（[Day 6](#day-6) 提過的機制）跟跨 Pod 用 Service 名稱溝通，是兩種不同層級的服務發現手段——前者靠共享網路命名空間，後者靠 `kube-dns` 解析。也因此，把原本耦合在同一 Pod 的 wordpress + mysql 拆開成兩個 Pod，才更貼近實務上「每個服務獨立部署、獨立擴展」的做法。

## 小結

- `kube-dns` 讓 Cluster 內的 Pod 可以用 **Service 名稱**取代**動態 Cluster IP**互相溝通，是 Kubernetes 內建、Cluster 建立後自動運行的服務發現機制。
- 每個 Pod 建立時，Kubernetes 會自動把 `kube-dns` 的位址寫進該 Pod 的 `/etc/resolv.conf`，因此 Pod 內對 Service 名稱的查詢都會先經過 `kube-dns` 解析。
- 本篇把 [Day 13](#day-13) 單一 Pod 內的 wordpress + mysql 拆成兩個獨立 Pod，驗證只要 Service 名稱固定，即使 Cluster IP 變動，Pod 之間仍能正常溝通。

# Day 18

> 參考來源：[[Day 18] 高彈性部署 Application - ConfigMap](https://ithelp.ithome.com.tw/articles/10196153)

## 前言：為什麼需要 ConfigMap

開發時常見的一個錯誤，是把「部署環境的設定（configuration）」跟「程式碼」一起交付——例如把 `development` / `staging` / `production` 各環境的設定寫死在程式碼裡。這麼做的風險是：**只要有人存取到程式碼，就等於拿到各環境的敏感資料**。

[12 factor](https://12factor.net/config) 對此提出的解法是：**把配置存在環境變數中**，降低 Configuration 與程式碼的耦合。但配置與程式碼分開之後，又會遇到新問題：配置**散落各地**，需要一個地方統一管理；而且不同程式語言、不同服務的配置格式又常常不一樣，統一管理更加困難。

Kubernetes 提供的 `ConfigMap` API，就是用來**統一存放 Configuration**，並讓開發者能以**動態、代碼化**的方式為每個應用服務配置對應的設定。

今天筆記涵蓋：

- 定義什麼是 Configuration
- 比較 ConfigMap 與 [Secret](#day-12) 的差別
- 介紹 ConfigMap 的建立方式
- 實作：透過 ConfigMap 配置 Nginx，把流量導到 [Day 3](https://ithelp.ithome.com.tw/articles/10192519) 打造的 Node.js App

> 範例程式碼可參考原文附的 [demo-configmap](https://github.com/zxcvbnius/k8s-30-day-sharing/blob/master/Day18/demo-configmap)。

## 什麼是 Configuration

Configuration 泛指**程式存取外部資源或部署所需的資料**，例如資料庫的所在 IP、管理者的帳號密碼，或是 Nginx 的設定檔。一旦這些資料被不小心存取（例如資料庫被刪除或公開），可能讓專案陷入危險，或損害服務使用者的權益。

## ConfigMap 與 Secret 的差別

[Day 12](#day-12) 介紹過的 `Secret`，跟今天的 `ConfigMap` 想解決的面向不同：

| | 存放內容 | 範例 | 是否編碼 |
| --- | --- | --- | --- |
| **Secret** | 機密資料 | API Token、database 密碼 | 值會經過 Base64 編碼 |
| **ConfigMap** | 非機密、屬於部署面的資料 | 資料庫的 port number、Redis 的 config file | 不編碼，明碼存放 |

## ConfigMap 特點

- **一個 ConfigMap 物件可以存入整個 configuration**，例如 webserver 或 Nginx 的 config file。
- **無需修改 container 程式碼，就能替換不同環境的 Config**——開發過程中常因應 `staging` / `production` 等不同環境，需要不同的資料庫位址等設定，這種做法能加快跨環境部署的速度。
- **統一存放所有的 configuration**，可透過 `kubectl get` 快速查看目前系統所有的 ConfigMap。

## 建立 ConfigMap 的兩種方式

**1. 匯入整個 config 檔（`--from-file`）**

以 [Redis](https://redis.io/) 的 config file 為例：

```
# my-redis.conf
bind 127.0.0.1
port 6379
maxclients 10000
maxmemory 50mb
maxmemory-policy volatile-lru
syslog-enabled yes
dir /var/lib/redis
dbfilename redis.dump.rdb
databases 1
appendfsync everysec
save 600 10
```

```bash
$ kubectl create configmap redis-config --from-file=my-redis.conf
configmap "redis-config" created
```

建立後可用 `kubectl get configmap` 查看清單，`kubectl describe configmap redis-config` 可看到 `my-redis.conf` 完整內容。

**2. 從指令直接設定（`--from-literal`）**

```bash
$ kubectl create configmap mysql-host --from-literal=ip=127.0.0.1
configmap "mysql-host" created
```

同樣可用 `kubectl describe configmap mysql-host` 查看內容。

**刪除 ConfigMap**：

```bash
$ kubectl delete configmap mysql-host
configmap "mysql-host" deleted
```

## 實作：透過 ConfigMap 配置 Nginx

今天的實作會用 ConfigMap 配置一個 Nginx Service，讓 Nginx 收到 request 後，把流量導向 [Day 3](https://ithelp.ithome.com.tw/articles/10192519) 打造的 Node.js App。

**什麼是 Nginx**：Nginx 不只是輕量的 HTTP 伺服器，同時也是一個**反向代理**伺服器——收到用戶請求後，把流量導給後端 service，再把後端處理好的資源回傳給前端使用者。

### 1. 準備 Nginx 設定檔並建立 ConfigMap

```
# my-nginx.conf
server {
    listen            80;
    server_name       localhost;

    location / {
        proxy_bind 127.0.0.1;
        proxy_pass http://127.0.0.1:3000;
    }

    error_page 500 502 503 504    /50x.html;
    location = /50x.html {
        root    /usr/share/nginx/html;
    }
}
```

```bash
$ kubectl create configmap nginx-conf --from-file=./my-nginx.conf
configmap "nginx-conf" created
```

### 2. 建立 Pod，掛載 ConfigMap 供 Nginx container 使用

```yaml
# my-pod.yaml
apiVersion: v1
kind: Pod
metadata:
  name: apiserver
  labels:
    app: webserver
    tier: backend
spec:
  containers:
  - name: nodejs-app
    image: zxcvbnius/docker-demo
    ports:
    - containerPort: 3000
  - name: nginx
    image: nginx:1.13
    ports:
    - containerPort: 80
    volumeMounts:
    - name: nginx-conf-volume
      mountPath: /etc/nginx/conf.d
  volumes:
  - name: nginx-conf-volume
    configMap:
      name: nginx-conf
      items:
      - key: my-nginx.conf
        path: my-nginx.conf
```

這個 Pod 跟 [Day 13](#day-13) 一樣是 multi-container 設計：`nodejs-app` container 監聽 3000 port（[Day 3](https://ithelp.ithome.com.tw/articles/10192519) 的 Node.js App），`nginx` container 監聽 80 port 並反向代理到 `127.0.0.1:3000`；`nginx-conf` 這份 ConfigMap 則透過 `volumes.configMap` 掛載到 `nginx` container 的 `/etc/nginx/conf.d` 路徑下，掛載方式與 [Day 12](#day-12) Secret 掛載成檔案的寫法（`volumes[].name` ↔ `volumeMounts[].name` 對應）幾乎一致，差別只在 `volumes[].configMap` 換掉了 `volumes[].secret`，並多了 `items` 指定 key 對應的檔名。

```bash
$ kubectl create -f ./my-pod.yaml
pod "apiserver" created

$ kubectl get pods    # 確認 apiserver 狀態為 Ready

$ kubectl expose pod apiserver --port=80 --type=NodePort
service "apiserver" exposed

$ minikube service apiserver --url
http://192.168.99.100:31529
```

瀏覽器打開該網址後看到 `Hello World!` 字串，代表請求成功經 Nginx 反向代理到 Node.js App，也證明 ConfigMap 成功掛載在 Nginx Pod 上。

## 補充：`demo-cm-nginx` 裡，一個 Pod、兩個 container、`kubectl expose` 的關係

用專案裡實際的 [`demo-cm-nginx/my-pod.yaml`](demo-cm-nginx/my-pod.yaml) 跟 [`demo-cm-nginx/my-nginx.conf`](demo-cm-nginx/my-nginx.conf)，再搭配實際跑出來的指令結果，把「一個 Pod 兩個 container」跟「`kubectl expose`」兜起來看：

```yaml
# my-pod.yaml（節錄）
metadata:
  name: apiserver
  labels:
    app: webserver
    tier: backend
spec:
  containers:
  - name: nodejs-app          # 真正處理邏輯、回應 Hello World! 的後端
    image: zxcvbnius/docker-demo
    ports:
    - containerPort: 3000
  - name: nginx                # 反向代理，掛載 ConfigMap 當設定檔
    image: nginx:1.13
    ports:
    - containerPort: 80
    volumeMounts:
    - name: nginx-conf-volume
      mountPath: /etc/nginx/conf.d
  volumes:
  - name: nginx-conf-volume
    configMap:
      name: nginx-conf
```

`my-nginx.conf` 掛進 `nginx` container 後，關鍵是這兩行：

```
listen 80;
proxy_pass http://127.0.0.1:3000;
```

nginx 自己監聽 `80`，收到請求後轉手打給 `127.0.0.1:3000`——也就是**同一個 Pod 裡的 `nodejs-app` container**。這能成立是因為 [Day 6](#day-6) 提過的機制：**同一個 Pod 內的 container 共用網路，可以用 `localhost` 互相溝通**，nginx 才能用 `127.0.0.1` 打到隔壁的 nodejs-app，不需要另外建立 Service。

### `kubectl expose pod` 自動幫你做了什麼

```bash
$ kubectl expose pod apiserver --port=80 --type=NodePort
service/apiserver exposed

$ minikube service apiserver --url
http://192.168.49.2:30170
```

這行指令等於自動幫你建出一個 Service：

```yaml
apiVersion: v1
kind: Service
metadata:
  name: apiserver
spec:
  type: NodePort
  selector:
    app: webserver       # ← 沒給 --selector，自動抓 apiserver Pod 自己的 labels
    tier: backend
  ports:
  - port: 80              # ← 你指定的 --port
    targetPort: 80         # ← 沒指定 --target-port，預設跟 port 相同
    nodePort: 30170         # ← 沒指定，Kubernetes 隨機分配（30000~32767，見 Day 9）
```

三個容易忽略的細節：

- **selector 是自動抓的**：`kubectl expose pod <name>` 沒給 `--selector` 時，會直接把該 Pod 自己的 labels（`app=webserver, tier=backend`）複製過去當 Service 的 selector。
- **targetPort 沒填就等於 port**：這裡只給了 `--port=80`，沒給 `--target-port`，所以 `targetPort` 也是 `80`。
- **Service 只認「Pod IP 的某個 port 是誰在聽」，不知道也不管是哪個 container**：Pod 裡兩個 container 共用同一個 Pod IP，`nginx` 監聽 `80`、`nodejs-app` 監聽 `3000`，像同一棟樓開了兩個門號不同的門。Service 的 `targetPort: 80` 天生只會敲中 `nginx` 那扇門，敲不到 `nodejs-app`——除非另外建一個 `targetPort: 3000` 的 Service。

### 完整流量路徑圖

```
瀏覽器
  │  打 http://192.168.49.2:30170
  ▼
┌──────────────────────────────────────────────────────────────┐
│ Node (minikube)                                                │
│   nodePort: 30170  ◄── 隨機分配，因為指令沒指定 --node-port         │
│        │                                                        │
│        ▼                                                        │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ Service: apiserver (NodePort)                            │    │
│  │   port: 80        ◄── 來自 --port=80                       │    │
│  │   selector: app=webserver, tier=backend                  │    │
│  │              ◄── 自動抓 apiserver Pod 的 labels             │    │
│  └────────────────────────────────────────────────────────┘    │
│        │ targetPort: 80（沒指定，預設同 port）                     │
│        ▼                                                        │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ Pod: apiserver（單一 Pod IP，兩個 container 共用網路）           │    │
│  │                                                            │    │
│  │  ┌─────────────────────┐      ┌─────────────────────┐     │    │
│  │  │ container: nginx     │      │ container: nodejs-app│     │    │
│  │  │  監聽 port 80  ◄──────┼──────┤ 監聽 port 3000        │     │    │
│  │  │  (Service targetPort  │ 打  │  (真正處理 request 的  │     │    │
│  │  │   打進來的就是這扇門)   │127.0.0.1:3000│  後端)          │     │    │
│  │  │                       │─────▶│                       │     │    │
│  │  │  proxy_pass           │      │  回傳 "Hello World!"    │     │    │
│  │  │  http://127.0.0.1:3000│      │                       │     │    │
│  │  └─────────────────────┘      └─────────────────────┘     │    │
│  │        ▲                                                    │    │
│  │        │ 掛載 ConfigMap: nginx-conf → my-nginx.conf            │    │
│  │        │ (mountPath: /etc/nginx/conf.d)                       │    │
│  └────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

**一句話總結**：Service 只負責把外部流量從 `NodePort(30170)` → `Service Port(80)` → 送到 **Pod IP 的 80 port**；至於 Pod 裡是誰在 80 port 上接（這裡是 `nginx`），跟 Service 完全無關。「兩個 container 怎麼合作」發生在 Service 完全不知情的**Pod 內部**——`nginx` 用 `localhost:3000` 把請求轉給隔壁的 `nodejs-app`，這一步跟 [Day 13](#day-13) wordpress + mysql、[Day 17](#day-17) 的 Port 拆解是同一套底層邏輯的不同應用。

## 我的想法

- ConfigMap 跟 [Day 12](#day-12) Secret 掛載成檔案的機制幾乎是同一套（`volumes` + `volumeMounts` 名稱對應），差別純粹在**用途**：Secret 存機密、會 base64 編碼；ConfigMap 存非機密的部署配置、明碼存放。理解了其中一個，另一個幾乎是直接套用。
- 這天的 Nginx + Node.js 範例，也再次用到 [Day 6](#day-6) 提過的「同 Pod 內 container 共用網路」機制——`nginx` container 直接用 `proxy_pass http://127.0.0.1:3000` 打到同 Pod 內的 `nodejs-app` container，不需要另外建立 Service，跟 [Day 13](#day-13) wordpress 連 mysql 的手法如出一轍。

## 小結

- ConfigMap 用來統一存放**非機密**的部署配置（跟 [Day 12](#day-12) Secret 存放機密資料互補），可透過 `--from-file` 匯入整個設定檔，或 `--from-literal` 直接指定單一 key/value。
- 掛載方式與 Secret 相同，都是透過 `volumes` + `volumeMounts` 把內容掛成 container 內的檔案。
- 下一篇（Day 20）主題：`Volumes`——如何讓 Pod 的資料持久化（呼應 [Day 13](#day-13) 尾聲提到「Stateless Wordpress 資料不持久化」的待補坑）。

# Day 19

> 參考來源：[[Day 19] 在 Kubernetes 中實現負載平衡 - Ingress Controller](https://ithelp.ithome.com.tw/articles/10196261)

## 前言：為什麼需要 Ingress

[Day 9](#day-9) 介紹過的 Service，能讓 Cluster 中的 Pod 被外部存取，但**每一個 Service 都要指定一個對外的 port，跟 Node 上某個 port 做 port mapping**。這代表 **Service 數量一多，需要管理的 port number 也跟著變多**，維運上更複雜；像 AWS、GCP 這類雲端服務，每台機器都有自己的防火牆，新增或刪除 Service 都得跟著調整防火牆規則。

`Ingress` 的解法：**只開放一個對外的 port number**，在設定檔中依路徑（path）決定要把請求送到哪個 Service。

今天筆記涵蓋：

- 介紹什麼是 Ingress（含三個範例：依路徑導流、依 domain name 導流、SSL termination）
- 進階實作：在 minikube 上架設 Nginx Ingress Controller

> 範例程式碼可參考原文附的 [demo-ingress](https://github.com/zxcvbnius/k8s-30-day-sharing/blob/master/Day19/demo-ingress)。

## 什麼是 Ingress

沒有 Ingress 時，多個 Service 同時運行，Node 必須為每個 Service 開一個對應的 port；用了 Ingress 後，**只需要開放一個對外的 port**，由 Ingress 依設定檔中的規則（路徑、domain name 等）決定流量該轉給哪個 Service。除了少維護多個 port、少改防火牆規則，「可自訂條件」的特性也讓導流更有彈性。

> **勘誤（API 版本）**：原文（2018 年）寫的 Ingress API 版本是 `extensions/v1beta1`，這個版本在 **Kubernetes 1.22（2021 年）已被整個移除**（不是 deprecated，是真的拿掉），現在的叢集（例如本機 minikube，Server Version v1.35.1）只認 **`networking.k8s.io/v1`**，用舊版本會直接報錯：`no matches for kind "Ingress" in version "extensions/v1beta1"`。以下範例已全部改成 `networking.k8s.io/v1` 的新寫法，並存成本機的 [`demo-ingress/ingress-example-1.yaml`](demo-ingress/ingress-example-1.yaml) 驗證可用。新舊語法差異：
>
> | | 舊（`extensions/v1beta1`） | 新（`networking.k8s.io/v1`） |
> | --- | --- | --- |
> | 指定後端 Service | `backend.serviceName` / `backend.servicePort`（平的） | `backend.service.name` / `backend.service.port.number`（巢狀） |
> | path 比對規則 | 沒有，隱含行為 | **必填** `pathType`（`Prefix` / `Exact` / `ImplementationSpecific`） |

### Example 1：依路徑（path）導到不同 Service

```yaml
# ingress-example-1.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: example-1
spec:
  rules:
  - http:
      paths:
      - path: /test
        pathType: Prefix
        backend:
          service:
            name: test
            port:
              number: 80
```

- 目前 Ingress 使用的 API 版本是 `networking.k8s.io/v1`（原文寫的 `extensions/v1beta1` 已於 K8s 1.22 移除，見上方勘誤）。
- 這份設定代表：Node 收到流量後判斷路徑，若請求路徑**前綴**是 `/test`（`pathType: Prefix`），就把流量導到名稱為 `test` 的 Service。

```bash
$ kubectl create -f ./ingress-example-1.yaml
ingress "example-1" created
```

### Example 2：依 domain name 導到不同 Service

```yaml
# ingress-example-2.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: example-2
spec:
  rules:
  - host: helloworld-v1.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: hellworld-v1
            port:
              number: 80
  - host: helloworld-v2.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: helloworld-v2
            port:
              number: 80
```

若有多個 Domain Name 同時指向同一台 Node，可以用這種寫法把不同 Domain Name 對應到不同 Service。跟 `example-1` 不同的是，`example-1` 只看路徑是否相符就導給 `test`，`example-2` 是**先判斷請求打的是哪個 Domain Name，再導到對應的 Service**。

```bash
$ kubectl create -f ./ingress-example-2.yaml
ingress "example-2" created
```

### Example 3：SSL termination

Ingress 也能做**本地終止 SSL（SSL termination）**。先把 SSL 憑證存進 Secret：

```yaml
# ingress-ssl-secret.yaml
apiVersion: v1
data:
  tls.crt: base64_encoded_cert
  tls.key: base64_encoded_key
kind: Secret
metadata:
  name: ssh-secret
  namespace: default
type: Opaque
```

再透過 `spec.tls` 把憑證掛到 Ingress 底下：

```yaml
# ingress-example-3.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: example-3
spec:
  tls:
  - secretName: ssh-secret
  defaultBackend:            # v1 把原本的 spec.backend 改名為 spec.defaultBackend
    service:
      name: apiservice
      port:
        number: 80
```

## 在 minikube 上架設 Nginx Ingress Controller

**Ingress 本身沒有提供負載平衡（Load Balancing）的功能，需要搭配 `Ingress Controller` 才能實現**。目前主要支援兩種：`GCE` 與 `Nginx`；今天示範用 **Nginx Ingress Controller** 在 Cluster 內部架設 load balancer。

> 負載平衡（Load Balancing）：以往可以透過外部資源（如 AWS ELB）把流量分配給不同機器；Kubernetes 提供的 Ingress Controller，讓我們能在 Cluster 內部自己實現 Load Balancing，不需依賴外部資源。

### 1. 建立 Hello World Application

```yaml
# helloworld-pod.yaml
apiVersion: v1
kind: Pod
metadata:
  name: helloworld-pod
  labels:
    app: helloworld-pod
    tier: backend
spec:
  containers:
  - name: api-server
    image: zxcvbnius/docker-demo
    ports:
    - containerPort: 3000
```

```yaml
# helloworld-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: helloworld-service
spec:
  ports:
  - port: 3000
    protocol: TCP
    targetPort: 3000
  selector:
    app: helloworld-pod
```

```bash
$ kubectl create -f ./helloworld-pod.yaml
pod "helloworld-pod" created

$ kubectl create -f ./helloworld-service.yaml
service "helloworld-service" created
```

### 2. 建置 Ingress Controller：直接用 minikube 內建 addon

原文示範的做法，是照著 ingress-nginx 官方 `deploy` 資料夾的 README，手動 `kubectl apply` 好幾個分散的 yaml（namespace、default backend、ConfigMap、Controller 本身）：

```bash
# 原文（2018 年）的做法——namespace.yaml / default-backend.yaml / configmap.yaml /
# tcp-services-configmap.yaml / udp-services-configmap.yaml / without-rbac.yaml
$ curl https://raw.githubusercontent.com/kubernetes/ingress-nginx/master/deploy/namespace.yaml \
  | kubectl apply -f -
# ...（以下省略，原理同上）
```

> **勘誤（安裝方式已失效）**：上面這種「分成好幾個檔案，一個個 `curl | kubectl apply`」的方式現在**全部會失敗（curl 404）**。ingress-nginx 官方後來把所有元件整併成**單一一份安裝 YAML**，原文那些拆開的路徑（`namespace.yaml`、`default-backend.yaml`、`configmap.yaml`、`without-rbac.yaml`⋯）已經全數失效、不要再照著執行。
>
> 這份筆記的環境是 **minikube**，可以完全跳過上面手動 apply 的步驟，直接用內建 addon 一行指令搞定：
>
> ```bash
> $ minikube addons enable ingress
> ingress was successfully enabled
> ```
>
> 執行後，minikube 就會自動幫你把**最新版的 Ingress Controller、ConfigMap、Service、RBAC 全部安裝好**，不用擔心裝到過期或失效的元件——這也是這份筆記後續操作實際採用的方式。若不是 minikube、而是正式雲端 Cluster（AWS/GCP/Azure），才需要去查 [ingress-nginx 官方最新的安裝文件](https://kubernetes.github.io/ingress-nginx/deploy/)，用現行版本的單一安裝 YAML。

安裝完後，可以用以下指令確認：

```bash
$ kubectl get all -n ingress-nginx   # 確認 ingress-nginx namespace 底下的物件都 Ready
```

### 3. 建立 Helloworld Ingress

```yaml
# helloworld-ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: helloworld-ingress
  namespace: default
spec:
  rules:
  - host: helloworld.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: helloworld-service
            port:
              number: 3000
```

把打向 `helloworld.example.com` 的請求都轉到 `helloworld-service`。

### 4. 取得 minikube IP，設定本機端 hosts

```bash
$ minikube ip
192.168.99.100
```

編輯本機的 `/etc/hosts`（macOS / Linux），把 `helloworld.example.com` 指向剛剛查到的 minikube IP，讓本機查詢這個網域時，會被導到 minikube 的 IP address。

### 5. Demo

瀏覽器打開 `http://helloworld.example.com/`，會看到回傳 `Hello World!`，代表 `helloworld-ingress` 成功把流量導到 `helloworld-pod`。若改打一個沒有設定的路徑／網域，Ingress Controller 會回傳先前建立的 `default-backend`（`default backend - 404`）。

## 關係圖：Service 直接曝露 vs. Ingress 統一入口

```
【沒有 Ingress：每個 Service 各自佔用一個對外 port，Node 防火牆要開多個洞】
外部使用者
  │
  ├──▶ <NodeIP>:30001 ──▶ Service A ──▶ Pod A
  ├──▶ <NodeIP>:30002 ──▶ Service B ──▶ Pod B
  └──▶ <NodeIP>:30003 ──▶ Service C ──▶ Pod C

【有 Ingress：只開一個對外入口，由 Ingress 規則決定導去哪個 Service】
外部使用者
  │  打 http://helloworld.example.com/
  ▼
┌──────────────────────────────────────────┐
│ Ingress Controller（Nginx，本身是一個 Pod/  │  ← 真正做負載平衡、轉發的元件
│ Deployment，運行在 ingress-nginx namespace） │
└──────────────────────────────────────────┘
        │  依 Ingress 規則（host / path）比對
        ▼
┌──────────────────────────────────────────┐
│ Ingress: helloworld-ingress                │  ← 只是規則設定檔，本身不轉發流量
│   host: helloworld.example.com             │
│   → serviceName: helloworld-service        │
│   → servicePort: 3000                      │
└──────────────────────────────────────────┘
        │
        ▼
   Service: helloworld-service（port 3000 → targetPort 3000）
        │
        ▼
   Pod: helloworld-pod（containerPort 3000）
```

## 我的想法

- 這天解決的是 [Day 9](#day-9) NodePort 疊層關係圖裡最外層的痛點：NodePort 讓每個 Service 都要在 Node 上單獨佔一個實體 port（30000~32767 範圍內），Service 一多，port 管理跟防火牆規則就跟著爆炸。Ingress 把這個問題收斂成「只開一個入口，規則寫在 yaml 裡」，是**管理面**的優化，不是取代 Service——最終流量還是會落到 Service → Pod 這條路徑上（見上圖）。
- 容易搞混的一點：**`Ingress` 物件本身只是規則設定檔，不會憑空產生負載平衡能力**，必須額外部署 `Ingress Controller`（Nginx / GCE）這個真正在跑的元件來讀取、執行這些規則。這跟 [Day 8](#day-8) Deployment 需要靠 Replica Set 才能實際管理 Pod 的分工模式很像：一個是「宣告規則」，一個是「執行規則」。
- Ingress 是這系列筆記裡第一個**因為 API 版本太舊而直接跑不動**的元件（`extensions/v1beta1` 已被移除，見上方勘誤）。這提醒了一件事：像 Deployment（`apps/v1beta2` → `apps/v1`）、Ingress 這種還在快速演進的資源，**yaml 裡的 `apiVersion` 有沒有過期，是實際動手前就該先用 `kubectl api-resources` 或 `kubectl explain <kind>` 確認的事**，不能照抄教學文章的版本號。
- 不只是 yaml 內容會過期，**安裝步驟本身也會過期**：原文手動 `curl` 拆開的多個 ingress-nginx 部署檔案，路徑早就 404 了（官方已整併成單一安裝檔）。這種「第三方元件的官方安裝方式」比 K8s 核心資源的 `apiVersion` 變動更頻繁，遇到教學文章的安裝指令跑不動時，優先找**平台本身有沒有現成的 addon**（像 minikube 的 `addons enable`）通常比硬查官方最新安裝路徑更省事、也更不容易裝到過期版本。

## 小結

- Ingress 讓多個 Service 共用**一個對外 port**，並可依路徑或 domain name 決定導流目標，也支援 SSL termination。
- Ingress 本身**不提供負載平衡**，需要搭配 `Ingress Controller`（本篇示範 Nginx）才能真正在 Cluster 內部實現 Load Balancing，取代外部資源（如 AWS ELB）。
- Ingress Controller 目前仍有一些已知 issue，正式導入前建議先詳讀官方 README。
- **API 版本勘誤**：本篇所有 Ingress yaml 已從原文的 `extensions/v1beta1` 更新為現行的 `networking.k8s.io/v1`（`backend.serviceName/servicePort` → `backend.service.name/port.number`，並新增必填的 `pathType`），可對照 [`demo-ingress/ingress-example-1.yaml`](demo-ingress/ingress-example-1.yaml) 驗證。
- **安裝方式勘誤**：原文手動 `curl` 拆開的多個 ingress-nginx 部署 yaml（`namespace.yaml`/`default-backend.yaml`/`configmap.yaml`/`without-rbac.yaml`⋯）路徑已全數失效，官方已整併成單一安裝檔。這份筆記的環境（minikube）改用 `minikube addons enable ingress` 一行指令安裝，等同於裝好最新版的 Ingress Controller、ConfigMap、Service、RBAC。

# Day 20

> 參考來源：[[Day 20] 如何保存 Container 中資料 - Volumes](https://ithelp.ithome.com.tw/articles/10196428)

## 前言：為什麼需要 Volumes

前面幾天用到的 Pod 都是 [Stateless](#day-13) 的：**container 儲存的資料，會隨著 container 的生命週期消失而一併消失**，這也是 [Day 13](#day-13) 尾聲留下的坑——「Stateless Wordpress」在後台編輯過的內容，一旦 Pod crash 或被刪除就全部遺失。今天要介紹的 `Volumes`，就是用來打造 **Stateful** Pod 的機制：即便 Pod 中的 container 因故 crash，資料仍可完整保存，讓新產生的 container 能接續使用。

今天筆記涵蓋：

- 介紹什麼是 Volumes（四種常用類型）
- 實作：在 AWS Kubernetes Cluster 上綁定 AWS EBS Volumes

> 範例程式碼可參考原文附的 [demo-volumes](https://github.com/zxcvbnius/k8s-30-day-sharing/blob/master/Day20/demo-volumes)。

## 什麼是 Volumes

`Volumes` 是 Kubernetes Cluster 中專門用來**儲存資料**的地方，不只能把 container 的資料保存下來，也能透過**掛載（mounting）**的方式供多個 Pod 同時存取。Kubernetes 支援非常多種 Volume 類型，今天筆記介紹四種常用的：`emptyDir`、`hostPath`、Cloud Storage、NFS。

### emptyDir

每建立一個新 Pod，Kubernetes 就會在該 Pod 裡建立一個 `emptyDir`，**該 Pod 中所有 container 都可以讀寫這個目錄**。當 Pod 從 Node 中被移除時，`emptyDir` 也會隨之消失。常見用途：

- **暫時性儲存空間**：某些應用程式運行時需要臨時、無需永久保存的資料夾。
- **共用儲存空間**：同一 Pod 內所有 container 都能讀寫 `emptyDir`，可當作這些 container 的共用目錄（跟 [Day 6](#day-6)、[Day 13](#day-13) 提過的「同 Pod 內 container 共用網路可用 `localhost` 溝通」是類似概念，只是這裡共用的是檔案系統而非網路）。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: test-pd
spec:
  containers:
  - image: k8s.gcr.io/test-webserver
    name: test-container
    volumeMounts:
    - mountPath: /cache
      name: cache-volume
  volumes:
  - name: cache-volume
    emptyDir: {}
```

### hostPath

在 Pod 上掛載 **Node** 的資料夾或檔案。**`hostPath` 的生命週期與 Node 相同**：Pod 因故重啟時，檔案仍保存在 Node 的檔案系統底下，直到該 Node 物件被 Kubernetes Cluster 移除，資料才會消失。

```yaml
# hostpath-example.yaml
apiVersion: v1
kind: Pod
metadata:
  name: apiserver
spec:
  containers:
  - name: apiserver
    image: zxcvbnius/docker-demo
    volumeMounts:
    - mountPath: /tmp
      name: tmp-volume
    imagePullPolicy: Always
  volumes:
  - name: tmp-volume
    hostPath:
      path: /tmp
      type: Directory
```

這個 yaml 把 **Node 的 `/tmp` 掛在 `apiserver` 的 `/tmp` 下**，兩者存取相同資源：apiserver 的 `/tmp` 新增檔案，可以從 Node 的 `/tmp` 底下找到同一個檔案。

```bash
$ kubectl create -f ./hostpath-example.yaml
pod "apiserver" created
```

進到 `apiserver` 的 shell 中，在 `/tmp` 新增一個 `test.txt`；接著進到 `minikube` 的 shell（`minikube ssh`），可以在 Node 的 `/tmp` 底下找到同一個 `test.txt`。若該 Pod 被刪除，檔案仍會保存在 Node 的 `/tmp/test.txt` 中，供新的 Pod 物件使用。

### Cloud Storage

Kubernetes 也支援 AWS EBS、Google Disk、Microsoft Azure Disk 等雲端硬碟類型的 Volumes；今天的實作會示範如何把 AWS EBS 掛載在（架設於 AWS 的）Kubernetes Cluster 的 Pod 上。

### NFS（Network FileSystem）

```yaml
# nfs-example.yaml
apiVersion: v1
kind: Pod
metadata:
  name: apiserver
spec:
  containers:
  - name: apiserver
    image: zxcvbnius/docker-demo
    ports:
      - name: api-port
        containerPort: 3000
    volumeMounts:
      - name: nfs-volumes
        mountPath: /tmp
  volumes:
  - name: nfs-volumes
    nfs:
      server: {YOUR_NFS_SERVER_URL}
      path: /
```

> 更多 Kubernetes NFS 範例可參考[該連結](https://github.com/kubernetes/examples/tree/master/staging/volumes/nfs)。

## 實作：在 AWS Kubernetes Cluster 上綁定 AWS EBS Volumes

> 若還不熟悉怎麼在 AWS 上架設 Kubernetes，可先參考原文的 [Day 15] 介紹 kops 系列文章。

**1. 用 `aws-cli` 建立一個 1GB 的 EBS（Oregon 區域）**

```bash
$ aws ec2 create-volume \
  --size 1 \
  --region us-west-2 \
  --availability-zone us-west-2a \
  --volume-type gp2

{
    "VolumeId": "vol-0b29e0a08749ccef3",
    "SnapshotId": "",
    "Size": 1,
    "VolumeType": "gp2",
    "State": "creating",
    "Iops": 100,
    "CreateTime": "2018-01-08T04:38:58.885Z",
    "AvailabilityZone": "us-west-2a",
    "Encrypted": false
}
```

AWS 提供 5 種不同類型的 Volumes，這裡使用**一般用途的 SSD（gp2）**。可以在 AWS Console 的 EC2 頁面，或用 `aws ec2 describe-volumes --region us-west-2` 查詢剛建立的 EBS 詳細資料。

**2. 建立 Pod，掛載該 EBS**

```yaml
# aws-ebs-example.yaml
apiVersion: v1
kind: Pod
metadata:
  name: apiserver
spec:
  containers:
  - name: apiserver
    image: zxcvbnius/docker-demo
    ports:
      - name: api-port
        containerPort: 3000
    volumeMounts:
      - name: aws-ebs-volumes
        mountPath: /tmp
  volumes:
  - name: aws-ebs-volumes
    awsElasticBlockStore:
      # replace to your volumeID
      volumeID: vol-0b29e0a08749ccef3
```

這裡希望 `vol-0b29e0a08749ccef3` 掛載在 `apiserver` 的 `/tmp` 資料夾底下。

```bash
$ kubectl create -f ./aws-ebs-example.yaml
pod "apiserver" created

$ kubectl describe pod apiserver
...
Volumes:
  aws-ebs-volumes:
    Type:       AWSElasticBlockStore
    VolumeID:   vol-0b29e0a08749ccef3
```

`kubectl describe` 的 `Volumes` 欄位可以看到掛載的 `vol-0b29e0a08749ccef3`。之後在 `apiserver` 的 `/tmp` 底下新增或修改的檔案都會存放在 EBS 中，即便 `apiserver` 這個 Pod 不存在了，下次新建的 Pod 一樣可以從 `vol-0b29e0a08749ccef3` 找回資料。

**限制**：**AWS EBS 只能被綁定在 EC2 上**，也就是 Node 一定要架設在 AWS 上，才能綁定 EBS。

> **勘誤（in-tree volume plugin 已淘汰）**：原文示範的 `volumes.awsElasticBlockStore` 寫法屬於 Kubernetes **in-tree（內建）volume plugin**，自 Kubernetes 1.17 起已標示為 deprecated，並自 1.23 起預設透過 **CSI migration** 機制在背後轉譯給 [AWS EBS CSI Driver](https://github.com/kubernetes-sigs/aws-ebs-csi-driver) 處理；較新版本的 Cluster（尤其是 EKS 1.23+）需要額外安裝 `aws-ebs-csi-driver` 這個 add-on，`awsElasticBlockStore` 欄位才能正常運作。這也是這系列筆記另一個「yaml 語法還能寫、但背後執行方式已經演進」的例子，跟 [Day 19](#day-19) Ingress API 版本、安裝方式過期是同一類坑，實際操作前建議查對應 Cluster 版本的官方文件。
>
> 另外，這一天的實作**需要真實架在 AWS 上的 Kubernetes Cluster**（EBS 只能掛給同區域的 EC2 Node），無法直接在本機 minikube 上重現，這點與前面幾天大多可以純用 minikube 操作不同。

## 我的想法

- 這天正式補上 [Day 13](#day-13) 尾聲留下的坑：Stateless Wordpress 資料不持久化的問題，答案就是 `Volumes`——只要把 MySQL 的資料目錄改成掛載 `hostPath` 或 Cloud Storage（如 AWS EBS），Pod 重建後資料依然存在，就能把「Stateless Wordpress」升級成「Stateful Wordpress」。
- `emptyDir` / `hostPath` / Cloud Storage 三者的生命週期是一條漸進的光譜：`emptyDir` 跟著 **Pod** 生滅（最短命）、`hostPath` 跟著 **Node** 生滅（中等）、Cloud Storage（如 AWS EBS）則完全獨立於 Pod 和 Node 之外，只要不手動刪除就會一直存在（最持久）。选型時要依「這份資料需要活多久」來決定用哪一種。
- `volumes` + `volumeMounts` 這套掛載機制，跟 [Day 12](#day-12) Secret、[Day 18](#day-18) ConfigMap 掛載成檔案的寫法完全同構（`volumes[].name` ↔ `volumeMounts[].name` 對應），只是這次 `volumes[]` 底下換成 `emptyDir` / `hostPath` / `awsElasticBlockStore` / `nfs` 等不同的資料來源類型而已——理解了其中一種掛載方式，其餘幾種幾乎是直接代換。

## 小結

- `Volumes` 讓 container 的資料能在 Pod／Node 重建後依然保留，是把 Stateless 應用改造成 Stateful 應用的關鍵機制。
- 四種常用類型：`emptyDir`（隨 Pod 生滅，可當暫存或同 Pod 內 container 共用空間）、`hostPath`（隨 Node 生滅）、Cloud Storage（如 AWS EBS，獨立於 Pod/Node 之外，但只能掛給同雲端服務商的機器）、`NFS`。
- 本篇實作示範用 `aws-cli` 建立 AWS EBS，再透過 `volumes.awsElasticBlockStore` 掛載到 Pod；**原文所用的 in-tree plugin 寫法目前已 deprecated，新版 Cluster 需搭配 AWS EBS CSI Driver 才能運作**（見上方勘誤）。
- 下一篇（Day 21）主題：`Storage Class` 與 `PersistentVolumeClaim`——不必再透過 `aws-cli` 等外部指令手動建立 Volume，而是能用 `kubectl` 搭配 YAML 設定檔動態產生所需的 Volumes，對管理多個 Volumes 更有幫助。

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
| Utilize persistent and ephemeral volumes | Volume 的使用 | [Day 20](#day-20)（`emptyDir`/`hostPath`/Cloud Storage/`NFS` 四種常用類型、`volumes`+`volumeMounts` 掛載機制，尚未涉及 `PersistentVolume`/`PersistentVolumeClaim`/`StorageClass`） |

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
| ConfigMaps | 設定值管理 | [Day 18](#day-18)（`kubectl create configmap`、`--from-file`/`--from-literal`、`volumes.configMap` 掛載成檔案） |
| Secrets | 機敏資料管理 | [Day 12](#day-12)（`kubectl create secret`、YAML+base64、環境變數／volume 掛載，尚未涉及搭配 Service Account 限制存取） |
| ServiceAccounts | 服務帳號 | 尚未涉及 |
| SecurityContexts / Capabilities | 安全性設定 | 尚未涉及 |

## 20% - Services and Networking

| 知識點 | 內容 | 對應 Day |
| --- | --- | --- |
| NetworkPolicies | 網路流量控管規則 | 尚未涉及 |
| 建立與除錯 Service 存取 | 透過 Service 曝露應用、排除連線問題 | [Day 5](#day5)（`kubectl expose`、NodePort、Port Mapping 架構圖）、[Day 6](#day-6)（kube-proxy / iptables 如何決定流量轉發）、[Day 9](#day-9)（Service YAML 完整欄位、`ClusterIP`/`NodePort`/`LoadBalancer` 三種類型、Dynamic Cluster IP、NodePort Range 限制）、[Day 10](#day-10)（Service 的 `selector` 底層就是 Labels 篩選機制）、[Day 17](#day-17)（`kube-dns`：Pod 之間透過 Service 名稱互相溝通，不受 Cluster IP 動態變動影響） |
| Ingress | 對外路由規則 | [Day 19](#day-19)（Ingress 依路徑/domain name 導流、SSL termination、Ingress Controller 實現負載平衡） |

## 小結

- 已涵蓋：workload resource 概念（Day 7 Replication Controller、Day 8 Replica Set / Deployment）、Deployment 的 rollout / rollback（Day 8）、Service 完整概念與三種類型（Day 5、Day 6、Day 9）、DNS-based Service Discovery（Day 17 `kube-dns`）、基本 CLI 監控指令、Probes / health checks 的 `livenessProbe`（Day 11，尚缺 readiness／startup probe）、Secrets 基本建立與掛載方式（Day 12，尚缺 Service Account 限制存取）、ConfigMaps（Day 18）、Ingress / Ingress Controller（Day 19）、Volumes 基本類型與掛載機制（Day 20，尚缺 PersistentVolume/PersistentVolumeClaim/StorageClass）。
- Services and Networking 這個 Domain（20%）目前只剩 `NetworkPolicies` 尚未涉及，其餘知識點已有不錯的覆蓋。
- **Day 10 補充說明**：Labels / Selector 是貫穿多個考點的底層機制（workload resource 的 `selector`、Service 的 `selector` 都靠它），本身不是獨立的考綱條目，但值得作為理解其他考點的基礎；而 `nodeSelector`（Pod 排程到特定 Node）**不在目前 CKAD 官方考綱的 5 大 Domain 內**，比較屬於 CKA 的範疇，準備 CKAD 可以降低這部分的優先度。
- **Day 18 補充說明**：ConfigMap 與 [Day 12](#day-12) Secret 是同一套掛載機制（`volumes` + `volumeMounts`），差別在機密／非機密資料，考試時容易混淆兩者該用哪一個，記住「機密用 Secret、非機密部署配置用 ConfigMap」即可。
- **Day 19 補充說明**：`Ingress` 只是規則設定檔，真正負責轉發、負載平衡的是額外部署的 `Ingress Controller`，兩者是「宣告 vs. 執行」的分工——這跟 [Day 8](#day-8) Deployment 需要靠 Replica Set 才能實際管理 Pod 是同樣的分工模式，考試時要留意兩者缺一不可。
- **Day 20 補充說明**：`emptyDir`/`hostPath`/`awsElasticBlockStore`/`nfs` 全都是套用同一組 `volumes` + `volumeMounts` 掛載機制（跟 [Day 12](#day-12) Secret、[Day 18](#day-18) ConfigMap 掛載成檔案完全同構），差別只在 `volumes[]` 底下資料來源的類型與生命週期長短；CKAD 考綱這裡真正的重點其實是**下一篇（Day 21）** 的 `PersistentVolume` / `PersistentVolumeClaim`（這幾天示範的都是直接在 Pod 裡宣告 Volume，屬於較底層的用法，實務與考試更常見的是透過 PVC 動態要資源）。
- 佔分最重（25%）的 Environment/Config/Security Domain 目前已有 Secrets（Day 12）與 ConfigMaps（Day 18）兩塊，其餘 CRD/Operators、Authentication/Authorization、Requests/limits/quotas、ServiceAccounts、SecurityContexts 仍尚未涉及，加上部署策略（blue/green、canary）、Helm、Kustomize、readiness/startup probe、NetworkPolicies 等，是後續應優先加強的重點。
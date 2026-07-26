
# Overview

本筆記記錄 Kubernetes 學習歷程，目前包含以下章節：

- [Day 5](#day5) - Pod 與 Container 互動、Service 網路曝露
- [Day 6](#day-6) - Node 概念與 Kubernetes 內部運作
- [Day 7](#day-7) - Replication Controller 與 Pod 橫向擴展
- [Day 8](#day-8) - Replica Set 與 Deployment（Rollout / Rollback）
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
| Choose and use the right workload resource（Deployment、DaemonSet、CronJob 等） | 依需求選擇合適的 workload 物件來管理 Pod | [Day 7](#day-7)（Replication Controller）、[Day 8](#day-8)（Replica Set、Deployment） |
| Multi-container Pod design patterns（sidecar、init 等） | 同一 Pod 內多個 container 協作的設計模式 | [Day 6](#day-6)（提到同 Pod 內 container 可用 `localhost` 溝通，但尚未介紹 sidecar / init pattern） |
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
| Probes / health checks | liveness、readiness、startup probe | 尚未涉及 |
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
| Secrets | 機敏資料管理 | 尚未涉及 |
| ServiceAccounts | 服務帳號 | 尚未涉及 |
| SecurityContexts / Capabilities | 安全性設定 | 尚未涉及 |

## 20% - Services and Networking

| 知識點 | 內容 | 對應 Day |
| --- | --- | --- |
| NetworkPolicies | 網路流量控管規則 | 尚未涉及 |
| 建立與除錯 Service 存取 | 透過 Service 曝露應用、排除連線問題 | [Day 5](#day5)（`kubectl expose`、NodePort、Port Mapping 架構圖）、[Day 6](#day-6)（kube-proxy / iptables 如何決定流量轉發，有助於理解 Service 連線原理） |
| Ingress | 對外路由規則 | 尚未涉及 |

## 小結

- 已涵蓋：workload resource 概念（Day 7 Replication Controller、Day 8 Replica Set / Deployment）、Deployment 的 rollout / rollback（Day 8）、Service 基礎操作與底層原理（Day 5、Day 6）、基本 CLI 監控指令。
- 佔分最重（25%）的 Environment/Config/Security 幾乎完全尚未涉及，加上部署策略（blue/green、canary）、Helm、Kustomize、Probes 等，是 Day 9 之後應優先加強的重點。
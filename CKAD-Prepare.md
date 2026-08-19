# CKAD 考古題練習記錄

本文件記錄「CKAD 20 題考古題」教材的練習過程，與 `Record.md`（原教學系列逐日筆記）分開記錄。目前進度：

- [公用知識](#公用知識)
- [題目1 - CronJob 手動觸發 Job](#題目1---cronjob-手動觸發-job)
- [題目2 - CronJob 建立（不需手動觸發）](#題目2---cronjob-建立不需手動觸發)
- [題目3 - 用 Dockerfile 建置並匯出 OCI 格式 image](#題目3---用-dockerfile-建置並匯出-oci-格式-image)
- [題目4 - 建立指定 CPU/記憶體 resource requests 的 Pod](#題目4---建立指定-cpu記憶體-resource-requests-的-pod)
- [題目5 - 修正 Deployment 的記憶體 requests/limits（依 namespace LimitRange）](#題目5---修正-deployment-的記憶體-requestslimits依-namespace-limitrange)
- [題目7 - 金絲雀部署（Canary Deployment）](#題目7---金絲雀部署canary-deployment)
- [題目8 - 修改 Deployment 的 SecurityContext（runAsUser / allowPrivilegeEscalation）](#題目8---修改-deployment-的-securitycontextrunasuser--allowprivilegeescalation)
- [題目9 - 建立 Deployment 並指定環境變數](#題目9---建立-deployment-並指定環境變數)
- [題目10 - RBAC 授權除錯（ServiceAccount 權限不足）](#題目10---rbac-授權除錯serviceaccount-權限不足)
- [題目11 - 建立 ConfigMap 並掛載成 Volume](#題目11---建立-configmap-並掛載成-volume)
- [題目12 - 建立 Secret 並以環境變數使用](#題目12---建立-secret-並以環境變數使用)

## 公用知識

- `kubectl config get-contexts`：列出目前 kubeconfig 裡所有可用的 context
- `kubectl config use-context k8s`：切換到指定 context（範例用 `k8s`）
- `kubectl config set-context k8s --namespace=pod-resource`
- （未來陸續補充的通用指令都放這裡）

### `containerPort` vs Service 的 `port` / `targetPort`

同一個字「port」在不同層級代表不同東西，是 Service 相關題目最容易搞混的地方（完整圖解見 [Record.md Day 13](Record.md#day-13)）：

| 欄位 | 在哪裡宣告 | 意義 |
| --- | --- | --- |
| `containerPort` | Deployment/Pod 的 `containers[].ports` | 宣告 container **實際監聽**哪個 port，比較偏文件用途；不寫也不影響流量能不能打進去 |
| `Service.spec.ports[].port` | Service | Client 連這個 Service 要打的 port |
| `Service.spec.ports[].targetPort` | Service | Service 收到流量後**實際轉發到 Pod 的哪個 port**——這個才要對到 container 真正監聽的 port，沒寫預設等於 `port` |

- `port` 跟 `targetPort` 可以不同（例如對外 `port: 80`、實際轉給 Pod 的 `targetPort: 8080`）
- 只宣告 `containerPort`、沒建 Service 的題目（例如 [題目9](#題目9---建立-deployment-並指定環境變數)），單純就是文件宣告，不用多想要不要建 Service

## 題目1 - CronJob 手動觸發 Job

**題目敘述**：

現有一個 CronJob `ppi`，需要手動建立一次性的 Job 來立即執行，不用等排程時間到，命名為 `ppi-test`。

**相關資源**：[CKAD/cronjob-1.yaml](CKAD/cronjob-1.yaml)

**解法指令**：

```bash
kubectl create job ppi-test --from=cronjob/ppi
```

**對應考綱 Domain**：

`Application Design and Build`（20%）→ `Choose and use the right workload resource`（CronJob 是這個知識點下 `Record.md` CKAD TEST 章節目前還沒涉及到的 workload 類型，這題正好補上）

**易錯點／踩坑筆記**：

- `kubectl create job --help` 可查到 `--from=cronjob/<name>` 的用法，考試時忘記語法可以現查
- `--from` 是直接複製 CronJob 的 `jobTemplate` 建立一次性 Job，不受 `schedule` 排程限制，也不會影響原本 CronJob 的排程繼續運作

## 題目2 - CronJob 建立（不需手動觸發）

**題目敘述**：

跟題目1 情境類似（建立一個 CronJob），但這次不需要額外手動觸發 Job，只要照規格建立好 CronJob，讓它依 `schedule` 自動排程執行即可。

**相關資源**：[CKAD/cronjob-2.yaml](CKAD/cronjob-2.yaml)

**解法指令**：

```bash
kubectl apply -f CKAD/cronjob-2.yaml
```

**對應考綱 Domain**：

`Application Design and Build`（20%）→ `Choose and use the right workload resource`（同題目1，這題練習的是最基本的 CronJob 建立方式，不涉及手動觸發 Job 的額外指令）

**易錯點／踩坑筆記**：

- 這題的 `activeDeadlineSeconds: 10` 放在 `jobTemplate.spec.template.spec`（Pod 層級），跟題目1 放在 `jobTemplate.spec`（Job 層級）位置不同——兩者都是合法欄位但語意不同：Job 層級是「整個 Job 從建立起算的存活時間上限」，Pod 層級是「這個 Pod 從啟動起算的存活時間上限」，考試讀 yaml 時要留意欄位縮排在哪一層
- `restartPolicy: OnFailure` 跟題目1 的 `Never` 不同，代表 container 失敗時 kubelet 會在同一個 Pod 內重啟 container，而不是讓 Job controller 建立新 Pod

## 題目3 - 用 Dockerfile 建置並匯出 OCI 格式 image

**題目敘述**：

已存在一個 Dockerfile 於 `/ckad/DF/Dockerfile`。

1. 使用該 Dockerfile 建置一個名為 `centos`、標籤為 `8.2` 的 image（系統預裝了 docker、skopeo、buildah、img、podman 等多種工具可自行選用）。**不要** push 到 registry、**不要**執行 container、**不要**以其他方式使用它。
2. 以 **OCI 格式**匯出建好的 image，存到 `/ckad/DF/centos-8.2.tar`。

> 這題實際考試時要先切換到對應的 cluster/node 才能執行，模擬環境不需要切換。

**相關資源**：`/ckad/DF/Dockerfile`（考場既有檔案，非本專案內容）

**解法指令**：

```bash
cd /ckad/DF
sudo docker build -t centos:8.2 .
sudo docker save centos:8.2 > /ckad/DF/centos-8.2.tar
```

**對應考綱 Domain**：

`Application Design and Build`（20%）→ `Define, build and modify container images`（這是筆記系列裡第一次涉及這個知識點）

**易錯點／踩坑筆記**：

- 選擇只用 `docker`（build + save）而不用 `skopeo copy` 轉檔，是因為**不能保證考試環境一定有裝 skopeo**，只依賴系統一定會有的工具比較保險——這題「系統預裝了多種工具可自行選用」的用意就是讓考生挑一個自己有把握、且確定可用的組合，不用堅持湊出「最標準」的解法
- 要留意：`docker save` 匯出的嚴格來說是 **Docker 自家的 image archive 格式**（`manifest.json` + `repositories`），跟 `skopeo`/`buildah push oci-archive:` 產生的**標準 OCI archive 格式**（`index.json` + `oci-layout`）不完全相同；如果考試評分是嚴格檢查 `oci-layout` 這類 OCI 規格檔案，`docker save` 可能不算過關，實際考場如有餘裕可以用 `docker manifest inspect` 或解壓 tar 確認內容物、或改用 `podman save --format oci-archive` 這種同樣不依賴額外工具、但明確聲明 OCI 格式的指令來對照
- `sudo` 是因為 docker daemon 通常需要 root 權限操作（除非有另外設定 rootless docker 或把使用者加進 `docker` 群組）
- 題目明確要求「不要 push、不要 run、不要以其他方式使用」，build 完千萬別手滑多打 `docker run` 或 `docker push`，考試會直接扣分
- image 名稱與標籤要精確符合 `centos:8.2`，大小寫、冒號位置都不能錯

## 題目4 - 建立指定 CPU/記憶體 resource requests 的 Pod

**Quick Reference**：

- Cluster/配置環境：`k8s`
- Namespace：`pod-resources`

**題目敘述**：

> ⚠️ 必須先切換到正確的 Cluster/配置環境（`kubectl config use-context k8s`），不這樣做可能導致零分。

在現有的 namespace `pod-resources` 中建立一個名為 `nginx-resources` 的 Pod。使用 `nginx:1.16` 映像檔指定一個容器，為其容器指定 `40m` 的 CPU 和 `50Mi` 的記憶體的資源請求（resource requests）。

**相關資源**：[CKAD/04-pod-resource-1.yaml](CKAD/04-pod-resource-1.yaml)

**解法指令**：

```bash
kubectl apply -f CKAD/04-pod-resource-1.yaml
```

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: nginx-resources
  namespace: pod-resources
spec:
  containers:
  - name: app
    image: nginx:1.16
    resources:
      requests:
        memory: "50Mi"
        cpu: "40m"
```

**對應考綱 Domain**：

`Application Environment, Configuration and Security`（25%）→ `Requests/limits/quotas`、`定義資源需求（resource requirements）`（延續 [Record.md Day 25](Record.md#day-25) 學過的 `resources.requests.cpu`，這題再加上 `resources.requests.memory`）

**易錯點／踩坑筆記**：

- 題目沒有指定容器名稱，可以自訂（這裡用 `app`），但 Pod 名稱 `nginx-resources`、namespace `pod-resources`、image `nginx:1.16` 都是題目明確要求，一個字都不能改
- CPU 用 `40m`（millicpu，等於 0.04 顆核心）、記憶體用 `50Mi`（Mebibyte）；`m` 是 CPU 專屬單位，記憶體則用 `Mi`/`Gi`（二進位）或 `M`/`G`（十進位），兩者單位系統不能混用
- 這題只要求 `requests`，沒有要求 `limits`，不要多加，避免跟題目要求不符
- namespace 是「已存在」的（`pod-resources`），不用自己建立，用錯 namespace 是這類題目最常見的扣分點——建議先 `kubectl config set-context --current --namespace=pod-resources` 切換預設 namespace，或是在 yaml/指令裡明確帶 `-n pod-resources` / `namespace:` 欄位，避免建到 `default`

## 題目5 - 修正 Deployment 的記憶體 requests/limits（依 namespace LimitRange）

**Quick Reference**：

- Cluster/配置環境：`k8s`
- Namespace：`haddock`

**題目敘述**：

> ⚠️ 必須先切換到正確的 Cluster/配置環境（`kubectl config use-context k8s`），不這樣做可能導致零分。

`haddock` namespace 中名為 `nosql` 的 Deployment 的 Pod 因其容器已用完資源而無法啟動。請更新 `nosql` Deployment，使 Pod：

- 為其容器請求 `15Mi` 的記憶體
- 將記憶體限制設為 `haddock` namespace 設置的**最大記憶體容量的一半**

`nosql` Deployment 的配置清單可在 `/ckad/chief-cardinal/nosql.yaml` 找到。

**相關資源**：[CKAD/limitrange.yaml](CKAD/limitrange.yaml)（自建的練習用 `LimitRange`，模擬考場 `haddock` namespace 既有的設定）、[CKAD/05-nosql.yaml](CKAD/05-nosql.yaml)（模擬考場 `/ckad/chief-cardinal/nosql.yaml`）

**解法指令**：

```bash
kubectl config use-context k8s

# 1. 查 haddock namespace，一次看到 LimitRange 與 ResourceQuota 兩種限制
kubectl describe ns haddock
```

`kubectl describe ns haddock` 輸出裡的 `Limits` 區塊會列出這個 namespace 的 `LimitRange` 規則，例如（依 [CKAD/limitrange.yaml](CKAD/limitrange.yaml) 練習範例）：

```
Type       Resource  Min  Max   Default Request  Default Limit  Max Limit/Request Ratio
----       --------  ---  ---   ---------------  -------------  -----------------------
Container  memory    -    40Mi  8Mi              16Mi           -
```

查到 `Max` = `40Mi`，所以 `limits.memory` = `40Mi ÷ 2` = `20Mi`。接著把 `requests.memory: 15Mi`、`limits.memory: 20Mi` 補進 `nosql` Deployment：

```bash
kubectl set resources deployment nosql -n haddock \
  --requests=memory=15Mi \
  --limits=memory=20Mi

# 確認 rollout 套用成功、Pod 恢復 Running
kubectl rollout status deployment/nosql -n haddock
```

**對應考綱 Domain**：

`Application Environment, Configuration and Security`（25%）→ `Requests/limits/quotas`（延續 [題目4](#題目4---建立指定-cpu記憶體-resource-requests-的-pod) 的 `requests`，這題多了 `limits`，而且 `limits` 的數值不是題目直接給定的常數，而是要動態查詢 namespace 的 `LimitRange` 才能算出來，是目前筆記裡第一次碰到 `LimitRange`）

**易錯點／踩坑筆記**：

- **`kubectl describe ns <namespace>` 是這題的核心指令**：一次可以看到該 namespace 的 `LimitRange`（`Limits` 區塊）跟 `ResourceQuota`（`Resource Quotas` 區塊），不用分別下 `kubectl describe limitrange` 跟 `kubectl describe resourcequota` 兩次指令，考試時間有限，這樣查最快
- 這題的關鍵是先搞懂 `LimitRange` 跟 [Record.md Day 27](Record.md#day-27) 學過的 `ResourceQuota` 不是同一個東西：`ResourceQuota` 管的是「整個 namespace 總量上限」，`LimitRange` 管的是「單一 container/Pod 預設值與上下限」（例如 `default`/`defaultRequest`/`max`/`min`），這題要查的是 `LimitRange` 的 `max.memory`，不是 `ResourceQuota`
- 題目說 Pod「因容器已用完資源而無法啟動」，通常代表原本的 `nosql.yaml` 裡完全沒寫 `resources`，或寫的數值超出 `LimitRange` 的 `max` 限制導致被拒絕（`Pending` + `exceeded quota`／`maximum memory usage`錯誤）——修改前可以先用 `kubectl describe pod` 或 `kubectl get events -n haddock` 確認實際卡住的原因
- `limits.memory` 一定要**先查出 `haddock` namespace `LimitRange` 的 `max.memory`，再手動除以 2 算出實際數字**填進 yaml，不能憑空亂填一個看起來合理的值——這是這題最容易忽略、也最容易算錯的地方（練習範例中 `max.memory: 40Mi`，算出來的 `limits.memory` 就是 `20Mi`）
- 修改 Deployment 後要確認 rollout 有成功套用到新的 ReplicaSet／Pod（`kubectl rollout status deployment/nosql -n haddock`），舊的卡住的 Pod 不會自動變好，需要靠新 rollout 產生新 Pod 才會用上新的 resources 設定

## 題目7 - 金絲雀部署（Canary Deployment）

**Quick Reference**：

- Cluster/配置環境：`k8s`
- Namespace：`goshawk`

**題目敘述**：

> ⚠️ 必須先切換到正確的 Cluster/配置環境（`kubectl config use-context k8s`），不這樣做可能導致零分。

**情境（Context）**：為了測試新的應用程式發布，需要準備一個金絲雀部署（canary deployment）。

**現況**：namespace `goshawk` 中名為 `chipmunk-service` 的 Service，指向名為 `current-chipmunk-deployment` 的 Deployment 建立的 5 個 Pod：

```
       +------------------+
       | chipmunk-service |
       +--------+---------+
          /     |     \
         /      |      \
+-------v-------v-------v-----------------------+
|  [ Pod 1 ]  [ Pod 2 ]  ...  [ Pod 5 ]         |
|                                               |
|  current-chipmunk-deployment                  |
+-----------------------------------------------+
```

**Task**：新建一個 canary Deployment，讓它的 Pod 也能被同一個 `chipmunk-service` 分流到，跟 `current-chipmunk-deployment` 的 Pod 一起接流量。**不需要修改 Service**，只要讓兩個 Deployment 依 replica 數量做出金絲雀該有的流量比例分配即可。

**相關資源**：[CKAD/ckad/goshawk/current-chipmunk-deployment.yaml](CKAD/ckad/goshawk/current-chipmunk-deployment.yaml)（模擬考場既有的 Deployment）、[CKAD/07-CanaryRelease.yaml](CKAD/07-CanaryRelease.yaml)（新建的 canary Deployment）

**解法指令**：

```bash
kubectl config use-context k8s

kubectl apply -f CKAD/ckad/goshawk/current-chipmunk-deployment.yaml
kubectl apply -f CKAD/07-CanaryRelease.yaml

# 驗證：chipmunk-service 底下應該同時出現兩個 Deployment 的 Pod
kubectl get pods -n goshawk -l run=dep-svc --show-labels
kubectl get endpoints chipmunk-service -n goshawk
```

`CKAD/ckad/goshawk/current-chipmunk-deployment.yaml` 關鍵欄位：

```yaml
spec:
  replicas: 6
  selector:
    matchLabels:
      app: current-chipmunk-deployment   # 區分用，只認領自己的 Pod
      run: dep-svc                       # 公用標籤，Service 靠這個 selector 分流
  template:
    metadata:
      labels:
        app: current-chipmunk-deployment
        run: dep-svc
```

`CKAD/07-CanaryRelease.yaml` 關鍵欄位：

```yaml
spec:
  replicas: 4
  selector:
    matchLabels:
      app: canary-chipmunk-deployment    # 區分用，只認領自己的 Pod
      run: dep-svc                       # 公用標籤，Service 靠這個 selector 分流
  template:
    metadata:
      labels:
        app: canary-chipmunk-deployment
        run: dep-svc
```

兩邊 `replicas` 是 `6 : 4`，也就是流量約 `60% : 40%` 分給穩定版 / 金絲雀版。

**對應考綱 Domain**：

`Application Deployment`（20%）→ `部署策略（blue/green、canary）`（這是筆記系列裡第一次涉及這個知識點，`Record.md` CKAD TEST 章節目前標註「尚未涉及」）

**易錯點／踩坑筆記**：

- **完全不用改 Service**：`chipmunk-service` 的 selector 只挑 `run: dep-svc` 這個「公用標籤」，不挑 Deployment 專屬的 `app` label，所以任何新建的 Deployment，只要它產生的 Pod 也帶有 `run: dep-svc`，就會自動被這個既有 Service 納入分流——這是這題的核心陷阱：很多人看到「金絲雀」就想去改 Service 的 weight／annotation，但原生 Kubernetes Service 沒有流量權重這種欄位，靠的完全是 Pod 數量比例
- **兩個 Deployment 的 `selector.matchLabels` 一定要有各自專屬的區分標籤**（這裡是 `app: current-chipmunk-deployment` vs `app: canary-chipmunk-deployment`），只留公用的 `run: dep-svc` 會導致兩個 Deployment 的 selector 互相重疊——Deployment controller 會分不清哪些 Pod 是自己的，兩邊互搶對方的 Pod，造成 replica 數量不斷震盪（這跟 [Record.md Day 8](Record.md#day-8)/[Day 10](Record.md#day-10) 學過的 `selector`/`matchLabels` 篩選機制是同一個底層原理，只是這題是「刻意設計兩層 label：一層讓 Service 選中、一層讓各自 Deployment 認領」）
- **金絲雀的「流量比例」＝「Pod 數量比例」**：Service 對它 selector 選中的所有 Pod 是無差別輪詢（round-robin）負載平衡，沒有辦法針對單一 Deployment 設定權重，唯一能控制比例的手段就是調整兩個 Deployment 各自的 `replicas`——這裡練習用 `6:4`，實際題目如果要求「新版只吃 10% 流量」，就要抓比較大的公因數（例如穩定版 9、金絲雀版 1，總數 10）才能精確算出比例
- image／containerPort 等其他 Pod spec 要跟既有 Deployment 對齊（這裡都用 `vicuu/nginx:hi`、`containerPort: 3000`），確保新舊版本除了刻意要測試的差異外，其餘設定一致，才是「金絲雀測試」的正確用法

## 題目8 - 修改 Deployment 的 SecurityContext（runAsUser / allowPrivilegeEscalation）

**Quick Reference**：

- Cluster/配置環境：`k8s`
- Namespace：`quetzal`

**題目敘述**：

> ⚠️ 必須先切換到正確的 Cluster/配置環境（`kubectl config use-context k8s`），不這樣做可能導致零分。

修改運行在 namespace `quetzal`、名為 `broker-deployment` 的**既有** Deployment，使其容器：

- 以使用者 `30000` 運行
- 禁止特權提升（no privilege escalation）

`broker-deployment` 的清單檔案可在 `/ckad/daring-moccasin/broker-deployment.yaml` 找到（模擬環境無此檔案，做題也不需要這個檔案，直接對 cluster 上既有的 Deployment 操作即可）。

**相關資源**：[CKAD/08-Security-Context.yaml](CKAD/08-Security-Context.yaml)（只記錄要補進去的 `securityContext` 片段，非完整清單，也不需要 `kubectl apply` 整份檔案）

**解法指令**：

```bash
kubectl config use-context k8s

# 先查一下 container 名稱，等一下 edit 時才知道要改哪個 container
kubectl get deployment broker-deployment -n quetzal -o yaml | grep -A2 "containers:"

kubectl edit deployment broker-deployment -n quetzal
```

在 `spec.template.spec.containers[].securityContext` 補上：

```yaml
        securityContext:
          runAsUser: 30000
          allowPrivilegeEscalation: false
```

也可以用 `kubectl patch` 一次到位（假設 container 名稱是 `broker`）：

```bash
kubectl patch deployment broker-deployment -n quetzal --type='json' -p='[
  {"op": "add", "path": "/spec/template/spec/containers/0/securityContext", "value": {"runAsUser": 30000, "allowPrivilegeEscalation": false}}
]'
```

**若考場環境沒有可用的編輯器（`kubectl edit` 打不開／沒有設定 `EDITOR`）**，改用「匯出 → 修改 → 套用」三步驟，一樣能達成同樣效果：

```bash
kubectl get deploy broker-deployment -n quetzal -o yaml > 8.yaml

# 用任何方式編輯 8.yaml，在 spec.template.spec.containers[].securityContext 補上：
#   securityContext:
#     runAsUser: 30000
#     allowPrivilegeEscalation: false

kubectl apply -f 8.yaml
```

**對應考綱 Domain**：

`Application Environment, Configuration and Security`（25%）→ `SecurityContexts / Capabilities`（這是筆記系列裡第一次涉及這個知識點，`Record.md` CKAD TEST 章節目前標註「尚未涉及」）

**易錯點／踩坑筆記**：

- `runAsUser` 可以設在 **Pod 層級**（`spec.securityContext`）或 **container 層級**（`spec.containers[].securityContext`，會覆蓋 Pod 層級的值）；但 `allowPrivilegeEscalation` **只有 container 層級才有這個欄位**（`PodSecurityContext` type 沒有這個 key），所以一定得放 container 層級，沒得選。兩種放法都合法：[Kubernetes 官方文件範例](https://kubernetes.io/docs/tasks/configure-pod-container/security-context/) 就是「`runAsUser` 放 Pod 層級（整個 Pod 共用身份）、`allowPrivilegeEscalation` 放 container 層級」這種分層寫法；也有教學把兩者都塞進 container 層級、圖個好找不用切兩層改。挑一種寫法記熟、考試時別漏改任一層就好
- 這題是修改「既有」Deployment，不是新建，重點是 `kubectl edit`／`kubectl patch`，不是憑空生一份新 yaml；如果考場真的給了 `/ckad/daring-moccasin/broker-deployment.yaml`，也只是「參考清單長什麼樣子」，改的時候還是對 cluster 上的物件動手，改完 apply 或直接 edit 都可以
- **`kubectl edit` 依賴考場環境有可用的文字編輯器（`$EDITOR`），不能保證一定能用**——比較保險的備案是 `kubectl get deploy <name> -n <ns> -o yaml > 8.yaml` 先把當下的完整 yaml 匯出成檔案，用熟悉的方式編輯完再 `kubectl apply -f 8.yaml` 套用回去，效果跟 `kubectl edit` 一樣，只是多了一個「匯出檔案」的步驟，但不依賴考場有沒有裝、有沒有設定好編輯器
- container 名稱一定要先查清楚再改（`kubectl get deployment ... -o yaml` 或 `kubectl describe deployment`），`kubectl patch` 用 JSON path 時如果寫錯 index（例如題目其實有多個 container，只改對了 `containers/0` 但目標其實是 `containers/1`）就會改錯 container，白做工
- 修改完 Deployment 的 Pod template 會觸發 rolling update，記得用 `kubectl rollout status deployment/broker-deployment -n quetzal` 確認新 Pod 有成功套用設定並且 `Running`，也可以 `kubectl get pod <new-pod> -n quetzal -o yaml | grep -A3 securityContext` 直接驗證欄位有沒有進去
- `allowPrivilegeEscalation: false` 這個欄位在 YAML 裡的布林值就是小寫 `false`，不要打成字串 `"false"`（字串會被當成 truthy 值，等於沒設定成功）

## 題目9 - 建立 Deployment 並指定環境變數

**Quick Reference**：

- Cluster/配置環境：`k8s`
- Namespace：`ckad00014`

**題目敘述**：

> ⚠️ 必須先切換到正確的 Cluster/配置環境（`kubectl config use-context k8s`），不這樣做可能導致零分。

**情境（Context）**：需要新建一個用於運行 NGINX 的 Deployment。

**Task**：在現有的 namespace `ckad00014` 中建立一個運行 **6 個 Pod 副本**、名為 `api` 的 Deployment。使用 `nginx:1.16` 映像檔指定一個容器，將名為 `NGINX_PORT`、值為 `8000` 的環境變數加到容器中，然後公開 port `80`。

**相關資源**：[CKAD/09-deployment-env.yaml](CKAD/09-deployment-env.yaml)

**解法指令**：

```bash
kubectl apply -f CKAD/09-deployment-env.yaml
```

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
  namespace: ckad00014
  labels:
    app: nginx
spec:
  replicas: 6
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:1.16
        env:
        - name: NGINX_PORT
          value: "8000"
        ports:
        - containerPort: 80
```

**對應考綱 Domain**：

`Application Design and Build`（20%）→ `Choose and use the right workload resource`（建立 Deployment 本身）、`Application Environment, Configuration and Security`（25%）→ ConfigMap／環境變數相關（這題直接在 `env` 寫死值，是最基本的環境變數設定方式，跟 [Record.md Day 18](Record.md#day-18) 用 `ConfigMap` 掛環境變數是不同做法：這題沒要求要用 ConfigMap，就用最簡單的 inline `env` 即可，不用過度設計）

**易錯點／踩坑筆記**：

- 這份練習 yaml 原本是抄 Kubernetes 官方文件那份經典的 `nginx-deployment` 範例（`name: nginx-deployment`、沒有 `namespace`、`replicas: 3`、`image: nginx:1.14.2`、沒有 `env`），直接套用會整個對不上題目要求——套用任何範本前，一定要逐一比對題目給的每個具體數值（Deployment 名稱、namespace、replica 數、image 版本），不能因為「長得像」就直接交卷
- 環境變數的 `value` 欄位型別是**字串**，YAML 裡數字不加引號也會被解析成整數，跟 k8s API 要求的 `string` 型別衝突，保險起見這裡寫成 `value: "8000"`（加雙引號）；用 `kubectl set env` 指令則不用擔心這個問題，指令本身會處理成字串
- 題目說「公開端口 80」指的是**容器要監聽/宣告 port 80**（`containerPort: 80`），不是要另外建立 Service——這題沒有提到 Service，不要多做，只要 Deployment 的 `ports` 欄位寫對即可
- `NGINX_PORT=8000` 這個環境變數本身**不會**讓 nginx 真的改成監聽 8000 port（nginx 預設監聽 80，要改監聽 port 需要修改 nginx 設定檔或搭配自訂 image/entrypoint 讀取這個環境變數）——這題純粹是「幫容器加一個環境變數」的操作題，跟「nginx 服務實際監聽在哪個 port」是兩回事，題目要求的 `containerPort: 80` 才是實際對外聲明的 port
- 也可以用指令式寫法一次生成 skeleton 再補環境變數，速度更快：
  ```bash
  kubectl create deployment api -n ckad00014 --image=nginx:1.16 --replicas=6 --port=80 --dry-run=client -o yaml > 09-deployment-env.yaml
  # 再手動編輯加入 env，或用 kubectl set env 補上：
  kubectl set env deployment/api -n ckad00014 NGINX_PORT=8000
  ```

## 題目10 - RBAC 授權除錯（ServiceAccount 權限不足）

**Quick Reference**：

- Cluster/配置環境：`k8s`
- Namespace：`gorilla`

**題目敘述**：

> ⚠️ 必須先切換到正確的 Cluster/配置環境（`kubectl config use-context k8s`），不這樣做可能導致零分。
>
> 備註（原題）：debug 錯誤，邏輯稍微有點繞。

名為 `honeybee-deployment` 的 Deployment（namespace `gorilla`）裡的 Pod 正在記錄錯誤。

1. 查看日誌以識別錯誤訊息，會看到類似：
   ```
   User "system:serviceaccount:gorilla:default" cannot list resource "serviceaccounts" [...] in the namespace "gorilla"
   ```
2. 更新 `honeybee-deployment`（廣義上，讓這個 Deployment 底下的 Pod 不再噴這個錯），解決 Pod 日誌中的錯誤。

`honeybee-deployment` 的清單檔案可在 `/ckad/prompt-escargot/honeybee-deployment.yaml` 找到。

> 💡 **這題真正要練的核心技能**：不是死背 `Role`/`RoleBinding` 的 yaml 語法，而是學會**用 kubectl 檢查現有的 `ServiceAccount`／`Role`／`RoleBinding`**，搞清楚「目前哪些 SA 已經有哪些權限」，然後判斷「該把這個 Deployment 設定成用哪個 SA 才對」——修 RBAC 問題常常不是從零生一個 Role，而是先看清楚 cluster 上已經有什麼。

**相關資源**：

- [CKAD/ckad/honeybee-deployment.yaml](CKAD/ckad/honeybee-deployment.yaml)：**修改前**，`serviceAccountName: default`，`default` SA 沒有任何權限，Pod 日誌會持續噴 `Forbidden`
- [CKAD/10.RBAC.yaml](CKAD/10.RBAC.yaml)：**修改後**，`serviceAccountName: gorilla-sa`，`gorilla-sa` 已經透過 `gorilla-role` 取得 `get`/`list` 權限，套用後 Pod 可以順利執行 `kubectl get serviceaccounts` 不再報錯
- [CKAD/10-rbac-fix.yaml](CKAD/10-rbac-fix.yaml)：`gorilla-sa`（ServiceAccount）+ `gorilla-role`（Role：`pods`/`serviceaccounts`/`deployments` 的 `get`/`list`）+ `gorilla-role-binding`（RoleBinding，把兩者綁在一起）

`CKAD/ckad/honeybee-deployment.yaml` 的 container 在做什麼：

```yaml
command:
- sh
- -c
- |
  while true ; do
    date --rfc-3339=seconds
    kubectl get serviceaccounts
    sleep 10
  done
image: bitnami/kubectl:latest   # 原檔是 1.21，該 tag 已從 Docker Hub 下架，見下方踩坑筆記
```

`bitnami/kubectl` 這個 image 只打包了 `kubectl` CLI。container 起來後每 10 秒印一次時間戳記，然後執行 `kubectl get serviceaccounts`——沒帶 `-n`、也沒帶 `--kubeconfig`，`kubectl` 會自動偵測掛載在 `/var/run/secrets/kubernetes.io/serviceaccount/` 的 in-cluster config（token、CA 憑證、namespace 檔案），用 Pod 自己的 `serviceAccountName: default` 身份、Pod 自己所在的 `gorilla` namespace 去打 API server，因此才會出現錯誤訊息裡的 `system:serviceaccount:gorilla:default`。

**解法指令**（已在本機 minikube 實測跑過整個流程）：

```bash
kubectl config use-context k8s

# 1. 部署原始的 honeybee-deployment（修改前），重現錯誤
kubectl apply -f CKAD/ckad/honeybee-deployment.yaml

# 2. 查日誌，確認錯誤訊息
kubectl logs -n gorilla deploy/honeybee-deployment
# Error from server (Forbidden): serviceaccounts is forbidden:
# User "system:serviceaccount:gorilla:default" cannot list resource "serviceaccounts"
# in API group "" in the namespace "gorilla"
```

**第一步：用 `kubectl` 檢查現有的 SA / Role / RoleBinding，而不是急著憑空生一個新的**——這才是這題真正要練的解題方法：

```bash
# 這個 namespace 目前有哪些 ServiceAccount？
kubectl get sa -n gorilla
# NAME         SECRETS   AGE
# default      0         1h
# gorilla-sa   0         1h        ← 除了 default，還有沒有其他已經建好、看起來就是為這個任務準備的 SA？

# 這個 namespace 目前有哪些 Role／RoleBinding？
kubectl get role,rolebinding -n gorilla

# 針對看起來相關的 RoleBinding，查它綁定了誰（subjects）、綁的是哪個 Role（roleRef）
kubectl describe rolebinding gorilla-role-binding -n gorilla
# Role:  gorilla-role
# Subjects:
#   Kind            Name        Namespace
#   ServiceAccount  gorilla-sa  gorilla

# 再查那個 Role 實際開放了哪些權限
kubectl describe role gorilla-role -n gorilla
# PolicyRule:
#   Resources        Verbs
#   ---------        -----
#   pods             [get list]
#   serviceaccounts  [get list]
#   deployments.apps [get list]
```

看到這裡就能判斷出：`gorilla-sa` 已經透過 `gorilla-role` 具備 `serviceaccounts` 的 `get`/`list` 權限——**答案就是把 `honeybee-deployment` 改成用 `gorilla-sa`**，不用另外從零生一個 Role。

**第二步：把 Deployment 改成用 `gorilla-sa`**，兩種等價做法：

```bash
# 做法 A：指令式，不用碰 yaml
kubectl set serviceaccount deployment honeybee-deployment gorilla-sa -n gorilla

# 做法 B：直接改 yaml 再 apply（見 CKAD/10.RBAC.yaml，修改前後對照見下方）
kubectl apply -f CKAD/10.RBAC.yaml
```

```yaml
# CKAD/10.RBAC.yaml 跟 CKAD/ckad/honeybee-deployment.yaml 唯一的差異
      serviceAccount: gorilla-sa       # 修改前是 default
      serviceAccountName: gorilla-sa   # 修改前是 default（真正生效的欄位）
```

**驗證**：

```bash
kubectl logs -n gorilla deploy/honeybee-deployment --tail=6
# 應該會看到 kubectl get serviceaccounts 成功列出：
# NAME         AGE
# default      xxxm
# gorilla-sa   xxxm
```

補 RBAC 權限本身用的 [`CKAD/10-rbac-fix.yaml`](CKAD/10-rbac-fix.yaml)（`gorilla-sa` + `gorilla-role` + `gorilla-role-binding`）：

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: gorilla-sa
  namespace: gorilla
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: gorilla-role
  namespace: gorilla
rules:
- apiGroups: [""]                    # pods、serviceaccounts 都屬於 core API group
  resources: ["pods", "serviceaccounts"]
  verbs: ["get", "list"]
- apiGroups: ["apps"]                 # deployments 屬於 apps API group，要分開一條規則
  resources: ["deployments"]
  verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: gorilla-role-binding
  namespace: gorilla
subjects:
- kind: ServiceAccount
  name: gorilla-sa
  namespace: gorilla
roleRef:
  kind: Role
  name: gorilla-role
  apiGroup: rbac.authorization.k8s.io
```

**對應考綱 Domain**：

`Application Environment, Configuration and Security`（25%）→ `Authentication / Authorization / Admission Control`、`ServiceAccounts`（這是筆記系列裡第一次涉及這兩個知識點，`Record.md` CKAD TEST 章節目前都標註「尚未涉及」）

**易錯點／踩坑筆記**：

- **看懂錯誤訊息的結構是這題的第一關**：`User "system:serviceaccount:<namespace>:<sa-name>" cannot list resource "<resource>" in API group "<group>" in the namespace "<ns>"` 這句話已經把「誰」（哪個 namespace 的哪個 ServiceAccount）、「想做什麼」（`list`）、「對什麼資源」（`serviceaccounts`）都講清楚了，不用另外猜——直接照著這句話反推需要的 `Role` 規則即可
- Pod 預設會用該 namespace 的 `default` ServiceAccount（除非 `spec.serviceAccountName` 有另外指定），這題錯誤訊息裡的 `gorilla:default` 就是「`gorilla` namespace 底下的 `default` ServiceAccount」，不是某種特殊帳號名稱叫 `default`
- **`Role` 是「定義能做什麼」，`RoleBinding` 是「定義誰可以做」**——這是 RBAC 最基本的兩層設計，兩個都要建、缺一個都不會生效：只建 `Role` 沒有 `RoleBinding` 綁定，等於權限規則寫好了但沒人拿得到；只建 `RoleBinding` 沒有對應 `Role`，會直接 apply 失敗（`roleRef` 找不到）
- `Role`/`RoleBinding` 是 **namespace-scoped** 的資源，只在同一個 namespace 內生效；如果錯誤訊息裡的資源是 cluster-scoped（例如 `nodes`、`persistentvolumes`）或需要跨 namespace 存取，就要改用 `ClusterRole` + `ClusterRoleBinding`，這題的 `serviceaccounts` 是 namespace-scoped 資源，`Role`/`RoleBinding` 就夠了
- **`bitnami/kubectl:1.21` 這個 tag 在本機練習時抓不到**（`kubectl describe pod` 看到 `Failed to pull image ... manifest unknown`）：Bitnami 在 2025 年中重整了 Docker Hub 上的 image 目錄，舊版本號 tag 大量下架，`bitnami/` 這個免費 namespace 現在通常只留最新版。本機練習改用 `bitnami/kubectl:latest` 即可正常拉取；這是本機/practice cluster 的 registry 連線問題，跟考題邏輯無關，**實際考場的沙盒環境通常有自己的 image cache 或內部 registry，不一定會遇到這個坑**，但如果考試當下真的卡在 `ImagePullBackOff`，`kubectl describe pod` 看 `manifest unknown`／`not found` 這類訊息是第一時間該做的診斷
- 「更新 Deployment 以解決錯誤」**有兩種同樣合法的修法**，考場上兩種都可能是預期答案：(1) 讓 `default` SA 直接拿到權限（幫 `default` 建 `Role`+`RoleBinding`，Deployment 完全不用動）；(2) 讓 Deployment **改用**另一個「已經有權限」的 SA（`kubectl set serviceaccount` 或直接改 `serviceAccountName`）。這題練習刻意選第二種，是因為更貼近「先查清楚 cluster 上已經準備了什麼」這個實務除錯習慣——**兩種修法都要先確認清楚「現在到底綁的是哪個 SA、那個 SA 有沒有權限」，不要沒查就先動手改**
- `kubectl set serviceaccount`（別名 `kubectl set sa`）語法是 `kubectl set serviceaccount <resource> <name> <sa-name> -n <namespace>`——第一次打很容易打錯（例如漏打資源類型、資源名稱多打字），指令本身不接受打錯字的資源名稱，`kubectl` 會直接回報 `not found`，這種時候先用 `kubectl get deploy -n <ns>` 確認正確名稱再重打
- 補完 RBAC 權限、或幫 Deployment 換了 SA 之後，**已經在跑的 Pod 不一定會自動重試成功**：要看應用程式的邏輯是「每次迴圈重新呼叫 API」（這種等下一輪自然就正常了，練習範例的 `while true` 迴圈就是這種）還是「開機時呼叫一次失敗就直接 crash」（這種要 `kubectl rollout restart deployment/honeybee-deployment -n gorilla` 讓它重新啟動、重新嘗試）；不過如果是**改 `serviceAccountName`**（不管用指令或改 yaml），Deployment 的 Pod template 一定會變更，本來就會觸發 rolling update、產生新 Pod，這種情況不用額外下 `rollout restart`

## 題目11 - 建立 ConfigMap 並掛載成 Volume

**Quick Reference**：

- Cluster/配置環境：`k8s`
- Namespace：`default`

**題目敘述**：

> ⚠️ 必須先切換到正確的 Cluster/配置環境（`kubectl config use-context k8s`），不這樣做可能導致零分。

**情境（Context）**：需要建立一個 ConfigMap，並在一個 Pod 中使用這個 ConfigMap。

**Task**：

1. 在 namespace `default` 中建立一個名為 `some-config`、儲存以下 key/value 的 ConfigMap：
   - `key3: value4`
2. 在 namespace `default` 中建立一個名為 `nginx-configmap` 的 Pod。用 `nginx:stable` 映像檔指定一個容器。用儲存在 ConfigMap `some-config` 中的資料填充一個 Volume，並掛載在路徑 `/some/path`。

**相關資源**：[CKAD/11-configmap.yaml](CKAD/11-configmap.yaml)

**解法指令**（考試時的實際作法：能用指令式就用指令式，不熟的 flag 現場 `-h` 查）：

```bash
kubectl config use-context k8s

# 1. ConfigMap 用指令式一步到位，忘記 flag 名稱就先查 help
kubectl create configmap some-config -h
kubectl create configmap some-config --from-literal=key3=value4

# 2. Pod 要掛 Volume，kubectl run 沒有對應 flag，
#    改用 --dry-run=client -o yaml 先產生骨架，再手動補 volumes/volumeMounts
kubectl run nginx-configmap --image=nginx:stable --dry-run=client -o yaml > 11-pod.yaml
# 編輯 11-pod.yaml，補上：
#   volumeMounts: [{name: config-volume, mountPath: /some/path}]
#   volumes: [{name: config-volume, configMap: {name: some-config}}]
kubectl apply -f 11-pod.yaml
```

完整 yaml 對照（`kubectl apply -f CKAD/11-configmap.yaml` 也能一次到位，練習用兩種方式都跑過一次比較熟）：

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: some-config
  namespace: default
data:
  key3: value4
---
apiVersion: v1
kind: Pod
metadata:
  name: nginx-configmap
  namespace: default
spec:
  containers:
  - name: nginx
    image: nginx:stable
    volumeMounts:
    - name: config-volume
      mountPath: /some/path
  volumes:
  - name: config-volume
    configMap:
      name: some-config
```

**驗證**：

```bash
kubectl exec nginx-configmap -n default -- ls /some/path
# key3

kubectl exec -it nginx-configmap -n default -- cat /some/path/key3
# value4
```

**對應考綱 Domain**：

`Application Environment, Configuration and Security`（25%）→ `ConfigMaps`（延續 [Record.md Day 18](Record.md#day-18) 學過的 `kubectl create configmap`／`volumes.configMap` 掛載機制，這題是同一套知識點直接考出來的標準題型）

**易錯點／踩坑筆記**：

- **這題 namespace 是 `default`**，跟前面幾題（`pod-resources`/`haddock`/`goshawk`/`quetzal`/`ckad00014`/`gorilla`）都不一樣——`default` 是每個 cluster 天生就有的 namespace，**不用也不能用 `kubectl create namespace` 再建一次**，题目沒特別提到 namespace 時反而要留意是不是就是要用 `default`，不要因為前面題目慣性都要指定專屬 namespace，就自己多帶一個不存在的 `-n`
- 用 `configMap` 掛成 Volume 時，**ConfigMap 裡的每一個 key 都會變成掛載目錄下的一個檔案**，檔名就是 key 名稱、檔案內容就是 value——這題 `key3: value4` 掛到 `/some/path` 之後，實際會出現 `/some/path/key3` 這個檔案，內容是 `value4`，這是跟 [Record.md Day 18](Record.md#day-18) 用環境變數方式掛 ConfigMap（`envFrom`/`valueFrom.configMapKeyRef`）完全不同的用法，題目明確說「填充卷（Volume）」就是要用 `volumes.configMap` 這種掛檔案的方式，不是環境變數
- `mountPath: /some/path` 是**掛載到 container 內部檔案系統的路徑**，跟 container image 裡原本可能存在的目錄無關——如果該路徑在 image 裡本來就有檔案，掛上 ConfigMap Volume 後**原本的內容會被完全蓋掉**（覆蓋整個目錄，不是合併），這題掛在 `/some/path` 是全新路徑不影響 nginx 本身運作，但如果之後題目要求掛在 nginx 設定檔目錄之類的地方，要特別小心這個覆蓋行為
- `data` 底下的 value 如果是純數字或看起來像特殊 YAML 值（`true`/`false`/`null` 等），保險起見也建議加引號寫成字串，跟 [題目9](#題目9---建立-deployment-並指定環境變數) 環境變數 `value` 欄位的坑是同一種道理；這題 `value4` 本身是字串沒有這個疑慮，純粹是通用習慣提醒
- **考試時的原則：能用指令式（`kubectl create`/`kubectl run`）就不要手寫整份 yaml**，像這題的 `ConfigMap` 用 `kubectl create configmap some-config --from-literal=key3=value4` 一行就搞定，比手打 yaml 快很多也不容易漏欄位或縮排錯；不確定 flag 名稱時**現場 `-h` 查**（例如 `kubectl create configmap some-config -h` 會列出 `--from-literal`/`--from-file` 這些選項），比憑記憶硬猜可靠。跟 [題目1](#題目1---cronjob-手動觸發-job) 用 `kubectl create job -h` 查 `--from=cronjob/` 是同一個應試習慣
- 但 **Pod 掛 Volume 這種比較複雜的 spec，`kubectl run`／`kubectl create` 都沒有對應的 flag 可以一次生成**，只能先用 `--dry-run=client -o yaml` 產生一份陽春骨架，再手動編輯補上 `volumes`/`volumeMounts` 這兩塊——指令式跟 yaml 編輯**是互補而不是二選一**，簡單的物件（ConfigMap/Secret 本身）用指令式建立最快，物件之間的「掛載關係」（Volume、envFrom 等）通常還是得回到 yaml 手動接起來
- **驗證時 `kubectl exec` 沒帶 `-n` 也會踩到 namespace 坑**：這題實測過，練習前面幾題（[題目5](#題目5---修正-deployment-的記憶體-requestslimits依-namespace-limitrange)/[題目10](#題目10---rbac-授權除錯serviceaccount-權限不足)）切換過 `k8s` context 的預設 namespace（`kubectl config set-context --current --namespace=...`）之後，之後所有沒帶 `-n` 的指令都會打到那個殘留設定的 namespace，不是 `default`——`kubectl exec nginx-configmap`（沒帶 `-n default`）會直接 `Error from server (NotFound)`，因為 Pod 根本不在當前預設 namespace 裡。**下指令前養成先 `kubectl config view --minify -o jsonpath='{..namespace}'` 確認目前預設 namespace 的習慣**，比每次都用猜的可靠，或是乾脆每個指令都手動帶 `-n <namespace>`，不依賴預設值
- `kubectl exec` 要執行「用某個 shell 執行一段指令」時，**`/bin/bash <command> <args>` 這種寫法是錯的**：`/bin/bash cat /some/path/key3` 會讓 bash 把 `cat` 當成**要讀取執行的 script 檔案路徑**，而不是「要執行 cat 這個指令」，因為 `cat` 是二進位檔不是文字腳本，會報錯 `cannot execute binary file`。正確寫法是**直接把指令放在 `--` 後面**（`kubectl exec ... -- cat /some/path/key3`，不需要 `/bin/bash`），或是真的要透過 shell 執行多段指令時用 `bash -c "指令"` 包起來（`-- bash -c "cat /some/path/key3"`）

## 題目12 - 建立 Secret 並以環境變數使用

**Quick Reference**：

- Cluster/配置環境：`k8s`
- Namespace：`default`

**題目敘述**：

> ⚠️ 必須先切換到正確的 Cluster/配置環境（`kubectl config use-context k8s`），不這樣做可能導致零分。

**情境（Context）**：需要建立一個 Secret，並在一個 Pod 中使用這個 Secret。

**Task**：

1. 在 namespace `default` 中建立一個名為 `another-secret`、包含以下單一 key/value 的 Secret：
   - `key1: value12`
2. 在 namespace `default` 中建立一個名為 `nginx-secret` 的 Pod。用 `nginx:1.16` 映像檔指定一個容器。加一個名為 `COOL_VARIABLE` 的環境變數，值來自 Secret 的 `key1`。

**相關資源**：[CKAD/12-secret.yaml](CKAD/12-secret.yaml)

**解法指令**（考試時作法：跟 [題目11](#題目11---建立-configmap-並掛載成-volume) 同一套節奏——Secret 用指令式一步到位，Pod 的環境變數引用還是得回 yaml 手動接）：

```bash
kubectl config use-context k8s

# 1. Secret 用指令式建立，不確定 flag 就現場查
kubectl create secret generic another-secret -h
kubectl create secret generic another-secret -n default --from-literal=key1=value12

# 2. Pod 用 --dry-run 產生骨架，再手動補 env.valueFrom.secretKeyRef
kubectl run nginx-secret -n default --image=nginx:1.16 --dry-run=client -o yaml > 12-pod.yaml
# 編輯 12-pod.yaml，補上：
#   env:
#   - name: COOL_VARIABLE
#     valueFrom:
#       secretKeyRef:
#         name: another-secret
#         key: key1
kubectl apply -f 12-pod.yaml
```

完整 yaml 對照（`kubectl apply -f CKAD/12-secret.yaml` 也能一次到位）：

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: another-secret
  namespace: default
type: Opaque
stringData:
  key1: value12
---
apiVersion: v1
kind: Pod
metadata:
  name: nginx-secret
  namespace: default
spec:
  containers:
  - name: nginx
    image: nginx:1.16
    env:
    - name: COOL_VARIABLE
      valueFrom:
        secretKeyRef:
          name: another-secret
          key: key1
```

**驗證**：

```bash
kubectl exec -it nginx-secret -n default -- printenv COOL_VARIABLE
# value12
```

**對應考綱 Domain**：

`Application Environment, Configuration and Security`（25%）→ `Secrets`（延續 [Record.md Day 12](Record.md#day-12) 學過的 `kubectl create secret generic`、`secretKeyRef` 環境變數掛法，這題是同一套知識點直接考出來的標準題型，剛好跟 [題目11](#題目11---建立-configmap-並掛載成-volume) 的 ConfigMap 掛 Volume 形成對照）

**易錯點／踩坑筆記**：

- **這題用的是環境變數（`env.valueFrom.secretKeyRef`），不是 Volume**——跟 [題目11](#題目11---建立-configmap-並掛載成-volume) 剛好相反：題目11 說「填充卷」用 `volumes.secret`/`volumes.configMap`，這題說「加一個環境變數」就要用 `env.valueFrom.secretKeyRef`（單一 key）或 `envFrom.secretRef`（整包 Secret 全部變成環境變數）。看清楚題目要的是「掛檔案」還是「當環境變數」，這是這兩題唯一的本質差異，其他步驟幾乎一樣
- `secretKeyRef` 底下要同時指定 `name`（Secret 物件名稱）跟 `key`（Secret 裡的哪個 key），這題是 `name: another-secret` + `key: key1`——只寫 `name` 沒寫 `key` 會直接 apply 失敗（`key` 是必填欄位）
- 建立 Secret 時，**`kubectl create secret generic --from-literal` 建出來的值會自動 base64 編碼存進 `data` 欄位**，這是 Secret 跟 ConfigMap 最大的差異（ConfigMap 明文存在 `data`，Secret 是 base64 存在 `data`，或用 `stringData` 讓 Kubernetes 幫你自動轉換）；這份練習 yaml 用 `stringData: {key1: value12}` 明文寫，`kubectl apply` 之後 Kubernetes 會自動轉成 base64 存進 `data`，兩種寫法效果一樣，`stringData` 純粹是給人看的方便寫法
- Container 裡讀出來的環境變數值**已經是解碼後的明文**（`value12`），不會是 base64 字串——base64 編碼只發生在 etcd 儲存層，Kubernetes 在把值注入環境變數／掛載成檔案的當下就已經自動解碼了，這題驗證 `printenv COOL_VARIABLE` 應該直接看到 `value12`，如果看到一串 base64 亂碼，代表 yaml 寫錯了（例如誤把 base64 值直接塞進 `stringData`）
- 同樣要留意 [題目11](#題目11---建立-configmap-並掛載成-volume) 提過的殘留 namespace 坑：驗證指令記得帶 `-n default`，不要依賴當前 context 的預設 namespace

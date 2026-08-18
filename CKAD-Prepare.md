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

## 公用知識

- `kubectl config get-contexts`：列出目前 kubeconfig 裡所有可用的 context
- `kubectl config use-context k8s`：切換到指定 context（範例用 `k8s`）
- `kubectl config set-context k8s --namespace=pod-resource`
- （未來陸續補充的通用指令都放這裡）

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

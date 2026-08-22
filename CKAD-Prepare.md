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
- [題目13 - Liveness Probe 除錯（跨 namespace 找壞掉的 Pod）](#題目13---liveness-probe-除錯跨-namespace-找壞掉的-pod)
- [題目14 - 幫既有 Deployment 加上 ReadinessProbe](#題目14---幫既有-deployment-加上-readinessprobe)
- [題目15 - Deployment 升級策略、更新與回滾](#題目15---deployment-升級策略更新與回滾)
- [題目16 - ServiceAccount 命名規則、禁止自動掛載 Token、清理未使用的 SA](#題目16---serviceaccount-命名規則禁止自動掛載-token清理未使用的-sa)
- [題目17 - 更新 Deployment 並暴露 Service](#題目17---更新-deployment-並暴露-service)
- [題目18 - 用既有 NetworkPolicy 限制 Pod 只能跟指定對象通訊](#題目18---用既有-networkpolicy-限制-pod-只能跟指定對象通訊)
- [題目19 - Ingress 排錯-1](#題目19---ingress-排錯-1)
- [題目20 - Ingress 排錯-2](#題目20---ingress-排錯-2)

## 公用知識

- `kubectl config get-contexts`：列出目前 kubeconfig 裡所有可用的 context
- `kubectl config use-context k8s`：切換到指定 context（範例用 `k8s`）
- `kubectl config set-context k8s --namespace=pod-resource`
- `kubectl get pods -A`：撈出**所有 namespace** 的 Pod（`-A`/`--all-namespaces`），題目沒指定或說「可能在任何 namespace」時的第一步（見 [題目13](#題目13---liveness-probe-除錯跨-namespace-找壞掉的-pod)）；同樣的 `-A` 也能加在 `get events`/`get deploy` 等其他資源上，不是 `get pods` 專屬
- `kubectl get pods -n <namespace> --show-labels`：一次列出該 namespace 底下每個 Pod 目前的所有標籤，不用一個一個 `kubectl get pod <name> -o yaml` 慢慢翻——凡是題目牽涉到 label selector（Service、NetworkPolicy、Deployment selector）的情境，這是確認「現在標籤長怎樣」最快的指令，[題目17](#題目17---更新-deployment-並暴露-service)/[題目18](#題目18---用既有-networkpolicy-限制-pod-只能跟指定對象通訊) 都用得到
- （未來陸續補充的通用指令都放這裡）

### 修改既有物件：優先用「匯出 → 編輯 → apply」，少用 `kubectl edit`

`kubectl edit` 預設開啟的編輯器常常是最原始難用的 `vi`（不熟的話光是「怎麼存檔離開」就會卡住浪費時間），建議固定用這個模式取代：

```bash
# 1. 匯出 YAML
kubectl get deployment <name> -o yaml > deploy.yaml

# 2. 用習慣的編輯器修改
nano deploy.yaml   # 或 vim/其他熟悉的編輯器

# 3. 套用變更
kubectl apply -f deploy.yaml
```

- 好處不只是「換個熟悉的編輯器」：整個過程有實體檔案留底，改錯了可以直接對照、重編輯再 apply 一次，不用像 `kubectl edit` 那樣在編輯器裡卡住、或改壞了要重新整個流程來過
- 這個模式在 [題目8](#題目8---修改-deployment-的-securitycontextrunasuser--allowprivilegeescalation) 就已經用過（當時定位是「沒有編輯器可用時的備案」），現在直接**升級成優先做法**，不用等到 `kubectl edit` 真的打不開才想到；[題目13](#題目13---liveness-probe-除錯跨-namespace-找壞掉的-pod) 修 Pod 的 liveness probe、[題目14](#題目14---幫既有-deployment-加上-readinessprobe)/[題目15](#題目15---deployment-升級策略更新與回滾) 修 Deployment 也都是同一套「匯出→編輯→套用」的節奏，只是分別用 `apply`（Deployment，可覆蓋更新）跟「`delete` 再 `apply`」（單獨的 Pod，container 欄位不可變，見題目13）
- 考場如果連 `nano`/`vim` 都不熟，`sed -i` 這種指令式取代也是選項（[題目13](#題目13---liveness-probe-除錯跨-namespace-找壞掉的-pod) 用過），但只適合「明確知道要改哪一行、不會誤改到其他相同字串」的簡單情況，欄位複雜或有重複字串時還是手動編輯比較保險

### `containerPort` vs Service 的 `port` / `targetPort`

同一個字「port」在不同層級代表不同東西，是 Service 相關題目最容易搞混的地方（完整圖解見 [Record.md Day 13](Record.md#day-13)）：

| 欄位 | 在哪裡宣告 | 意義 |
| --- | --- | --- |
| `containerPort` | Deployment/Pod 的 `containers[].ports` | 宣告 container **實際監聽**哪個 port，比較偏文件用途；不寫也不影響流量能不能打進去 |
| `Service.spec.ports[].port` | Service | Client 連這個 Service 要打的 port |
| `Service.spec.ports[].targetPort` | Service | Service 收到流量後**實際轉發到 Pod 的哪個 port**——這個才要對到 container 真正監聽的 port，沒寫預設等於 `port` |

- `port` 跟 `targetPort` 可以不同（例如對外 `port: 80`、實際轉給 Pod 的 `targetPort: 8080`）
- 只宣告 `containerPort`、沒建 Service 的題目（例如 [題目9](#題目9---建立-deployment-並指定環境變數)），單純就是文件宣告，不用多想要不要建 Service

### livenessProbe / readinessProbe / startupProbe 完整欄位對照

三種 Probe **yaml 欄位結構完全一樣**，差別只在「探測失敗後 Kubernetes 會做什麼」（`livenessProbe` 基礎概念見 [Record.md Day 11](Record.md#day-11)，這裡把 `readinessProbe`/`startupProbe` 跟完整欄位一起補齊）：

| Probe 類型 | 探測失敗的後果 | 用途 |
| --- | --- | --- |
| `livenessProbe` | container 被 kubelet **重啟**（跟 `restartPolicy` 邏輯連動） | 偵測「服務卡死了、要不要重開」——服務還活著但沒回應（例如 deadlock） |
| `readinessProbe` | Pod 被**移出 Service 的 Endpoints**，不會重啟，只是暫時不接新流量 | 偵測「服務現在能不能接流量」——例如啟動中、暫時在做重載入設定、依賴的下游還沒連上 |
| `startupProbe` | 探測**成功前**，`livenessProbe`/`readinessProbe` 完全不會開始執行；探測失敗達到 `failureThreshold` 才重啟 container | 給啟動特別慢的應用（例如要跑很久的初始化）多一點寬限期，避免還沒啟動完就被 `livenessProbe` 誤判、反覆重啟 |

**三種探測方式**（`httpGet`/`exec`/`tcpSocket` 三選一寫在同一個 Probe 底下，`grpc` 是較新版本才有的第四種）：

| 探測方式 | 判定成功的條件 | 範例欄位 |
| --- | --- | --- |
| `httpGet` | 對指定 `path`/`port` 發 HTTP GET，回應碼 `200`~`399` 視為成功 | `path: /healthz`、`port: 80`、`scheme: HTTP`（也可 `HTTPS`）、`httpHeaders`（可加自訂 header） |
| `exec` | 在 container 內執行指定指令，**exit code 為 `0`** 視為成功 | `command: ["cat", "/tmp/healthy"]` |
| `tcpSocket` | 指定的 `port` 能成功建立 TCP 連線就視為成功，不管有沒有回應內容 | `port: 3306` |
| `grpc`（k8s 1.24+） | 對指定 `port` 發 gRPC Health Checking Protocol 請求 | `port: 50051`、`service:`（可選，指定要檢查的 gRPC service 名稱） |

**共同計時／閾值欄位**（[題目14](#題目14---幫既有-deployment-加上-readinessprobe) 實際考過 `initialDelaySeconds`/`periodSeconds`）：

| 欄位 | 意義 | 預設值 |
| --- | --- | --- |
| `initialDelaySeconds` | container 啟動後，延遲幾秒才開始第一次探測 | `0`（container 一啟動就馬上探測） |
| `periodSeconds` | 每隔幾秒探測一次 | `10` |
| `timeoutSeconds` | 單次探測最多等幾秒沒回應就算逾時失敗 | `1` |
| `successThreshold` | 連續成功幾次才視為「恢復正常」（`Failure`→`Success` 的判定次數） | `1`（`livenessProbe`/`startupProbe` 只能設 `1`，不能改） |
| `failureThreshold` | 連續失敗幾次才判定為「真的異常」，觸發重啟或移出 Endpoints | `3` |

- `successThreshold` 只有 `readinessProbe` 可以設大於 `1` 的值（例如要求連續成功 3 次才恢復接流量，避免服務忽好忽壞時流量一直被打進去又拔掉）；`livenessProbe`/`startupProbe` 這個欄位固定只能是 `1`，寫其他數字會被 API server 拒絕
- 同一個 container 可以**同時**設定 `livenessProbe`、`readinessProbe`、`startupProbe` 三種，互不衝突，各自獨立判斷、各自觸發各自的行為

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

## 題目13 - Liveness Probe 除錯（跨 namespace 找壞掉的 Pod）

**備註（原題）**：較為耗時，實際考試有 5 個 Pod 要查，Pod 要刪了重建。

**Quick Reference**：

- Cluster/配置環境：`dk8s`（跟前面題目用的 `k8s` 不同，這題原文就是寫 `dk8s`，照抄不改）

**題目敘述**：

> ⚠️ 必須先切換到正確的 Cluster/配置環境（`kubectl config use-context dk8s`），不這樣做可能導致零分。

由於 Liveness Probe 發生了問題，你無法存取一個應用程式。該應用程式可能在**任何 namespace** 中運行。

1. 找出對應的 Pod，並將其名稱和 namespace 寫入檔案 `/ckad/CKAD00011/broken.txt`，格式：
   ```text
   <namespaceName>/<podName>
   ```
   （檔案已存在）
2. 用 `kubectl get events` 取得相關錯誤事件，寫入檔案 `/ckad/CKAD00011/error.txt`，**必須用 `-o wide` 輸出格式**（不用會扣分）。（檔案已存在）
3. 修復故障 Pod 的 Liveness Probe 問題。

**相關資源**：[CKAD/13-broken-liveness.yaml](CKAD/13-broken-liveness.yaml)（自建的練習情境：`moth` namespace 下的 `moth-app` Pod，`livenessProbe` 故意打錯 port，模擬「Liveness Probe 設定錯誤」）

**解法指令**（已在本機 minikube 完整實測跑過一輪，包含刪除重建）：

```bash
kubectl config use-context dk8s

# 1. 部署練習情境，重現「Pod 因 liveness probe 失敗一直被重啟」
kubectl apply -f CKAD/13-broken-liveness.yaml
```

**第一步：跨所有 namespace 找出壞掉的 Pod**——這題的難點就是「不知道在哪個 namespace」：

```bash
# 1a. 先掃過所有 namespace 的 Pod，找 RESTARTS 異常或狀態不對勁的候選
kubectl get pods -A

# 1b. 對候選 Pod 用 describe，尾巴的 Events 區塊就能直接確認是不是 liveness probe 問題
#     （不用另外再打一次 kubectl get events，describe 本身就會帶最近的事件）
kubectl describe pod moth-app -n moth | tail
# Events:
#   Type     Reason     Age   From     Message
#   ----     ------     ----  ----     -------
#   Warning  Unhealthy  ...   kubelet  Liveness probe failed: Get "http://...:8080/": dial tcp ... connection refused
#   Normal   Killing    ...   kubelet  Container nginx failed liveness probe, will be restarted
```

確認 `moth` namespace 底下的 `moth-app` 就是壞掉的 Pod。

**第二步：寫入 `broken.txt`**：

```bash
mkdir -p /ckad/CKAD00011
echo "moth/moth-app" > /ckad/CKAD00011/broken.txt
```

**第三步：用 `-o wide` 抓相關錯誤事件寫入 `error.txt`**——**用 Pod 名稱 `grep`**，而不是用 `unhealthy` 這種關鍵字篩，也不是整包不篩：只篩關鍵字可能漏掉 `Killing`/`BackOff` 這些同樣相關但不含 `unhealthy` 字樣的事件；完全不篩，如果該 namespace 還有其他 Pod（practice 環境常常是這樣），會混進不相關的事件——**篩 Pod 名稱剛好precise 對到「這個 Pod 的所有事件」，不多不少**：

```bash
kubectl get events -n moth -o wide | grep moth-app > /ckad/CKAD00011/error.txt
```

**第四步：修復 Liveness Probe（Pod 要刪了重建，這是這題「較耗時」的原因）**——單獨的 Pod（不是透過 Deployment 管理）**沒辦法直接 `kubectl edit` 改 `livenessProbe`**，因為 container 相關欄位在 Pod 建立後是不可變的（immutable），只能：

```bash
# 1. 把現有 Pod 的 yaml 匯出
kubectl get pod moth-app -n moth -o yaml > moth-app.yaml

# 2. 先備份一份原始檔，之後改壞了、或要對照原本錯在哪，都還有得救
cp moth-app.yaml bak-moth-app.yaml

# 3. 編輯 moth-app.yaml，修正 livenessProbe.httpGet.port（8080 → 80）
sed -i 's/port: 8080/port: 80/' moth-app.yaml   # 依實際錯誤欄位調整，多處同值時建議手動開檔案編輯

# 4. 用匯出的 yaml 刪除舊 Pod（等同 kubectl delete pod moth-app -n moth）
kubectl delete -f moth-app.yaml

# 5. 用修好的 yaml 重新建立
kubectl apply -f moth-app.yaml
```

**驗證**：

```bash
kubectl get pod moth-app -n moth
# RESTARTS 應該停在 0，不再持續增加

kubectl get events -n moth --sort-by='.lastTimestamp' | tail -6
# 最後幾筆事件應該是 Pulled/Created/Started，沒有新的 Unhealthy
```

**對應考綱 Domain**：

`Application Observability and Maintenance`（15%）→ `Probes / health checks`、`Debugging in Kubernetes`（延續 [Record.md Day 11](Record.md#day-11) 學過的 `livenessProbe`，這題是第一次真正拿它來做**除錯**而不是建立，也是筆記系列第一次碰到「跨 namespace 找壞掉的物件」這種情境題）

**易錯點／踩坑筆記**：

- **「應用程式可能在任何 namespace」是這題最大的時間壓力來源**：不要一個一個 namespace 手動 `kubectl get pods -n X` 慢慢找，直接 `kubectl get pods -A` 或 `kubectl get events -A` 一次看全部；`kubectl get events -A --sort-by='.lastTimestamp'` 依時間排序、篩 `Unhealthy`/`Liveness` 關鍵字通常是最快定位到問題的方法，比盯著 RESTARTS 數字猜可靠——RESTARTS 數字可能因為 cluster 曾經重開機而每個 Pod 都有殘留次數，不代表「現在」還在壞
- **`broken.txt` 的格式是 `<namespace>/<podName>`，順序不要寫反**（不是 `<podName>/<namespace>`），這種純文字格式題，格式錯字面上就是錯，跟 yaml 語法錯誤一樣會被扣分，寫完最好 `cat` 出來確認一次
- **`-o wide` 是這題明確警告「不用會扣分」的必要 flag**，`kubectl get events` 預設輸出跟 `-o wide` 輸出的欄位不同（`-o wide` 會多列出 `SUBOBJECT`／`SOURCE`／`REPORTING CONTROLLER` 這類欄位），養成看到題目特別註明輸出格式，就照抄不要automatically 用預設值的習慣
- **單獨建立的 Pod，container 相關欄位（包括 `livenessProbe`）建立後不可變（immutable）**，`kubectl edit pod` 改這類欄位會被 API server 拒絕（`field is immutable`）——這也是備註寫「Pod 要刪了重建」的原因：正確流程是「匯出 yaml → 修正 → 刪除舊 Pod → apply 新 yaml」，這跟 [題目8](#題目8---修改-deployment-的-securitycontextrunasuser--allowprivilegeescalation) 修改 **Deployment** 的 SecurityContext 可以直接 `kubectl edit`／改完自動 rolling update 不同——Deployment 修改 Pod template 會觸發**新 Pod 自動取代舊 Pod**，但單獨的 Pod 沒有上層 controller 幫你做這件事，要手動刪除+重建
- 實際考試有 5 個 Pod 要一一檢查（這題備註提到的），代表**壞掉的 Pod 可能不只一個、或者要從 5 個候選裡篩出真正有問題的那個**——每找到一個「看起來有問題」的 Pod，先用 `kubectl describe pod` 或 `kubectl get events` 確認真的是 liveness probe 的問題（不是其他原因，例如 `ImagePullBackOff`、`OOMKilled`），避免抓錯目標寫進 `broken.txt`
- `sed -i 's/port: 8080/port: 80/'` 這種字串替換方式只適合「明確知道錯在哪一行、且不會誤改到其他相同字串」的簡單情況；如果 yaml 裡有多處 `port: 8080`（例如 `containerPort`跟 `livenessProbe.httpGet.port` 剛好都寫 `8080`），無腦 `sed` 可能會改錯地方，這種情況還是手動開檔案編輯比較保險
- **`kubectl describe pod <name> -n <ns> | tail` 是比另外打一次 `kubectl get events` 更快的候選確認法**：`describe pod` 輸出本身最後就有一段 `Events:`，`| tail` 直接看到最近幾筆，不用兩支指令來回切換——`kubectl get pods -A` 負責「大範圍篩出候選」，`describe ... | tail` 負責「針對候選快速確認原因」，兩者搭配比單用其中一個更快
- **修改前先 `cp` 一份備份再動手**（`cp moth-app.yaml bak-moth-app.yaml`）：這題流程有「匯出 → 編輯 → 刪除 → 重建」四個步驟，中間任何一步改錯（例如 `sed` 改壞了 yaml 格式、或改錯了欄位）都可能導致重建失敗，這時候已經先 `kubectl delete` 掉舊 Pod 了，沒有備份就等於三個步驟都要重來；養成修改任何「已經在 cluster 上運作」的物件前先備份一份原始 yaml 的習慣，是比較穩妥的除錯節奏，不只這題適用

## 題目14 - 幫既有 Deployment 加上 ReadinessProbe

**Quick Reference**：

- Cluster/配置環境：`dk8s`（原題只給了這行，沒有另外列 Quick Reference 區塊標明 namespace，練習先假設 `default`，實際考試以畫面上真正顯示的 namespace 為準）

**題目敘述**：

> ⚠️ 必須先切換到正確的 Cluster/配置環境（`kubectl config use-context dk8s`），不這樣做可能導致零分。

修改現有的 Deployment `probe-http`，增加 `readinessProbe` 探測器，規格如下：

- 使用 `httpGet` 進行探測
- 探測路徑為 `/healthz/return200`
- 探測 port 為 `80`
- 執行第一次探測前應等待 `15` 秒（`initialDelaySeconds`）
- 探測時間間隔為 `20` 秒（`periodSeconds`）

**相關資源**：[CKAD/14-probe-http-existing.yaml](CKAD/14-probe-http-existing.yaml)——**已經是修好之後的最終版本**（image 是 `vicuu/helloweb:v1`，這個 image 真的有實作 `/healthz/return200` 這個路徑，`readinessProbe` 也已經寫進去了），保留當作「答案參照」；下面的解法指令示範的是**考場實際情境**：假設一開始拿到的 `probe-http` 完全沒有 `readinessProbe`，示範怎麼用 `kubectl patch` 幫既有 Deployment 補上去

**解法指令**（已在本機 minikube 實測套用並驗證欄位正確、Pod 確實變成 `Ready`）：

```bash
kubectl config use-context dk8s

# 情境重現：先部署一份「還沒加 readinessProbe」的版本
kubectl create deployment probe-http -n default --image=vicuu/helloweb:v1 --port=80

# 用 kubectl patch 直接補上 readinessProbe（假設只有一個 container，index 是 0）
kubectl patch deployment probe-http -n default --type='json' -p='[
  {"op": "add", "path": "/spec/template/spec/containers/0/readinessProbe", "value": {
    "httpGet": {"path": "/healthz/return200", "port": 80},
    "initialDelaySeconds": 15,
    "periodSeconds": 20
  }}
]'
```

也可以用 `kubectl edit` 或「匯出 → 編輯 → apply」（沒有編輯器可用時的備案，見 [題目8](#題目8---修改-deployment-的-securitycontextrunasuser--allowprivilegeescalation)）手動補上同一段：

```yaml
        readinessProbe:
          httpGet:
            path: /healthz/return200
            port: 80
          initialDelaySeconds: 15
          periodSeconds: 20
```

**驗證**：

```bash
kubectl get deploy probe-http -n default -o jsonpath='{.spec.template.spec.containers[0].readinessProbe}'
# {"failureThreshold":3,"httpGet":{"path":"/healthz/return200","port":80,"scheme":"HTTP"},
#  "initialDelaySeconds":15,"periodSeconds":20,"successThreshold":1,"timeoutSeconds":1}

kubectl get pods -n default -l app=probe-http
# READY 應該是 1/1（用 vicuu/helloweb:v1 這個真的有實作該路徑的 image 才驗證得出來）
```

**對應考綱 Domain**：

`Application Observability and Maintenance`（15%）→ `Probes / health checks`（延續 [Record.md Day 11](Record.md#day-11) 的 `livenessProbe`跟[題目13](#題目13---liveness-probe-除錯跨-namespace-找壞掉的-pod) 的 debug 情境，這題是筆記系列第一次真正建立 `readinessProbe`）

**易錯點／踩坑筆記**：

- **`livenessProbe` 跟 `readinessProbe` 的 yaml 欄位結構完全一樣**（都是 `httpGet`/`tcpSocket`/`exec` + `initialDelaySeconds`/`periodSeconds`/`timeoutSeconds`/`successThreshold`/`failureThreshold`），差別純粹在**用途**：`livenessProbe` 探測失敗 → container 被 kubelet **重啟**；`readinessProbe` 探測失敗 → Pod 被**移出 Service 的 Endpoints**（不會重啟，只是暫時不接流量），兩者可以同時設定在同一個 container 上，互不衝突
- 沒有指定 `containerPort` 名稱時，`httpGet.port` 直接寫數字 `80` 就好，不用像 [Record.md Day 13](Record.md#day-13) 提過的可以用 named port 這種寫法，題目給的是數字就照抄數字
- 這題是**修改既有 Deployment**（不是新建），跟 [題目8](#題目8---修改-deployment-的-securitycontextrunasuser--allowprivilegeescalation)、[題目5](#題目5---修正-deployment-的記憶體-requestslimits依-namespace-limitrange) 是同一種題型套路——考場常見的「改一個已經在跑的物件」類型，重點永遠是先查清楚現況（`kubectl get deploy ... -o yaml`）、確認 container 名稱/index，再用 `edit`／`patch`／「匯出改完 apply」三選一動手，不要自己重寫一份新 yaml 整個 `apply` 蓋過去（容易漏掉原本就有的欄位，例如 `resources`、`env`）
- `kubectl set` 底下**沒有** `probe` 這個子指令（跟 `kubectl set env`/`kubectl set resources`/`kubectl set serviceaccount` 不同），沒有「一行指令幫 Deployment 加探測器」這種捷徑，只能透過 `edit`/`patch`/改 yaml 這幾種方式，考試時別浪費時間找不存在的指令
- 練習素材一開始用 `nginx:stable` 當 image，但 `nginx:stable` 沒有 `/healthz/return200` 這個路徑，探測會一直失敗、`READY` 卡在 `0/1`——只能驗證「yaml 欄位寫對」，驗證不了「Pod 真的變 `Ready`」；換成 `vicuu/helloweb:v1`（真的有實作這個路徑）之後，`READY` 才會變成 `1/1`。這也是一個提醒：**readinessProbe 探測會不會過，跟 yaml 語法對不對是兩回事**，yaml 寫得再標準，應用程式本身沒有那個 endpoint 一樣過不了，考試時如果 Pod 遲遲不 Ready，先確認題目給的路徑跟 image 是不是真的匹配，別只顧著檢查 yaml 縮排

## 題目15 - Deployment 升級策略、更新與回滾

**Quick Reference**：

- Cluster/配置環境：`k8s`
- Namespace：`default`

**題目敘述**：

> ⚠️ 必須先切換到正確的 Cluster/配置環境（`kubectl config use-context k8s`），不這樣做可能導致零分。

**情境（Context）**：需要更新一個應用程式，然後執行該更新的回滾。

**Task**：

1. 更新 namespace `default` 中的 Deployment `webapp` 的比例縮放配置，將 `maxSurge` 設為 `10%`，將 `maxUnavailable` 設為 `4`。
2. 更新 Deployment `webapp`，讓容器映像檔改用 `lfccncf/nginx` 的 `1.13.7` 版本標籤。
3. 將 Deployment `webapp` 回滾至前一版本。

**相關資源**：[CKAD/15-webapp-existing.yaml](CKAD/15-webapp-existing.yaml)（自建的練習用「既有」Deployment，初始 image 是 `lfccncf/nginx:1.13`）

**解法指令**（已在本機 minikube 完整實測三個步驟，包含驗證回滾後真的還原）：

```bash
kubectl config use-context k8s

# 部署練習用的「既有」Deployment
kubectl apply -f CKAD/15-webapp-existing.yaml
kubectl rollout status deployment/webapp -n default

# 1. 設定 maxSurge/maxUnavailable
kubectl patch deployment webapp -n default --type='json' -p='[
  {"op": "replace", "path": "/spec/strategy", "value": {
    "type": "RollingUpdate",
    "rollingUpdate": {"maxSurge": "10%", "maxUnavailable": 4}
  }}
]'

# 2. 更新 image 版本（container 名稱是 nginx，依實際 yaml 調整）
kubectl set image deployment/webapp nginx=lfccncf/nginx:1.13.7 -n default
kubectl rollout status deployment/webapp -n default

# 3. 回滾到前一版本
kubectl rollout undo deployment/webapp -n default
kubectl rollout status deployment/webapp -n default
```

`kubectl patch` 那段等價的 yaml 寫法（`kubectl edit`／匯出改 apply 都可以）：

```yaml
spec:
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 10%
      maxUnavailable: 4
```

**驗證**：

```bash
# 確認策略設定正確
kubectl get deploy webapp -n default -o jsonpath='{.spec.strategy}'
# {"rollingUpdate":{"maxSurge":"10%","maxUnavailable":4},"type":"RollingUpdate"}

# 確認回滾後 image 真的變回舊版本（不是還停在 1.13.7）
kubectl get deploy webapp -n default -o jsonpath='{.spec.template.spec.containers[0].image}'
# lfccncf/nginx:1.13

# 查看 rollout 歷史，確認多了一筆紀錄
kubectl rollout history deployment webapp -n default
```

**對應考綱 Domain**：

`Application Deployment`（20%）→ `Deployment 與 rolling update`（延續 [Record.md Day 8](Record.md#day-8) 學過的 `kubectl set image`、`rollout status/history/undo`、`maxSurge`/`maxUnavailable`，這題是把 Day 8 三個核心操作一次串起來考的整合題型）

**易錯點／踩坑筆記**：

- `maxSurge` 跟 `maxUnavailable` 都定義在 `spec.strategy.rollingUpdate` 底下，**不是** `spec.template` 裡的東西，改的時候不要跟 container 層級的設定搞混；這題 `maxSurge` 給的是百分比字串 `"10%"`，`maxUnavailable` 給的是純數字 `4`，**兩個欄位的型別是 `IntOrString`，可以混用數字跟百分比**，不用兩個都用同一種格式
- **`kubectl rollout undo` 只會回滾 `spec.template`（Pod 版本），不會動到 `spec.strategy`**：這題實測過，回滾後 `image` 確實變回 `lfccncf/nginx:1.13`，但 `maxSurge`/`maxUnavailable` 的設定完全沒被還原、依然是 `10%`/`4`——因為 `strategy` 是 Deployment 層級的設定，不屬於 ReplicaSet 版本歷史的一部分，`rollout undo` 只回滾「哪個 ReplicaSet 該是目前的版本」，題目要求的三個步驟做完，最終狀態應該是「新的 strategy + 舊的 image」，不是全部都變回最初的樣子，這是這題容易誤解的地方
- 實測 `kubectl rollout undo` 時會出現一個警告：`Warning: resource deployments/webapp was previously managed with 'kubectl apply'. Rolling back will not update the kubectl.kubernetes.io/last-applied-configuration annotation, which may cause unexpected behavior on future 'kubectl apply' operations.`——這是**正常的警告，不是錯誤**，代表回滾後如果之後又用 `kubectl apply -f 原本的yaml檔` 會蓋回 apply 檔案裡寫的版本（把回滾的結果又蓋掉），這題只要求「回滾」這個動作本身完成即可，不用理會這個警告，但要知道它在講什麼、之後不要不小心又 `apply` 舊檔案蓋掉回滾結果
- 沒有用 `--record` 或 `--record=true` 執行 `kubectl set image`，`kubectl rollout history` 的 `CHANGE-CAUSE` 欄位會是空的（`<none>`）——這題沒有要求要看 `CHANGE-CAUSE`，不影響解題，但如果考題要求「查看每次更新的原因」，記得更新指令要加 `--record`（雖然這個 flag 在新版 kubectl 已標示為 deprecated，但目前仍可用）
- 這題本質上是 [Record.md Day 8](Record.md#day-8) 三個指令的排列組合：`maxSurge`/`maxUnavailable` 設定 → `kubectl set image` 更新 → `kubectl rollout undo` 回滾，考試時不要漏掉任何一步，尤其是**順序**：要先更新（產生新版本），才有版本可以回滾，題目的步驟順序就是正確的操作順序，照著做即可

## 題目16 - ServiceAccount 命名規則、禁止自動掛載 Token、清理未使用的 SA

**Quick Reference**：

- Namespace：`qa`

**題目敘述**：

**情境（Context）**：組織的安全策略要求：

- ServiceAccount **不得自動掛載 API 憑據**
- ServiceAccount **名稱必須以 `-sa` 結尾**

清單檔案 `/cks/sa/pod1.yaml` 中指定的 Pod，因為 ServiceAccount 指定錯誤而無法建立。

**Task**：

1. 在現有 namespace `qa` 中建立一個名為 `backend-sa` 的新 ServiceAccount，確保這個 ServiceAccount **不自動掛載 API 憑據**。
2. 使用 `/cks/sa/pod1.yaml` 中的清單檔案來建立一個 Pod。
3. 最後，清理 namespace `qa` 中任何**未使用**的 ServiceAccount。

> 題號雖然編在 CKAD 練習序列裡，但題目風格（安全策略、ServiceAccount 治理）比較偏 **CKS**（Certified Kubernetes Security Specialist）的考點；CKAD 官方考綱裡跟這題最相關的還是 `ServiceAccounts` 這個知識點本身，題目多考的「命名規則」「禁止自動掛載」「清理未使用資源」則是更廣義的資安治理概念，CKAD/CKS 兩張證照在 `ServiceAccounts` 這塊知識是共用、互通的。

**相關資源**：[CKAD/16-qa-setup.yaml](CKAD/16-qa-setup.yaml)（自建的練習用「既有」狀態：`qa` namespace + `frontend-sa`（被 `frontend` Pod 使用中）+ `old-token-sa`（沒人用，練習清理用））、[CKAD/16-pod1-broken.yaml](CKAD/16-pod1-broken.yaml)（模擬考場的 `/cks/sa/pod1.yaml`，`serviceAccountName` 一開始故意指定錯誤）

**解法指令**（已在本機 minikube 完整實測三個步驟）：

```bash
# 部署練習用的既有狀態
kubectl apply -f CKAD/16-qa-setup.yaml

# 印證題目描述：直接套用「錯誤」的 pod1.yaml 會直接被拒絕，根本建不起來
kubectl apply -f CKAD/16-pod1-broken.yaml
# Error from server (Forbidden): pods "pod1" is forbidden:
# error looking up service account qa/backend: serviceaccount "backend" not found

# 1. 建立 backend-sa，關閉自動掛載 API 憑據
kubectl create serviceaccount backend-sa -n qa
kubectl patch serviceaccount backend-sa -n qa -p '{"automountServiceAccountToken": false}'

# 2. 修正 pod1.yaml 的 serviceAccountName，再建立 Pod
sed -i 's/serviceAccountName: backend/serviceAccountName: backend-sa/' CKAD/16-pod1-broken.yaml
kubectl apply -f CKAD/16-pod1-broken.yaml

# 3. 找出並清理未使用的 ServiceAccount
kubectl get sa -n qa
kubectl get pods -n qa -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.serviceAccountName}{"\n"}{end}'
# 兩份清單對照，SA 清單裡有、但沒有任何 Pod 在用的，就是要刪的（這裡是 old-token-sa）
kubectl delete sa old-token-sa -n qa
```

`kubectl create serviceaccount` 沒有 `--automount` 這種 flag，`automountServiceAccountToken` 只能建立後用 `patch`／`edit`／yaml 補上：

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: backend-sa
  namespace: qa
automountServiceAccountToken: false
```

**驗證**：

```bash
kubectl get sa backend-sa -n qa -o yaml | grep automount
# automountServiceAccountToken: false

kubectl get pod pod1 -n qa
# READY 1/1，Running

# 確認真的沒有 token 被掛進去
kubectl exec pod1 -n qa -- ls /var/run/secrets/kubernetes.io/serviceaccount/
# ls: cannot access '/var/run/secrets/kubernetes.io/serviceaccount/': No such file or directory

kubectl get sa -n qa
# 應該只剩 default／frontend-sa／backend-sa，old-token-sa 已經不見
```

**對應考綱 Domain**：

`Application Environment, Configuration and Security`（25%）→ `ServiceAccounts`（延續 [Record.md Day 32](Record.md#day-32) 學過的 `ServiceAccount` 基礎，這題深入到 `automountServiceAccountToken` 這個安全性欄位、以及「清理未使用資源」這種治理性任務）

**易錯點／踩坑筆記**：

- **Pod 引用不存在的 ServiceAccount，不是「排程失敗」（`Pending`），而是直接在建立階段被拒絕**：實測 `kubectl apply` 直接回傳 `Error from server (Forbidden): ... serviceaccount "backend" not found`，Pod 物件連建都建不起來，這跟資源不足導致 `Pending` 的排程失敗是完全不同的失敗階段——`ServiceAccount` 存在與否是在 API server 的 admission 階段就檢查，比 scheduler 排程還要早一步
- `automountServiceAccountToken` 這個欄位**在 `ServiceAccount` 跟 `Pod` 兩個層級都存在**：`ServiceAccount` 層級設 `false` 是「這個身份預設不掛 token」，`Pod.spec.automountServiceAccountToken` 則是**該 Pod 自己的設定，會覆蓋 ServiceAccount 層級的值**——這題只要求 ServiceAccount 層級不自動掛載，題目沒特別要求 Pod 層級也要設，設在 SA 層級對所有用這個 SA 的 Pod 都有效，比每個 Pod 各自設更省事，也更符合「組織安全策略」這種「一次設定、全體套用」的治理精神
- **`kubectl create serviceaccount` 沒有對應的 flag 可以直接指定 `automountServiceAccountToken`**（不像 `kubectl create secret` 有 `--from-literal`），只能先建立、再用 `kubectl patch`／`kubectl edit`／改 yaml 補上，這跟[題目14](#題目14---幫既有-deployment-加上-readinessprobe)發現「`kubectl set` 沒有 `probe` 子指令」是同一種提醒：不是每個物件、每個欄位都有指令式捷徑，該回 yaml 就回 yaml
- **判斷「未使用」的方法：拿 `kubectl get sa` 的清單，去對照 `kubectl get pods -o jsonpath='{...spec.serviceAccountName}'` 這種列出「每個 Pod 實際用哪個 SA」的清單**，兩邊一比對，SA 清單裡有、但沒有任何 Pod 引用到的，就是未使用——不要單純看 SA 的 `AGE` 或用猜的，也不要漏掉「有些 Pod 可能沒寫 `serviceAccountName`」這種隱性使用 `default` 的情況（這種 Pod 的 `jsonpath` 輸出會是空字串，不是完全沒有值）
- **`default` 這個系統自動產生的 ServiceAccount，慣例上不算進「未使用要清理」的範圍**，就算目前沒有 Pod 明確指定用它，也不建議刪除——它是每個 namespace 天生就有的資源（[Record.md Day 32](Record.md#day-32) 提過），清理未使用 SA 這種任務通常針對「使用者自己建立的」SA，不是系統自動管理的物件
- 這題的**核心精神是「安全治理」而不是「單純的 CRUD」**：`-sa` 命名規則、禁止自動掛載 token、清理未使用資源，三件事合起來是在降低「多餘的 ServiceAccount 帶著能打 API 的憑證到處留著」這種攻擊面——跟 [Record.md Day 32](Record.md#day-32) 討論過的「最小權限原則」（`Role` 只給需要的 `verbs`）是同一種資安思維的不同層面：一個管「能做什麼」，一個管「憑證會不會被不必要地掛出去、留下來」

## 題目17 - 更新 Deployment 並暴露 Service

**備註（原題）**：建議導出 yaml 修改後重建。

**Quick Reference**：

- Cluster/配置環境：`k8s`
- Namespace：`ckad00017`

**題目敘述**：

> ⚠️ 必須先切換到正確的 Cluster/配置環境（`kubectl config use-context k8s`），不這樣做可能導致零分。

**情境（Context）**：需要擴展一個現有的應用程式，並將其公開在基礎設施內。

**Task**：

1. 更新 namespace `ckad00017` 中的 Deployment `ckad00017-deployment`：
   - 讓它運行 **5 個 Pod 副本**
   - 為 Pod 加上標籤 `tier: dmz`
2. 在 namespace `ckad00017` 中建立一個名為 `rover` 的 **NodePort** Service，在 **TCP port 81** 上公開 Deployment `ckad00017-deployment`。

**相關資源**：[CKAD/17-ckad00017-deployment.yaml](CKAD/17-ckad00017-deployment.yaml)（修改「既有」Deployment 後的目標狀態，image 是 `vicuu/nginx:hello81`——這個 image 真的有實作監聽在 81 port、回應 `Hello World ^_^ / Port 81`）、[CKAD/17-rover-service.yaml](CKAD/17-rover-service.yaml)（新建的 NodePort Service）——**已在本機 minikube 完整實測，包含中間踩過的幾個坑**

**解法指令**：

```bash
kubectl config use-context k8s

# 1. 依備註建議，先把既有 Deployment 匯出成 yaml 再修改（比直接 kubectl edit 更好掌握變更）
kubectl get deploy ckad00017-deployment -n ckad00017 -o yaml > ckad00017-deployment.yaml
# 編輯 ckad00017-deployment.yaml：
#   spec.replicas 改成 5
#   spec.template.metadata.labels 加上 tier: dmz（不要動 spec.selector！）
kubectl apply -f ckad00017-deployment.yaml

# 2. 建立 NodePort Service
kubectl apply -f CKAD/17-rover-service.yaml
# 或指令式一步到位：
kubectl expose deployment ckad00017-deployment -n ckad00017 \
  --name=rover --type=NodePort --port=81 --target-port=81
```

`CKAD/17-ckad00017-deployment.yaml` 關鍵欄位：

```yaml
spec:
  replicas: 5
  selector:
    matchLabels:
      app: ckad00017-deployment   # 不能改，immutable
  template:
    metadata:
      labels:
        app: ckad00017-deployment
        tier: dmz                 # 新加的標籤
    spec:
      containers:
      - name: nginx
        image: vicuu/nginx:hello81   # 這個 image 真的監聽在 81，不是預設的 80
        ports:
        - containerPort: 81
```

`CKAD/17-rover-service.yaml` 關鍵欄位：

```yaml
spec:
  type: NodePort
  selector:
    app: ckad00017-deployment     # 對到 Deployment 的 Pod 標籤，扁平寫法，不要多包一層
  ports:
  - protocol: TCP
    port: 81
    targetPort: 81                # 對到 image 實際監聽的 81，不是隨便填數字
```

**驗證**（依序排除三種常見卡住的原因，已實測跑過一輪）：

```bash
kubectl get deploy ckad00017-deployment -n ckad00017
# REPLICAS 應該是 5/5

kubectl get pods -n ckad00017 --show-labels
# 應該看到每個 Pod 都有 tier=dmz

kubectl get svc rover -n ckad00017
# TYPE 是 NodePort，PORT(S) 應該是 81:<隨機nodePort>/TCP

# 關鍵一步：先確認 Service 真的有連到 Pod（Endpoints 不能是 <none>）
kubectl get endpoints rover -n ckad00017
# 應該列出 5 個 <PodIP>:81

# 從 host 機器測 NodePort（minikube docker driver 用這個，不是 ClusterIP）
curl http://$(minikube ip):<nodePort>
# Hello World ^_^ / Port 81

# 或用 minikube 內建指令自動組好 URL
minikube service rover -n ckad00017 --url
```

**對應考綱 Domain**：

`Application Deployment`（20%）→ 修改既有 Deployment（延續 [題目5](#題目5---修正-deployment-的記憶體-requestslimits依-namespace-limitrange)/[題目8](#題目8---修改-deployment-的-securitycontextrunasuser--allowprivilegeescalation) 的套路）、`Services and Networking`（20%）→ `建立與除錯 Service 存取`（延續 [Record.md Day 9](Record.md#day-9) 的 `NodePort` 類型、[Record.md Day 13](Record.md#day-13) 的 port/targetPort 對照）

**易錯點／踩坑筆記**：

- **`spec.selector.matchLabels` 是 immutable（建立後不可修改）欄位**：這題「幫 Pod 加標籤」的正確位置是 **`spec.template.metadata.labels`**，不是 `spec.selector`——如果手滑把新標籤也加進 `spec.selector.matchLabels`，`kubectl apply` 會直接被拒絕（`field is immutable`）。只要 `template.labels` 有涵蓋 `selector` 原本要求的 key/value，多加其他標籤完全不影響 selector 照常匹配
- 備註「建議導出 yaml 修改後重建」對 **Deployment** 而言，實際上是「匯出 → 編輯 → `kubectl apply`」（跟 [公用知識](#修改既有物件優先用匯出--編輯--apply少用-kubectl-edit) 提過的做法一致），**不是**像 [題目13](#題目13---liveness-probe-除錯跨-namespace-找壞掉的-pod) 那種單獨 Pod 需要真的 `delete` 再重建——Deployment 修改 `template`／`replicas` 直接 `apply` 就會觸發 rolling update，用不著刪除
- **`Service.spec.selector` 是扁平的 key/value map，不能多包一層 `labels:`**——實測踩過這個坑：`selector: {labels: {app: xxx}}` 這種寫法 `kubectl apply` 會直接報 `unrecognized type: string` 錯誤，正確寫法是 `selector: {app: xxx}` 直接放，跟 `matchLabels` 底下那層很像但**不是同一種欄位結構**，容易搞混
- **`selector` 對錯人 namespace/名稱，Service 會建立成功但完全連不到任何 Pod**：實測套用過一份 `selector: {app.kubernetes.io/name: MyApp}` 的 yaml，`kubectl apply` 沒有報錯、Service 也正常建立，但 `kubectl get endpoints rover` 顯示 `<none>`——**Service 建立成功≠設定正確**，`selector` 打錯字或用錯 key，Kubernetes 不會主動告訴你「找不到 Pod」，一定要額外查 `Endpoints` 才會發現
- **`type` 沒寫會預設變成 `ClusterIP`**，不是 `NodePort`，這題明確要求 `NodePort`，`spec.type: NodePort` 這個欄位不能漏
- **`containerPort`/`targetPort` 該填多少，取決於這題實際用的 image**：這題用的是 `vicuu/nginx:hello81`——這是特別做來監聽在 81 port 的自訂 image（回應內容就寫著 `Port 81`），所以這題 `targetPort: 81` 才是對的；如果換成一般 `nginx:stable`/`nginx:1.14.2` 這種預設監聽 80 的標準 image，就要填 `80`——**沒有一體適用的答案，永遠要先確認 image 實際監聽哪個 port**，不能看到題目給的數字就直接套用到 `targetPort`
- **`ClusterIP` 從 host 機器（minikube 外部）是打不通的，這是設計上的本質限制，不是設定錯誤**：實測 `curl <ClusterIP>:81` 從 host 終端機執行會直接 hang 住（timeout），但同一個 `curl <ClusterIP>:81` 在 `minikube ssh` 進去 node 裡面執行卻能正常回應——ClusterIP 只是 cluster 內部 iptables/ipvs 轉發規則產生的虛擬位址，只有 **Pod 或 Node 自己**能路由到它，host 機器在這個網路範圍之外
- **`ClusterIP` 跟 `NodePort` 是兩個獨立的位址/port 組合，不能混搭**：`curl <ClusterIP>:<nodePort>` 這種寫法一定打不通，因為 NodePort 是開在**每個 Node 的實體 IP** 上（`minikube ip` 拿到的位址），不是開在 ClusterIP 上，`ClusterIP` 那個位址上根本沒人監聽 nodePort 那個號碼
- **從 host 機器驗證 minikube 的 NodePort Service，有三種可行方式**：① `curl http://$(minikube ip):<nodePort>`（最直接）、② `minikube service <svc> -n <ns> --url`（minikube 內建指令自動組好 URL）、③ `minikube ssh` 進節點內部後改用 `curl <ClusterIP>:<port>` 或 `curl localhost:<nodePort>`；另外也可以用 `kubectl run <tmp-pod> --rm -i --restart=Never --image=curlimages/curl -- curl <ClusterIP>:<port>` 建一個用完即丟的 Pod，從 cluster 內部直接測 ClusterIP，不用進 node
- 排查「Service 連不通」的建議順序：① `kubectl get endpoints <svc>` 確認有沒有連到 Pod（沒有就是 `selector` 錯）→ ② `kubectl get svc <svc>` 確認 `type`/`port` 對不對 → ③ 確認 `targetPort` 對不對到 container 實際監聽的 port → ④ 確認自己是從**哪裡**測試（host 只能用 NodePort、cluster 內部才能用 ClusterIP），這四層任何一層錯了都會讓 `curl` 打不通，但錯誤訊息（或根本沒有錯誤訊息）不會直接告訴你是哪一層，要照順序一步步排除

## 題目18 - 用既有 NetworkPolicy 限制 Pod 只能跟指定對象通訊

**Quick Reference**：

- Cluster/配置環境：`nk8s`（跟前面題目的 `k8s`/`dk8s` 都不同，原題就是寫 `nk8s`，照抄不改）
- Namespace：`ckad00018`

**題目敘述**：

> ⚠️ 必須先切換到正確的 Cluster/配置環境（`kubectl config use-context nk8s`），不這樣做可能導致零分。

**情境（Context）**：需要讓一個 Pod 只跟其他兩個指定的 Pod 通訊，不能跟這兩個以外的 Pod 通訊。

**Task**：更新 namespace `ckad00018` 中的 Pod `ckad00018-newpod`，使其套用一個**只允許此 Pod 與 Pod `front` 和 `db` 之間收發流量**的 NetworkPolicy。

> ℹ️ 提示：所有必要的 NetworkPolicy **均已建立**。

> ⚠️ 警告：完成這題時，**不能 create／modify／delete 任何 NetworkPolicy**，只能使用現有的 NetworkPolicy。

**這題的關鍵推理**：題目只叫你改 **Pod**，明確禁止碰 NetworkPolicy——代表 NetworkPolicy 的 `podSelector` 早就設定好了、只是還沒有 Pod 符合那個 selector。`ckad00018-newpod` 現在會被限制，唯一能做的事就是**幫它加上正確的 label**，讓它「被選中」去套用那條既有的 NetworkPolicy，不是去寫網路規則本身。

**相關資源**：

- [CKAD/18-build-env.yaml](CKAD/18-build-env.yaml)——環境模擬用，`ckad00018` namespace + `front`/`db` 兩個 Pod（`app: front`/`app: db`）
- [CKAD/18-networkpolicy.yaml](CKAD/18-networkpolicy.yaml)——**僅供環境模擬／參考**，模擬考場已經存在的兩條 NetworkPolicy，**不是這題要交出去的答案**：
  - `db-front`：管制 `app: db` 這個 Pod，只放行帶有 `db-access: "true"` 標籤的對象
  - `access-front`：管制 `app: front` 這個 Pod，只放行帶有 `front-access: "true"` 標籤的對象
- [CKAD/18-ckad00018-newpod.yaml](CKAD/18-ckad00018-newpod.yaml)——**這題唯一該修改的物件**，要同時加上 `front-access: "true"` 跟 `db-access: "true"` 兩個標籤

> 已在本機 minikube 完整套用並實測驗證（含正向連線測試 + 意外發現的 CNI 未強制執行問題，見下方踩坑筆記）。

**這題的關鍵推理，跟原本以為的不太一樣**：一開始以為會有一條「專門管 `ckad00018-newpod`」的 NetworkPolicy，但實際環境是**反過來的設計**——`front`、`db` 各自有一條 NetworkPolicy 管制「誰可以連自己」，`ckad00018-newpod` 本身完全沒有專屬規則。所以 `newpod` 要跟 `db` 通，靠的是滿足 `db-front` 這條規則的 `db-access: "true"`；要跟 `front` 通，靠的是滿足 `access-front` 這條規則的 `front-access: "true"`——**兩個目標各自對應一條規則、各自要求一個標籤，兩個都要加，缺一個就只能通一邊**。

**解法指令**（已實測跑過整個流程）：

```bash
kubectl config use-context nk8s

# 1. 先查清楚 namespace 裡有哪些既有的 NetworkPolicy，看它們各自的 podSelector 管的是誰
kubectl get networkpolicy -n ckad00018
# NAME           POD-SELECTOR   AGE
# access-front   app=front      ...
# db-front       app=db         ...
kubectl get networkpolicy -n ckad00018 -o yaml
# 確認 access-front 要求 front-access: "true"、db-front 要求 db-access: "true"

# 2. 確認 ckad00018-newpod「現在」的標籤
kubectl get pod ckad00018-newpod -n ckad00018 --show-labels

# 3. 補上兩個 NetworkPolicy 各自要求的標籤（記得帶 Pod 名稱！）
kubectl label pod ckad00018-newpod -n ckad00018 front-access=true
kubectl label pod ckad00018-newpod -n ckad00018 db-access=true
```

`CKAD/18-ckad00018-newpod.yaml` 關鍵欄位：

```yaml
metadata:
  name: ckad00018-newpod
  namespace: ckad00018
  labels:
    front-access: "true"   # 對到 access-front 這條規則
    db-access: "true"      # 對到 db-front 這條規則
```

**驗證**（已實測）：

```bash
kubectl get pod ckad00018-newpod -n ckad00018 --show-labels
# labels 應該同時有 front-access=true, db-access=true

# 正向連線測試：newpod 連 front、db 都應該通
FRONT_IP=$(kubectl get pod front -n ckad00018 -o jsonpath='{.status.podIP}')
DB_IP=$(kubectl get pod db -n ckad00018 -o jsonpath='{.status.podIP}')
kubectl exec ckad00018-newpod -n ckad00018 -- curl -s -m 4 -o /dev/null -w "HTTP %{http_code}\n" http://$FRONT_IP
kubectl exec ckad00018-newpod -n ckad00018 -- curl -s -m 4 -o /dev/null -w "HTTP %{http_code}\n" http://$DB_IP
# 兩個都應該是 HTTP 200

# 反向測試：沒有 front-access 標籤的第三方 Pod，理論上應該連不到 front
kubectl run outsider -n ckad00018 --image=curlimages/curl --restart=Never -- sleep 3600
kubectl exec outsider -n ckad00018 -- curl -s -m 4 -o /dev/null -w "HTTP %{http_code}\n" http://$FRONT_IP
kubectl delete pod outsider -n ckad00018
```

**對應考綱 Domain**：

`Services and Networking`（20%）→ `NetworkPolicies`（這是筆記系列第一次涉及這個知識點，`Record.md` CKAD TEST 章節目前標註「尚未涉及」）

**易錯點／踩坑筆記**：

- **NetworkPolicy 不是「指定 Pod 名稱」去管控，而是透過 `podSelector`（label selector）去選中一群 Pod**，這是這題最核心的觀念：`front`、`db`、`ckad00018-newpod` 三個角色的名稱完全不會出現在 NetworkPolicy 的 yaml 裡，只會看到 `matchLabels`——這也是為什麼題目可以合理要求「不能碰 NetworkPolicy，只能改 Pod」：規則早就用標籤定義好了，缺的只是「哪些 Pod 符合這個標籤」
- **規則可能是「掛在對方身上」，不是「掛在自己身上」**：這題一開始容易誤以為要找一條專門管 `ckad00018-newpod` 的 NetworkPolicy，但實際環境是 `db-front`（管 `app: db`）、`access-front`（管 `app: front`）各自獨立管制「誰可以連我」，`newpod` 完全沒有專屬規則——`newpod` 要做的是**滿足對方規則裡對「訪客」的標籤要求**，而不是找一條寫著自己名字的規則。讀題時如果只找「跟 `newpod` 有關」的規則會找不到重點，正確做法是找「跟 `front`/`db` 有關」的規則，看它們各自要求訪客帶什麼標籤
- **兩個目標（`front`、`db`）各自對應一條獨立規則，兩個標籤都要加，不是加一個就兩邊都通**：`db-front` 只認 `db-access: "true"`，`access-front` 只認 `front-access: "true"`，這是兩條互相獨立的規則，`newpod` 要兩個目標都連得到，兩個標籤缺一不可——這跟原本猜測「一條規則、一個標籤」的簡化情境不同，實際環境比較貼近真實場景：每個服務自己管自己的存取名單，而不是有一個中央規則管全部人
- `kubectl label pod -n ckad00018 front-access=true` 這種寫法**漏了 Pod 名稱**，實測會直接報錯 `error: resource(s) were provided, but no name was specified`——`kubectl label` 的正確語法是 `kubectl label <resource-type> <resource-name> -n <namespace> <key>=<value>`，資源名稱是必填，不能只給 namespace
- `NetworkPolicy` 的 `ingress`（誰可以連進來）跟 `egress`（自己可以連出去給誰）**是分開控制的兩個方向**，這題兩條規則都同時列了 `Ingress`、`Egress`，也各自在兩個方向都寫了同樣的標籤條件——只寫一半會漏掉一個方向的限制
- **一旦 `NetworkPolicy.spec.podSelector` 選中了某個 Pod，那個 Pod 在對應方向就會從「預設全開放」變成「預設全封鎖，只有規則允許的才通」**——這是白名單機制，加標籤這個動作本身就會產生限制效果，不用另外「啟用」
- **重要實測結果：這個 minikube 環境的 NetworkPolicy 完全沒有被強制執行**——標籤、規則都設定正確，`newpod` 加標籤前後連線都是 `HTTP 200`；額外測試一個完全沒有 `front-access` 標籤的第三方 Pod（`outsider`）去連 `front`，**結果同樣是 `HTTP 200`，理論上應該被擋下來卻沒有**。檢查 `kube-system` 底下沒有 Calico/Cilium/Weave 這類支援 NetworkPolicy 的 CNI 插件，證實這個環境用的是不支援 NetworkPolicy 的預設 CNI——**`kubectl apply` 成功、`kubectl get networkpolicy` 也能查到規則，不代表規則真的有在擋流量**，這是本機練習環境的限制，跟 yaml 寫得對不對無關；實際 CKAD 考場的沙盒環境通常會配置支援 NetworkPolicy 的 CNI（不然這類考題就沒有意義了），但本機練習如果看到「規則設定正確、連線卻還是全部打通」，不要自我懷疑 yaml 哪裡寫錯，先確認 CNI 支援度
- [CKAD/18-networkpolicy.yaml](CKAD/18-networkpolicy.yaml) 只是環境模擬用的參考檔，**不是**這題要交的答案——這題真正的答案只有 [CKAD/18-ckad00018-newpod.yaml](CKAD/18-ckad00018-newpod.yaml) 這一份，考試時千萬別誤把心力花在改 NetworkPolicy 上，題目已經明確警告不能動它

## 題目19 - Ingress 排錯-1

**備註（原題）**：`svc` 的 `targetPort` 對應 `deployment` 的 `containerPort`。

**Quick Reference**：

- Cluster/配置環境：`k8s`
- Namespace：`ingress-ckad`

**題目敘述**：

> ⚠️ 必須先切換到正確的 Cluster/配置環境（`kubectl config use-context k8s`），不這樣做可能導致零分。

在 namespace `ingress-ckad` 下，`deployment`、`service`、`ingress` 三個資源已經部署好了，但配置有問題，導致 Ingress 網路不通。3 個資源的配置清單在目錄 `/ckad/CKAD202206` 中，請修改為正確的，並重新建立。

> ⚠️ 重要注意事項：這題的 **Deployment 是正確的，請不要修改 Deployment**。

**這題的解題範圍**：題目已經明講 Deployment 沒問題，代表**只有 Service、Ingress 兩份檔案要檢查**，不用浪費時間去懷疑 Deployment；備註又提示「`targetPort` 要對應 `containerPort`」，但**實測後發現真正的 bug 不是 `targetPort`，而是 `selector`**——備註是通用提醒（這類 port 對應錯誤很常考），不代表這題唯一的錯誤方向就在那裡，讀提示要小心別被錯誤方向帶偏。

**相關資源**：[CKAD/19-deployment.yaml](CKAD/19-deployment.yaml)（正確，不要修改）、[CKAD/19-service.yaml](CKAD/19-service.yaml)、[CKAD/19-ingress.yaml](CKAD/19-ingress.yaml)——**已在本機 minikube 完整實測並排錯成功**

**真正的 bug 在哪裡**：

```yaml
# Deployment 的 Pod labels 實際上是：
labels:
  name: nginx-ing        # ← key 是 name

# 但 Service 原本寫的 selector 是：
selector:
  app: nginx-ing          # ← key 打成 app，跟 Pod 標籤的 key 對不上，完全選不到任何 Pod
```

`targetPort: 81` 反而是對的——這份 Deployment 用的 `image: vicuu/nginx:hello81` 就是[題目17](#題目17---更新-deployment-並暴露-service)聊過的那個自訂 image，真的監聽在 81，跟 `containerPort: 81` 一致，備註提示在這題其實沒有踩到雷，真正踩雷的是 **selector 的 key 打錯**，`kubectl get endpoints` 顯示 `<none>` 才抓到。

Ingress 額外還有一個**非阻塞性**的疑慮：只用了舊版 annotation `kubernetes.io/ingress.class: "nginx"`，沒有寫新版標準的 `spec.ingressClassName: nginx`。實測查過這個環境的 `ingress-nginx` controller（v1.14.3）啟動參數有 `--watch-ingress-without-class=true`，所以沒設定 class 的 Ingress 一樣會被處理——這題**不影響連線**，但嚴格來說是過時寫法，遇到沒開這個參數的環境就會出問題。

**解法指令**（已實測跑過整個排錯流程）：

```bash
kubectl config use-context k8s

# 1. 三份資源都看過一輪（Deployment 不用查，題目說是對的）
kubectl get deploy,svc,ingress -n ingress-ckad

# 2. 對照 Pod 實際標籤 vs Service selector（這一步就抓到 key 打錯）
kubectl get pods -n ingress-ckad --show-labels
kubectl get svc nginx-ing-svc -n ingress-ckad -o jsonpath='{.spec.selector}'
kubectl get endpoints nginx-ing-svc -n ingress-ckad
# Endpoints 是 <none> → selector 沒選到任何 Pod，這就是真正的 bug

# 3. 修正 Service 的 selector（key 從 app 改成 name），重新套用
kubectl apply -f CKAD/19-service.yaml

# 4. 再次確認 Endpoints 有進去了
kubectl get endpoints nginx-ing-svc -n ingress-ckad
```

`CKAD/19-service.yaml` 修正重點：

```yaml
spec:
  selector:
    name: nginx-ing   # 原本錯寫成 app: nginx-ing，key 對不上 Pod 實際標籤
```

**驗證**（已實測，兩層都測過）：

```bash
# 查 Ingress Controller 怎麼對外曝露
kubectl get svc -n ingress-nginx
# ingress-nginx-controller 是 NodePort，80:31280/TCP

# 只測 Service（跳過 Ingress，快速排除是不是 Service 本身的問題）
minikube ssh -- "curl http://10.96.54.242:80"
# Hello World ^_^ / Port 81

# 測完整 Ingress 路徑（帶題目路徑 /hello）
minikube ssh -- "curl http://192.168.49.2/hello"
# Hello World ^_^ / Port 81
```

兩層都回應 `Hello World ^_^ / Port 81`，確認排錯成功。

**對應考綱 Domain**：

`Services and Networking`（20%）→ `建立與除錯 Service 存取`、`Ingress`（延續 [Record.md Day 19](Record.md#day-19) 的 Ingress 基礎、[Record.md Day 13](Record.md#day-13) 的 port/targetPort 對照，這題把兩者串成一個綜合除錯題）

**易錯點／踩坑筆記**：

- **題目明講「Deployment 是對的、不要動」，這既是提示也是約束**——提示：把檢查範圍縮小到兩份檔案，省時間；約束：就算你懷疑 Deployment 哪裡怪，也不能動它，改了 Deployment 就是不照題目要求，就算意外把服務修通了也可能被扣分
- **備註提示的方向不一定是這題實際的 bug 所在**：備註寫「`targetPort` 對應 `containerPort`」，這題實測後這個對應關係其實是對的（`81` = `81`），真正的 bug 是 **`selector` 的 key 打錯**（`app` vs `name`）——備註更像是「這類題目常見的檢查項目」提醒，不是「這題唯一的答案」，**不能只顧著查提示提到的那個地方，其他欄位也要照排查順序過一遍**，不然容易漏掉真正的 bug
- **`Service.spec.selector` 的 key 打錯，不會讓 `kubectl apply` 報錯**，Service 一樣能成功建立，`TYPE`/`PORT(S)` 看起來都正常——因為 selector 只是一個 map，Kubernetes 不會檢查這個 key 是否真的對應到任何 Pod 的標籤。**唯一能抓到這種錯誤的方法是查 `kubectl get endpoints`**，`Endpoints` 是 `<none>` 就代表 selector 沒選到任何東西，這是排查「Service 建立成功但連不通」最關鍵的一步，[題目17](#題目17---更新-deployment-並暴露-service) 也踩過同樣的坑
- `Ingress.spec.rules[].http.paths[].backend.service.name` 打錯字（或名稱對不上實際的 Service）一樣不會讓 `kubectl apply` 報錯，要用 `kubectl describe ingress` 看 `Backends` 那一欄才抓得到——這題雖然這次沒踩到這個坑（Service 名稱有對上），但排查順序上這是跟 selector 錯誤同一等級、容易被忽略的地方
- **舊版 `kubernetes.io/ingress.class` annotation vs 新版 `spec.ingressClassName`**：現代 `ingress-nginx`（v1.x）預設只認 `ingressClassName`，除非 controller 有開 `--watch-ingress-without-class=true` 才會相容舊 annotation——這題環境剛好有開，所以沒有造成連線問題，但這是**環境相依**的行為，不是 Ingress 語法本身保證正確，實際考場如果 `kubectl get ingress` 顯示 `CLASS: <none>` 卻連不通，這就是該檢查的方向
- 排查「Ingress 打不通」的建議順序：① 確認 Deployment 的 Pod 是否 `Running`（這題已知沒問題可跳過）→ ② `kubectl get endpoints <svc>` 確認 Service 有沒有連到 Pod（這題卡在這一步：selector 錯）→ ③ `kubectl describe ingress` 確認 `Backends` 有沒有指到健康的 Service/Pod → ④ 確認 Ingress Controller 本身是否正常運作、有沒有指定 `ingressClassName`
- **驗證要分層測試**：先測 Service（`curl <ClusterIP>:<port>`）排除是不是 Service 本身的問題，再測完整 Ingress 路徑（打 Ingress Controller 的入口 + 題目指定的路徑），兩層都要從 **`minikube ssh` 內部**測（host 機器打不到 ClusterIP，這是[題目17](#題目17---更新-deployment-並暴露-service)學過的網路範圍限制）；`ingress-nginx` 在 minikube 上除了 `NodePort`，也會直接綁在節點的 80/443（`minikube ip` 那個位址），所以進到 `minikube ssh` 之後直接打 `192.168.49.2/hello` 或 `localhost:31280/hello` 都能測到完整路徑

## 題目20 - Ingress 排錯-2

**備註（原題）**：對應的 svc 不存在。

**Quick Reference**：

- Cluster/配置環境：`k8s`
- Namespace：`ingress-kk`

**題目敘述**：

> ⚠️ 必須先切換到正確的 Cluster/配置環境（`kubectl config use-context k8s`），不這樣做可能導致零分。

在 namespace `ingress-kk` 下有一個 Ingress，但它似乎無法被正常存取，請找出原因並修復。

> ⚠️ 重要注意事項：這題的 **Deployment 是正確的，請不要修改 Deployment**。

**跟題目19 的關鍵差異**：[題目19](#題目19---ingress-排錯-1) 是「Service、Ingress 都存在，但欄位寫錯」；這題備註直接講明**對應的 Service 根本不存在**——不是改欄位，是要**從零新建一個 Service**，而且新建的 Service 要同時對上兩邊：`name`/`port` 要對到 Ingress 的 `backend.service` 設定，`selector`/`targetPort` 要對到 Deployment 實際的 Pod 標籤跟 `containerPort`。這題沒有給 Service 的清單檔案可以參考修改，得自己從 Deployment 跟 Ingress 兩份資訊反推出 Service 該長什麼樣子。

**相關資源**：

- [CKAD/20-deployment.yaml](CKAD/20-deployment.yaml)——模擬考場既有、**正確**的 Deployment（`kk-deployment`，`app: kk-web`、`image: vicuu/nginx:hello81`、`containerPort: 81`），只供參考、不要修改
- [CKAD/20-ingress.yaml](CKAD/20-ingress.yaml)——模擬考場既有的 Ingress（`ingress-kk-ingress`，`host: kk.example.com`、`path: /hello`），語法本身沒錯，但指到的 `backend.service.name: nginxsvc-kk` 在 cluster 上不存在
- [CKAD/20-service.yaml](CKAD/20-service.yaml)——**這題唯一該新增的物件**，從 Deployment/Ingress 兩邊反推出來的 Service（`nginxsvc-kk`）

> 這三份 yaml 目前**只是先寫好**，還沒在本機 minikube 套用驗證（使用者要求先不要執行 `kubectl apply`）。

**解法指令**（尚未執行，供之後練習/驗證參考）：

```bash
kubectl config use-context k8s

# 1. 先看目前 namespace 裡實際有哪些資源——這一步就會發現只有 deploy 跟 ingress，沒有 svc
kubectl get deploy,svc,ingress -n ingress-kk

# 2. 查 Ingress 的 backend 設定，抓出它期待的 Service 名稱／port
kubectl get ingress ingress-kk-ingress -n ingress-kk -o yaml
# 或用 describe，Backends 那欄會直接顯示 <error: endpoints "nginxsvc-kk" not found>，
# 這行錯誤訊息本身就把「該建立哪個名字的 Service」講得很清楚
kubectl describe ingress ingress-kk-ingress -n ingress-kk

# 3. 查 Deployment 的 Pod 標籤／containerPort，決定新 Service 的 selector／targetPort
kubectl get deploy kk-deployment -n ingress-kk -o yaml | grep -A2 "labels:\|containerPort"

# 4. 用查到的資訊建立 Service（名稱、port 對 Ingress；selector、targetPort 對 Deployment）
kubectl apply -f CKAD/20-service.yaml
# 或用指令式，直接從 Deployment 產生對應的 Service：
kubectl expose deployment kk-deployment -n ingress-kk --name=nginxsvc-kk --port=80 --target-port=81
```

`CKAD/20-service.yaml` 關鍵欄位：

```yaml
metadata:
  name: nginxsvc-kk      # 對到 Ingress 的 backend.service.name
spec:
  selector:
    app: kk-web            # 對到 Deployment 的 Pod 標籤
  ports:
  - protocol: TCP
    port: 80                # 對到 Ingress 的 backend.service.port.number
    targetPort: 81          # 對到 Deployment 的 containerPort（這題 image 監聽在 81，不是 80）
```

**驗證**（等實際套用後再執行）：

```bash
kubectl get svc nginxsvc-kk -n ingress-kk
# 應該看得到這個 Service 了

kubectl get endpoints nginxsvc-kk -n ingress-kk
# 應該列出 Pod 的 <PodIP>:81，不是 <none>

kubectl describe ingress ingress-kk-ingress -n ingress-kk
# Backends 那欄應該顯示健康的 Pod IP，不再是 <error: endpoints "nginxsvc-kk" not found>

# 從 minikube ssh 內部測試完整路徑（記得帶 Host header 跟路徑，這題 Ingress 有指定 host）
minikube ssh -- "curl -H 'Host: kk.example.com' http://$(minikube ip)/hello"
```

**對應考綱 Domain**：

`Services and Networking`（20%）→ `建立與除錯 Service 存取`、`Ingress`（延續 [題目19](#題目19---ingress-排錯-1) 的排錯邏輯，這題把「改錯欄位」升級成「補上完全缺失的物件」）

**易錯點／踩坑筆記**：

- **`kubectl describe ingress` 在 Service 不存在時，錯誤訊息會直接把答案寫出來**：`Backends` 那欄會顯示 `<error: endpoints "nginxsvc-kk" not found>`，這行訊息已經明講「我要找一個叫 `nginxsvc-kk` 的 Service（透過它的 Endpoints）但找不到」——遇到 Ingress 打不通，`kubectl describe ingress` 幾乎都該是第一個下的指令，很多時候答案已經直接寫在 `Backends`／`Events` 欄位裡，不用自己憑空猜
- **新建的 Service 要同時滿足兩份「契約」**：一份是 Ingress 對它的期待（`name` 要對到 `backend.service.name`、`port.number` 要對到 `backend.service.port.number`），另一份是 Deployment 對它的期待（`selector` 要對到 Pod 的 `labels`、`targetPort` 要對到 `containerPort`）——**Service 是中間的橋樑，兩邊都要對得上，只對一邊、另一邊沒對到，Service 建立成功了但還是不會通**（例如 selector 對了但 `name` 沒對到 Ingress 要的名字，Ingress 一樣抓不到這個 Service）
- 這題沒有任何一份現成的「錯誤的 Service yaml」可以拿來改，練習/考試時容易因為「找不到可以修的東西」而卡住——**這種情況正確的心態是「這題要新建，不是修改」**，跟[題目19](#題目19---ingress-排錯-1)那種「三份都在，改欄位」的排錯型態不一樣，讀題時第一件事是先 `kubectl get deploy,svc,ingress` 看清楚**現場實際有哪些物件**，不要預設三種資源都一定存在
- `kubectl expose deployment` 是這題除了手寫 yaml 之外更快的做法，因為它會**直接讀 Deployment 的 `spec.selector` 當作新 Service 的 selector**，不用自己再手動查一次 Pod 標籤——但 `--name`／`--port`／`--target-port` 還是要自己對照 Ingress 的要求手動帶，指令不會幫你自動猜這些值
- **`targetPort` 又是一個要對照 image 實際監聽 port 的例子**：這題 Deployment 用的是 `vicuu/nginx:hello81`（[題目17](#題目17---更新-deployment-並暴露-service)/[題目19](#題目19---ingress-排錯-1)都出現過的自訂 image，真的監聽在 81），新建的 Service `targetPort` 要填 `81`，不是看到 Ingress/Service 的 `port: 80` 就直覺填成 `80`——**`port`（Ingress／Service 對外用的號碼）不等於 `targetPort`（container 實際監聽的號碼），這題剛好又是兩個數字不一樣的設計**
- 這題的 Ingress 規則有指定 `host: kk.example.com`（不像[題目19](#題目19---ingress-排錯-1)只用 `path` 導流），驗證時 `curl` 一定要帶 `-H "Host: kk.example.com"`，不然 Ingress Controller 會找不到符合的規則、回應 `404 default backend`——這也是「Service 修好了、Ingress Controller 也在跑，但 curl 還是不通」時容易漏掉的一步：先確認 Ingress 規則有沒有限定 `host`，有的話測試時一定要帶對應的 `Host` header
- 跟[題目19](#題目19---ingress-排錯-1)合起來看，Ingress 排錯的核心邏輯其實只有一個：**Ingress → Service → Pod 這條鏈，任何一環「名字對不上」或「這個東西根本不存在」都會斷鏈**，差別只在斷在哪一環（題目19 是 Service selector 內部對不到 Pod；這題是 Ingress 要的 Service 整個不存在）——排查時養成「從 Ingress 往下查到 Service、再往下查到 Pod，每一步都用 `kubectl get`/`describe` 實際確認存不存在、對不對得上」的習慣，比憑印象猜更可靠

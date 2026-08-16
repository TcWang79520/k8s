# CKAD 考古題練習記錄

本文件記錄「CKAD 20 題考古題」教材的練習過程，與 `Record.md`（原教學系列逐日筆記）分開記錄。目前進度：

- [公用知識](#公用知識)
- [題目1 - CronJob 手動觸發 Job](#題目1---cronjob-手動觸發-job)
- [題目2 - CronJob 建立（不需手動觸發）](#題目2---cronjob-建立不需手動觸發)
- [題目3 - 用 Dockerfile 建置並匯出 OCI 格式 image](#題目3---用-dockerfile-建置並匯出-oci-格式-image)

## 公用知識

- `kubectl config get-contexts`：列出目前 kubeconfig 裡所有可用的 context
- `kubectl config use-context k8s`：切換到指定 context（範例用 `k8s`）
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

# CKAD 考古題練習記錄

本文件記錄「CKAD 20 題考古題」教材的練習過程，與 `Record.md`（原教學系列逐日筆記）分開記錄。目前進度：

- [公用知識](#公用知識)
- [題目1 - CronJob 手動觸發 Job](#題目1---cronjob-手動觸發-job)
- [題目2 - CronJob 建立（不需手動觸發）](#題目2---cronjob-建立不需手動觸發)

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

# CKAD 模擬測驗記錄（Exam A）

本文件記錄 CKAD 模擬測驗（Exam A）中寫過的題目與解法，與 `Exam-2.md`（KodeKloud Exam 2）、`../CKAD-Prepare.md`（20 題考古題）、`../Record.md`（原教學系列逐日筆記）分開記錄。

- [Q1 - 建立 Job template（completions / parallelism / Pod labels）](#q1---建立-job-templatecompletions--parallelism--pod-labels)
- [Q2 - 建立 CronJob（每 30 分鐘列出容器內程序）](#q2---建立-cronjob每-30-分鐘列出容器內程序)
- [Q3 - NodePort / ClusterIP Service 與 NetworkPolicy（三層式應用）](#q3---nodeport--clusterip-service-與-networkpolicy三層式應用)
- [Q4 - 為 Deployment 加上 InitContainer（共用 emptyDir 寫入 index.html）](#q4---為-deployment-加上-initcontainer共用-emptydir-寫入-indexhtml)
- [Q5 - Deployment 滾動更新策略、rollout history 與 rollback](#q5---deployment-滾動更新策略rollout-history-與-rollback)

## Q1 - 建立 Job template（completions / parallelism / Pod labels）

**題目**：

Create a Job template at `/course/3/job.yaml` in Namespace `neptune`:

- Name `neb-new-job`, container name `neb-new-job-container`
- Image `busybox:1`, command `sleep 2 && echo done`
- 3 completions in total, 2 running in parallel
- Pods are labelled `id: awesome-job`

**解法**：

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: neb-new-job
  namespace: neptune
spec:
  completions: 3
  parallelism: 2
  template:
    metadata:
      labels:
        id: awesome-job
    spec:
      containers:
      - name: neb-new-job-container
        image: busybox:1
        command: ["/bin/sh", "-c", "sleep 2 && echo done"]
      restartPolicy: Never
```

- 題目要求檔案放在 `/course/3/job.yaml`，可先用 `kubectl create job neb-new-job --image=busybox:1 -n neptune --dry-run=client -o yaml > /course/3/job.yaml` 產生骨架，再補上 `completions`、`parallelism`、Pod labels 與 command。
- `completions: 3` 是總共要成功完成 3 個 Pod；`parallelism: 2` 是同時最多跑 2 個。
- `id: awesome-job` 這個 label 要寫在 `spec.template.metadata.labels`（Pod 上），不是 Job 的 `metadata.labels`。
- `sleep 2 && echo done` 含有 shell 運算子 `&&`，必須包在 `/bin/sh -c` 裡執行，直接寫成 `command: ["sleep", "2", "&&", "echo", "done"]` 會失敗。
- `restartPolicy` 必須是 `Never`（或 `OnFailure`），Job 的 Pod template 不接受預設的 `Always`。

## Q2 - 建立 CronJob（每 30 分鐘列出容器內程序）

**題目**：

In the `ckad-job` namespace, create a cronjob named `simple-python-job` to run every 30 minutes to list all the running processes inside a container that used `python` image（the command needs to be run in a shell）。

> NOTE：In Unix-based operating systems, `ps -eaf` can be used to list all the running processes.

**解法**：

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: simple-python-job
  namespace: ckad-job
spec:
  schedule: "*/30 * * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: simple-python-job
            image: python
            command: ["/bin/sh", "-c"]
            args: ["ps -eaf"]
          restartPolicy: OnFailure
```

- 可用 `kubectl create cronjob simple-python-job --image=python --schedule="*/30 * * * *" -n ckad-job --dry-run=client -o yaml` 產生骨架，再補上 `command` / `args`。
- CronJob 的巢狀層級比 Job 多兩層：`spec.jobTemplate.spec.template.spec`，`restartPolicy` 要放在最內層的 Pod spec（與 `containers` 同層）。
- cron 格式為「分 時 日 月 星期」，每 30 分鐘是 `*/30 * * * *`；注意不是 `0 */30 * * *`（那會變成每 30 小時，且不合法）。
- 題目要求「command needs to be run in a shell」，所以用 `/bin/sh -c` 包住 `ps -eaf`。

## Q3 - NodePort / ClusterIP Service 與 NetworkPolicy（三層式應用）

**題目**：

We have already deployed an application that consists of frontend, backend, and database pods in the `app-ckad` namespace. Inspect them.

Your task is to create：

- A service `frontend-ckad-svcn` to expose the frontend pods outside the cluster on port `31100`.
- A service `backend-ckad-svcn` to make backend pods to be accessible within the cluster.
- A policy `database-ckad-netpol` to limit access to database pods only to backend pods.

**先觀察現況**（selector 與 targetPort 都要對齊實際的 Pod）：

```bash
kubectl get pods -n app-ckad --show-labels
kubectl describe pod <frontend-pod> -n app-ckad   # 看容器實際監聽的 Port
```

**解法**：

```yaml
apiVersion: v1
kind: Service
metadata:
  name: frontend-ckad-svcn
  namespace: app-ckad
spec:
  type: NodePort
  selector:
    app: frontend   # 需符合 frontend Pod 實際標籤
  ports:
  - protocol: TCP
    port: 80
    targetPort: 80  # 需符合 frontend 容器實際監聽 Port
    nodePort: 31100
---
apiVersion: v1
kind: Service
metadata:
  name: backend-ckad-svcn
  namespace: app-ckad
spec:
  type: ClusterIP   # 預設即為 ClusterIP，亦可明確宣告
  selector:
    app: backend    # 需符合 backend Pod 實際標籤
  ports:
  - protocol: TCP
    port: 80
    targetPort: 80  # 需符合 backend 容器實際監聽 Port
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: database-ckad-netpol
  namespace: app-ckad
spec:
  podSelector:
    matchLabels:
      app: database   # 目標：套用到 database Pods（依實際 Label 調整）
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: backend # 來源：僅允許 backend Pods 進入（依實際 Label 調整）
```

- 「expose outside the cluster on port 31100」＝ `type: NodePort` 且 `nodePort: 31100`（NodePort 預設範圍 30000–32767）；「accessible within the cluster」＝ `ClusterIP`。
- 三個資源的 `selector` / `matchLabels` 都不能照抄，務必先用 `--show-labels` 確認實際 Pod label（可能是 `app=frontend`，也可能是 `role=`、`tier=` 之類）。
- NetworkPolicy 的 `podSelector` 是「這條規則套用在誰身上」（database），`ingress.from.podSelector` 才是「允許誰進來」（backend），兩者不要寫反。
- 只寫 `policyTypes: [Ingress]` 時不影響 egress；一旦 database Pod 被任何 Ingress policy 選中，未列在 `from` 的來源就會全部被擋。
- `from` 底下的 `- podSelector:` 與 `- namespaceSelector:` 若寫成同一個 list item（同一個 `-`）是 AND，分成兩個 `-` 是 OR，這是常見扣分點。本題同 namespace 內，只需 `podSelector`。

## Q4 - 為 Deployment 加上 InitContainer（共用 emptyDir 寫入 index.html）

**題目**（`ssh ckad5601`）：

The Deployment YAML at `/course/17/test-init-container.yaml` spins up a single nginx Pod serving files from an empty mounted volume. Add an InitContainer to it：

- Name `init-con`, image `busybox:1`
- Mounts the same volume as the nginx container
- Writes `check this out!` into `index.html` at the root of that volume
- Test with `curl`.

**解法**：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: test-init-container
spec:
  replicas: 1
  selector:
    matchLabels:
      app: test-init-container
  template:
    metadata:
      labels:
        app: test-init-container
    spec:
      # --- 新增 initContainers 區段 ---
      initContainers:
      - name: init-con
        image: busybox:1
        command:
        - /bin/sh
        - -c
        - "echo 'check this out!' > /work-dir/index.html"
        volumeMounts:
        - name: web-content           # 需與 nginx 容器及 volumes 的名稱完全相同
          mountPath: /work-dir        # 掛載到 init-con 的根路徑或任意工作目錄
      # -------------------------------
      containers:
      - name: nginx
        image: nginx
        volumeMounts:
        - name: web-content
          mountPath: /usr/share/nginx/html
      volumes:
      - name: web-content
        emptyDir: {}
```

**驗證**：

```bash
kubectl apply -f /course/17/test-init-container.yaml
kubectl get pod -o wide        # 取得 Pod IP，確認 Init:0/1 → Running
curl <pod-ip>                  # 應輸出 check this out!
```

- `initContainers` 與 `containers` 同層（都在 `spec.template.spec` 底下），不要縮排到 `containers` 裡面。
- 兩個容器的 `volumeMounts.name` 必須是同一個 volume 名稱（這裡是 `web-content`），但 `mountPath` 可以各自不同——init 容器掛在 `/work-dir`，nginx 掛在 `/usr/share/nginx/html`，寫進去的 `index.html` 就會出現在 nginx 的 web root。
- 題目說「at the root of that volume」指的是 volume 掛載點的根目錄，所以路徑是 `/work-dir/index.html`，不是再往下開子目錄。
- InitContainer 必須跑完並成功結束（exit 0）主容器才會啟動；如果卡在 `Init:0/1` 或 `Init:Error`，用 `kubectl logs <pod> -c init-con` 看原因。
- 原檔案裡 volume 名稱與 nginx 的 mountPath 要照實際檔案為準，別直接套用此處的示例名稱。

## Q5 - Deployment 滾動更新策略、rollout history 與 rollback

**題目**：

Create a new deployment called `ocean-apd` in the `default` namespace using the image `kodekloud/webapp-color:v1`.

Use the following specs for the deployment：

1. Replica count should be 2.
2. Set the Max Unavailable to 45% and Max Surge to 55%.
3. Create the deployment and ensure all the pods are ready.
4. After successful deployment, upgrade the deployment image to `kodekloud/webapp-color:v2` and inspect the deployment rollout status.
5. Check the rolling history of the deployment and on the `student-node`, save the current revision count number to the `/opt/ocean-revision-count.txt` file.
6. Finally, perform a rollback and revert the deployment image to the older version.

**解法（YAML）**：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ocean-apd
  namespace: default
  labels:
    app: ocean-apd
spec:
  replicas: 2
  selector:
    matchLabels:
      app: ocean-apd
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 55%
      maxUnavailable: 45%
  template:
    metadata:
      labels:
        app: ocean-apd
    spec:
      containers:
      - name: ocean-apd
        image: kodekloud/webapp-color:v1
        ports:
        - containerPort: 80
```

**Step 1–3：建立 Deployment 並確認 Pod Ready**

```bash
kubectl apply -f ocean-apd.yaml
kubectl rollout status deployment/ocean-apd
```

**Step 4：升級映像檔至 v2 並檢查 rollout 狀態**

```bash
# 更新容器映像檔為 v2（ocean-apd 是「容器名稱」，不是 deployment 名稱）
kubectl set image deployment/ocean-apd ocean-apd=kodekloud/webapp-color:v2

# 檢查滾動更新狀態
kubectl rollout status deployment/ocean-apd
```

**Step 5：檢查 rollout 歷史紀錄並寫入 revision 數字**

```bash
kubectl rollout history deployment/ocean-apd
```

輸出會看到類似：

```
REVISION  CHANGE-CAUSE
1         <none>
2         <none>
```

此時當前的 revision 編號為 `2`，依題目要求存檔（這步要在 `student-node` 上做，不是在 cluster node 內）：

```bash
echo "2" > /opt/ocean-revision-count.txt
```

**Step 6：執行 rollback 回退到前一個版本**

```bash
# 回滾到前一版本 (v1)
kubectl rollout undo deployment/ocean-apd

# 確認回滾完成
kubectl rollout status deployment/ocean-apd

# 驗證目前運行的映像檔是否已回到 v1
kubectl get deployment ocean-apd -o jsonpath='{.spec.template.spec.containers[0].image}'
```

- `strategy` 與 `replicas`、`selector`、`template` 同層（都在 `spec` 底下）；YAML 的 key 順序不影響效力，寫在 `template` 前或後都可以，但放前面比較好讀。
- `maxSurge` / `maxUnavailable` 寫成百分比字串時不用加引號也可以，但兩者的 `type` 必須是 `RollingUpdate` 才有意義（`Recreate` 不接受這兩個欄位）。
- `kubectl set image deployment/<deploy> <container>=<image>` 中間那個名稱是**容器名稱**；本題剛好 deployment 與 container 同名叫 `ocean-apd`，容易誤會。名稱打錯時 kubectl 不會報錯，只是什麼都沒更新，記得用 `rollout status` 或 `get deploy -o jsonpath` 驗證。
- 第 5 步問的是「revision count」＝ 目前 history 裡最大的 revision 編號（升級完是 2），先存檔再做第 6 步；順序反過來會多出 revision 3，數字就不對了。
- `kubectl rollout undo` 不會把 revision 編號往回減，而是新增一個 revision 3（內容等同 v1）。若要回到指定版本可用 `--to-revision=1`。

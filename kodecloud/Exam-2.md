# KodeKloud 模擬測驗記錄（Exam 2）

本文件記錄在 KodeKloud 做 CKAD 模擬測驗（Exam 2）時，寫過的題目與解法，與 `../CKAD-Prepare.md`（20 題考古題）、`../Record.md`（原教學系列逐日筆記）分開記錄。目前留存的題號並非連續，是模擬測驗中實際有作答並留下記錄的題目：

- [Q1 - 建立多容器 Pod（emptyDir 共享 volume）](#q1---建立多容器-pod共享-emptydir-volume)
- [Q2 - 建立多容器 Pod（環境變數、印訊息）](#q2---建立多容器-pod環境變數印訊息)
- [Q3 - 建立 Job（alpine 執行 top）](#q3---建立-jobalpine-執行-top)
- [Q4 - 建立 Pod 並設定自訂 Annotation](#q4---建立-pod-並設定自訂-annotation)
- [Q6 - Deployment 滾動更新策略與 rollout undo](#q6---deployment-滾動更新策略與-rollout-undo)
- [Q10 - Service（NodePort/ClusterIP）與 NetworkPolicy](#q10---servicenodeportclusterip-與-networkpolicy)
- [Q12 - Deployment + ClusterIP Service + NetworkPolicy](#q12---deployment--clusterip-service--networkpolicy)
- [Q13 - 修改既有 Pod 的 SecurityContext（runAsUser + capabilities）](#q13---修改既有-pod-的-securitycontextrunasuser--capabilities)
- [Q16 - Pod 的 memory requests/limits 設定](#q16---pod-的-memory-requestslimits-設定)

## Q1 - 建立多容器 Pod（共享 emptyDir volume）

**題目**：

In the `ckad-multi-containers` namespace, create a `ckad-neighbor-pod` pod that matches the following requirements:

- Pod has an `emptyDir` volume named `my-vol`.
- The first container named `main-container`, runs `nginx:1.16` image. This container mounts the `my-vol` volume at `/usr/share/nginx/html` path.
- The second container is a co-located container named `neighbor-container`, and runs the `busybox:1.28` image. This container mounts the volume `my-vol` at `/var/log` path. Every 5 seconds, this container should write the current date along with greeting message `Hi I am from neighbor container` to `index.html` in the `my-vol` volume.

**解法**：

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: ckad-neighbor-pod
  namespace: ckad-multi-containers
spec:
  containers:
  - image: nginx:1.16
    name: main-container
    volumeMounts:
    - mountPath: /usr/share/nginx/html
      name: my-vol
  - image: busybox:1.28
    name: neighbor-container
    command: ["/bin/sh","-c"]
    args: ["while true; do echo \"$(date) Hi I am from neighbor container\" > /var/log/index.html; sleep 5; done"]
    volumeMounts:
    - mountPath: /var/log
      name: my-vol
  volumes:
  - name: my-vol
    emptyDir: {}
```

## Q2 - 建立多容器 Pod（環境變數、印訊息）

**題目**：

In the `ckad-multi-containers` namespace, create pod named `dos-containers-pod` which has 2 containers matching the below requirements:

- The first container named `alpha` runs the `nginx:1.17` image and has the `ROLE=SERVER` env variable configured.
- The second container named `beta`, runs `busybox:1.28` image. This container will print message `Hello multi-containers`（command needs to be run in shell）.

> NOTE：all containers should be in a running state to pass the validation.

**解法**：

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: dos-containers-pod
  namespace: ckad-multi-containers
spec:
  containers:
  - name: alpha
    image: nginx:1.17
    env:
    - name: ROLE
      value: "SERVER"
  - name: beta
    image: busybox:1.28
    command: ["/bin/sh","-c"]
    args: ["echo \"Hello multi-containers\"; sleep 7200"]
```

- `beta` container 印完訊息後接著 `sleep 7200`，是為了滿足題目「all containers should be in a running state」的要求——若只 `echo` 完就結束，container 會馬上進入 `Completed` 狀態，不算 running。

## Q3 - 建立 Job（alpine 執行 top）

**題目**：

In the `ckad-job` namespace, create a job called `alpine-job` that runs `top` command inside the container; use `alpine` image for this task.

**解法**：

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: alpine-job
  namespace: ckad-job
spec:
  template:
    spec:
      containers:
      - name: alpine-job
        image: alpine
        command: ["/bin/sh", "-c", "top"]
      restartPolicy: Never
  backoffLimit: 1
```

## Q4 - 建立 Pod 並設定自訂 Annotation

**題目**：

In the `ckad-pod-design` namespace, start a `ckad-redis-wiipwlznjy` pod running the `redis` image; the container should be named `redis-custom-annotation`.

Configure a custom annotation to that pod as below：

```
KKE: https://engineer.kodekloud.com/
```

**解法**：

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: ckad-redis-wiipwlznjy
  namespace: ckad-pod-design
  labels:
    run: ckad-redis-wiipwlznjy
  annotations:
    KKE: https://engineer.kodekloud.com/
spec:
  containers:
  - image: redis
    name: redis-custom-annotation
  dnsPolicy: ClusterFirst
  restartPolicy: Always
```

## Q6 - Deployment 滾動更新策略與 rollout undo

**題目**：

Create a new deployment called `ocean-apd` in the default namespace using the image `kodekloud/webapp-color:v1`. Use the following specs for the deployment：

1. Replica count should be 2.
2. Set the Max Unavailable to 45% and Max Surge to 55%.
3. Create the deployment and ensure all the pods are ready.
4. After successful deployment, upgrade the deployment image to `kodekloud/webapp-color:v2` and inspect the deployment rollout status.
5. Check the rolling history of the deployment and on the student-node, save the current revision count number to the `/opt/ocean-revision-count.txt` file.
6. Finally, perform a rollback and revert the deployment image to the older version.

**解法**：

`ocean-apd.yaml`：

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

Step 1~3：

```bash
kubectl apply -f ocean-apd.yaml
kubectl rollout status deployment/ocean-apd
```

Step 4（升級 image、確認 rollout 進度）：

```bash
kubectl set image deployment/ocean-apd ocean-apd=kodekloud/webapp-color:v2
kubectl rollout status deployment/ocean-apd
```

Step 5（查 rollout history，把目前 revision 數寫入檔案）：

```bash
kubectl rollout history deployment/ocean-apd
echo "2" > /opt/ocean-revision-count.txt
```

Step 6（回滾到舊版本 image）：

```bash
kubectl rollout undo deployment/ocean-apd
kubectl rollout status deployment/ocean-apd
```

## Q10 - Service（NodePort/ClusterIP）與 NetworkPolicy

**題目**：

We have already deployed an application that consists of frontend, backend, and database pods in the `app-ckad` namespace. Inspect them.

Your task is to create：

- A service `frontend-ckad-svcn` to expose the frontend pods outside the cluster on port `31100`.
- A service `backend-ckad-svcn` to make backend pods to be accessible within the cluster.
- A policy `database-ckad-netpol` to limit access to database pods only to backend pods.

**解法**：

`front-service.yaml`：

```yaml
apiVersion: v1
kind: Service
metadata:
  name: frontend-ckad-svcn
  namespace: app-ckad
spec:
  type: NodePort
  selector:
    app: frontend
  ports:
    - protocol: TCP
      port: 80
      targetPort: 80
      nodePort: 31100
```

`back-service.yaml`：

```yaml
apiVersion: v1
kind: Service
metadata:
  name: backend-ckad-svcn
  namespace: app-ckad
spec:
  selector:
    app: backend
  ports:
    - protocol: TCP
      port: 80
      targetPort: 80
```

`networkpolicy.yaml`：

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: database-ckad-netpol
  namespace: app-ckad
spec:
  podSelector:
    matchLabels:
      app: database
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: backend
```

- `backend-ckad-svcn` 沒有指定 `type`，預設為 `ClusterIP`，符合題目「make backend pods to be accessible within the cluster」（只要叢集內部能存取，不用曝露到外部）的要求。

## Q12 - Deployment + ClusterIP Service + NetworkPolicy

**題目**：

Please use the namespace `nginx-deployment` for the following scenario.

Create a deployment with name `nginx-ckad11` using `nginx` image with 2 replicas. Also expose the deployment via `ClusterIP` service .i.e. `nginx-ckad11-service` on port 80. Use the label `app=nginx-ckad` for both resources.

Now, create a NetworkPolicy .i.e. `ckad-allow` so that only pods with label criteria `criteria: allow` can access the deployment on port 80 and apply it.

**解法**：

```bash
kubectl apply -f - <<eof
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-ckad11
  namespace: nginx-deployment
spec:
  replicas: 2
  selector:
    matchLabels:
      app: nginx-ckad
  template:
    metadata:
      labels:
        app: nginx-ckad
    spec:
      containers:
        - name: nginx
          image: nginx
          ports:
            - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: nginx-ckad11-service
  namespace: nginx-deployment
spec:
  selector:
    app: nginx-ckad
  ports:
    - name: http
      port: 80
      targetPort: 80
  type: ClusterIP
eof
```

> 待補：`ckad-allow` 這個 NetworkPolicy 當時沒有留下解法紀錄，之後補測驗時可以再補上（依 `criteria: allow` 的 `podSelector` 限制 `Ingress` 存取）。

## Q13 - 修改既有 Pod 的 SecurityContext（runAsUser + capabilities）

**題目**：

Update pod `ckad06-cap-aecs` in the namespace `ckad05-securityctx-aecs` to run as root user and with the `SYS_TIME` and `NET_ADMIN` capabilities.

> Note：Make only the necessary changes. Do not modify the name of the pod.

**解法**：

沿用 [`CKAD-Prepare.md`「修改既有物件：優先用『匯出 → 編輯 → apply』」](../CKAD-Prepare.md#修改既有物件優先用匯出--編輯--apply少用-kubectl-edit) 的做法，先匯出現有 Pod 確認目前的 `capabilities` 設定：

```bash
kubectl config use-context cluster1

kubectl get -n ckad05-securityctx-aecs pod ckad06-cap-aecs -o yaml | egrep -i -A3 capabilities:
#       capabilities:
#         add:
#         - SYS_TIME
#     terminationMessagePath: /dev/termination-log

kubectl get -n ckad05-securityctx-aecs pod ckad06-cap-aecs -o yaml > pod-capabilities.yaml
vim pod-capabilities.yaml
```

編輯後的 `pod-capabilities.yaml`（補上 `NET_ADMIN`）：

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: ckad06-cap-aecs
  namespace: ckad05-securityctx-aecs
spec:
  containers:
  - command:
    - sleep
    - "4800"
    image: ubuntu
    name: ubuntu-sleeper
    securityContext:
      capabilities:
        add: ["SYS_TIME", "NET_ADMIN"]
```

> 待確認：原始筆記的 yaml 只補了 `capabilities`，沒看到明確設定 `runAsUser: 0`（`ubuntu` image 預設就是用 root 執行，這裡不確定當時是靠 image 預設行為過關、還是筆記漏記了 `runAsUser` 欄位）——之後有機會重考這題時可以順便確認清楚。

Pod 的 container 欄位不可變更，需用 `replace --force`（先刪除、再依新 yaml 建立）套用變更並驗證：

```bash
kubectl replace -f pod-capabilities.yaml --force
# pod "ckad06-cap-aecs" deleted
# pod/ckad06-cap-aecs replaced

kubectl get -n ckad05-securityctx-aecs pod ckad06-cap-aecs -o yaml | egrep -i -A3 capabilities:
#       capabilities:
#         add:
#         - SYS_TIME
#         - NET_ADMIN
```

## Q16 - Pod 的 memory requests/limits 設定

**題目**：

Create a Kubernetes Pod named `ckad15-memory`, with a container named `ckad15-memory` running the `polinux/stress` image, and configure it to use the following specifications：

- Command: `stress`
- Arguments: `["--vm", "1", "--vm-bytes", "10M", "--vm-hang", "1"]`
- Requested memory: `10Mi`
- Memory limit: `10Mi`

**解法**：

```bash
kubectl config use-context cluster2

cat << EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: ckad15-memory
spec:
  containers:
  - name: ckad15-memory
    image: polinux/stress
    resources:
      requests:
        memory: "10Mi"
      limits:
        memory: "10Mi"
    command: ["stress"]
    args: ["--vm", "1", "--vm-bytes", "10M", "--vm-hang", "1"]
EOF
# pod/ckad15-memory created
```

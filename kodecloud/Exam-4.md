# KodeKloud 模擬測驗記錄（Exam 4）

本文件記錄在 KodeKloud 做 CKAD 模擬測驗（Exam 4）時，寫過的題目與解法，與 `Exam-2.md`（Exam 2）、`Exam-ckad-A.md`（Exam A）、`../CKAD-Prepare.md`（20 題考古題）、`../Record.md`（原教學系列逐日筆記）分開記錄。

- [Q1 - 建立 privileged 模式的 Pod](#q1---建立-privileged-模式的-pod)
- [Q2 - 建立 hostPath 型別的 PersistentVolume](#q2---建立-hostpath-型別的-persistentvolume)

## Q1 - 建立 privileged 模式的 Pod

**題目**：

In the `ckad-pod-design` namespace, create a pod named `privileged-pod` that runs the `nginx:1.17` image, and the container should be run in privileged mode.

**解法**：

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: privileged-pod
  namespace: ckad-pod-design
spec:
  containers:
    - name: nginx
      image: nginx:1.17
      securityContext:
        privileged: true
```

- `privileged: true` 只能寫在 **container 層** 的 `securityContext`（`spec.containers[].securityContext`），Pod 層的 `spec.securityContext` 沒有這個欄位，寫上去會被 API server 拒絕。
- 題目沒指定 container 名稱時可自行命名（這裡取 `nginx`）；若用 `kubectl run privileged-pod --image=nginx:1.17` 產生骨架，container 名稱會與 Pod 同名。
- 快速產檔：`kubectl run privileged-pod --image=nginx:1.17 -n ckad-pod-design --dry-run=client -o yaml > pod.yaml`，再補上 `securityContext`。
- 相關但不同的欄位：`runAsUser`（指定 UID）、`capabilities`（加減個別權限）可寫在 container 層；`fsGroup`、`runAsGroup` 常寫在 Pod 層。`privileged: true` 等同給予容器近乎 host root 的權限，比 `capabilities.add` 範圍大得多。

## Q2 - 建立 hostPath 型別的 PersistentVolume

**題目**：

Create a persistent volume called `red-pv-ckad03-str` of `type: hostPath` and `capacity: 100Mi`.

**解法**：

```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: red-pv-ckad03-str
spec:
  capacity:
    storage: 100Mi
  accessModes:
    - ReadWriteOnce
  hostPath:
    path: /tmp/data
```

**驗證**：

```bash
kubectl apply -f red-pv.yaml
kubectl get pv red-pv-ckad03-str   # STATUS 應為 Available
```

- PV 是 **cluster-scoped**（叢集層級）資源，沒有 `namespace` 欄位，寫上去會被拒絕。
- `capacity.storage` 與 `accessModes` 是必填；題目只給容量時，`accessModes` 補 `ReadWriteOnce` 即可（hostPath 本來就只能單一節點使用）。
- `hostPath.path` 題目沒指定時可自訂（如 `/tmp/data`），但一定要寫，否則 PV 建立失敗。
- 沒有明寫 `persistentVolumeReclaimPolicy` 時預設是 `Retain`；沒寫 `storageClassName` 則為空字串，只有同樣沒指定 storageClass 的 PVC 能綁上來。
- PV 沒有 `kubectl create pv` 的快速指令，只能手寫 YAML；考場可從官方文件 Persistent Volumes 頁面複製範本再改。

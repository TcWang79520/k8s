# KodeKloud 模擬測驗記錄（Exam 1）

本文件記錄在 KodeKloud 做 CKAD 模擬測驗（Exam 1）時，**當下沒有把握、事後需要回頭補觀念**的題目，與 `../CKAD-Prepare.md`（20 題考古題）、`../Record.md`（原教學系列逐日筆記）分開記錄。留存的題號並非連續，只收錄實際卡關並留下記錄的題目：

- [Q9 - 建立 deny-all 的 NetworkPolicy（拒絕所有進出流量）](#q9---建立-deny-all-的-networkpolicy拒絕所有進出流量)
- [Q10 - 讓叢集內 Pod 連到叢集外的服務（手動建立 EndpointSlice）](#q10---讓叢集內-pod-連到叢集外的服務手動建立-endpointslice)
- [Q12 - 建立 ExternalName Service](#q12---建立-externalname-service)

## Q9 - 建立 deny-all 的 NetworkPolicy（拒絕所有進出流量）

**題目**：

You are requested to create a network policy named `deny-all-svcn` that denies all incoming and outgoing traffic to `ckad12-svcn` namespace.

> Note：The namespace `ckad12-svcn` doesn't exist. Create the namespace before creating the Policy.

**解法**：

namespace 不存在，所以要先建立，否則 NetworkPolicy 會因為找不到 namespace 而套用失敗：

```bash
kubectl create namespace ckad12-svcn
```

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-all-svcn
  namespace: ckad12-svcn
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
```

**重點整理**：

- `podSelector: {}` 是**空的 selector，代表選中該 namespace 底下的所有 Pod**，不是「不選任何 Pod」——這是寫 deny-all 規則的關鍵。
- `policyTypes` 同時列出 `Ingress` 與 `Egress`，且**底下完全不寫 `ingress:`／`egress:` 規則**，等於「沒有任何流量被允許」，達成全部拒絕。只寫 `policyTypes: [Ingress]` 的話，出向流量仍然是通的。
- NetworkPolicy 是 **namespace-scoped**，`metadata.namespace` 要指定到題目要求的 namespace；namespace 不存在時要先 `kubectl create namespace`。
- NetworkPolicy 要真的生效，叢集必須裝有支援 NetworkPolicy 的 CNI（例如 Calico、Cilium）；純 flannel 環境下規則會建得起來但不會擋任何流量。

## Q10 - 讓叢集內 Pod 連到叢集外的服務（手動建立 EndpointSlice）

**題目**：

We have an external webserver running on `student-node` which is exposed at port `9999`.

We have also created a service called `external-webserver-ckad01-svcn` that can connect to our local webserver from within the `cluster3` but, at the moment, it is not working as expected.

Fix the issue so that other pods within `cluster3` can use `external-webserver-ckad01-svcn` service to access the webserver.

> Note：不能砍掉重建既有的 k8s 物件。

**排查**：

Step 1（先確認外部 webserver 本身是活的，排除「服務根本沒起來」）：

```bash
curl student-node:9999
# ...
# <h1>Welcome to nginx!</h1>
# ...
```

Step 2（再確認 Service 的後端有沒有對上）：

```bash
kubectl describe svc external-webserver-ckad01-svcn
# Name:              external-webserver-ckad01-svcn
# Namespace:         default
# ...
# Endpoints:         <none>    ◄── 問題在這：沒有任何後端
```

**問題原因**：

這個 Service 沒有（也不能有）可用的 `selector`——因為真正的 webserver 跑在 `student-node` 這台**叢集外部的主機**上，不是 Pod，沒有任何 Pod label 可以被選到，所以 kube-proxy 找不到後端，`Endpoints` 是 `<none>`，請求自然打不通。

這類「Service 要指向叢集外部位址」的情境，標準做法就是**手動幫這個 Service 建立後端通訊錄**（EndpointSlice / 舊版的 Endpoints），把外部主機的 IP + Port 直接寫進去。

**解法**：

題目不允許刪除既有物件，所以不動 Service，只補上 EndpointSlice：

```bash
export IP_ADDR=$(ifconfig eth0 | grep 'inet ' | awk '{print $2}')

kubectl apply -f - <<EOF
apiVersion: discovery.k8s.io/v1
kind: EndpointSlice
metadata:
  name: external-webserver-ckad01-svcn
  labels:
    kubernetes.io/service-name: external-webserver-ckad01-svcn
addressType: IPv4
ports:
  - protocol: TCP
    port: 9999
endpoints:
  - addresses:
      - $IP_ADDR
EOF
```

驗證（從叢集內開一個臨時 Pod 打這個 Service）：

```bash
kubectl --context cluster3 run --rm -i test-curl-pod \
  --image=curlimages/curl --restart=Never -- curl -m 2 external-webserver-ckad01-svcn
# ...
# <title>Welcome to nginx!</title>
# ...
```

**重點整理**：

- `metadata.labels` 的 `kubernetes.io/service-name` 是**把 EndpointSlice 綁到 Service 的唯一關鍵**，值必須完全等於 Service 名稱；名字打錯就等於沒綁，`Endpoints` 依舊是 `<none>`。
- `ports[].port` 要填**外部服務實際監聽的 port（9999）**，不是 Service 對外宣告的 `port`；Service 的 `targetPort` 也要對到 9999，流量才會被 DNAT 到正確的位置。
- `addresses` 填外部主機的 IP，所以要先用 `ifconfig eth0` 取得 `student-node` 的實體 IP，不能寫 `localhost`／`127.0.0.1`（那會被解讀成 Pod 自己）。
- EndpointSlice 沒有 `namespace` 欄位時會建在 `default`，必須和目標 Service 同一個 namespace 才綁得起來。

**流量路徑圖**：

```
[ 其他 Pod 發送請求 ]
        │
        │  連線目標：http://external-webserver-ckad01-svcn:80
        ▼
┌────────────────────────────────────────────────────────┐
│  Service (虛擬招牌 / VIP)                              │
│  - spec.ports[].port: 80                               │
│  - spec.ports[].targetPort: 9999                       │
└────────────────────────────────────────────────────────┘
        │
        │  kube-proxy 透過 label: kubernetes.io/service-name 找到 Slice
        ▼
┌────────────────────────────────────────────────────────┐
│  EndpointSlice (實際後端通訊錄)                         │
│  - ports[].port: 9999      ◄── 對齊目標實際服務的 Port │
│  - addresses: 10.244.128.46                            │
└────────────────────────────────────────────────────────┘
        │
        │  DNAT 網路位址轉換 (把目標改寫為 10.244.128.46:9999)
        ▼
┌────────────────────────────────────────────────────────┐
│  外部主機 student-node (10.244.128.46)                 │
│                                                        │
│  [ 實體 Webserver ] 監聽在 :9999 ◄── 正確收到封包！     │
└────────────────────────────────────────────────────────┘
```

## Q12 - 建立 ExternalName Service

**題目**：

For this scenario, create a Service called `ckad12-service` that routes traffic to an external IP address.

Please note that service should listen on port `53` and be of type `ExternalName`. Use the external IP address `8.8.8.8`. Create the service in the `default` namespace.

**解法**：

```yaml
apiVersion: v1
kind: Service
metadata:
  name: ckad12-service
  namespace: default
spec:
  type: ExternalName
  externalName: 8.8.8.8
  ports:
    - name: http
      protocol: TCP
      port: 53
      targetPort: 53
```

**重點整理**：

- `ExternalName` 是唯一**不做流量轉發**的 Service 型別：它不會配 ClusterIP、不會有 Endpoints，CoreDNS 只是幫 `ckad12-service.default.svc.cluster.local` 回一筆 **CNAME** 指向 `externalName` 的值。真正的連線是 Pod 自己直接連過去的。
- 也因為不轉發流量，`selector`、`ports`、`targetPort` 對 `ExternalName` 其實**都不會生效**；題目要求「listen on port 53」才把 `ports` 寫上去（考試以通過驗證為準），但要知道它只是宣告用途，不影響行為。
- 嚴格來說 `externalName` 應該填 **DNS 名稱**（例如 `dns.google`），因為 CNAME 的目標必須是網域名稱；填 IP（`8.8.8.8`）在真實環境不一定能正常解析，這題是 KodeKloud 的題目設定要求這樣寫。
- 和 Q10 對照記憶：
  - 要把**外部 IP:Port** 接進叢集、且希望走 Service VIP／kube-proxy → 用 **無 selector 的 Service + 手動 EndpointSlice**（Q10）。
  - 只是要幫外部**網域名稱**在叢集內取一個好記的別名 → 用 **ExternalName**（Q12）。

# 部署 matcher 到 K8s

完整步驟與驗收見 [`specs/020-k8s-deploy/quickstart.md`](../specs/020-k8s-deploy/quickstart.md)。以下為摘要。

## 前提

- `docker`、`kubectl`（context 指向你的叢集）、`gh`（已登入、含 `write:packages`）
- 本機 `.env` 含現用 `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET`；本機測試 `MATCHER_INSECURE_COOKIE=1`

## 流程

# 部署在 namespace `matcher`；節點為 amd64（Apple Silicon 本機必須 --platform linux/amd64）。

```sh
# 1. build（amd64）+ 推映像到 ghcr（公開）
gh auth token | docker login ghcr.io -u timcsy --password-stdin
SHA=$(git rev-parse --short HEAD)
docker buildx build --platform linux/amd64 --provenance=false \
  -t ghcr.io/timcsy/matcher:$SHA -t ghcr.io/timcsy/matcher:latest --push .

# 2. namespace + 灌機密（值來自本機 .env，不入庫）
kubectl apply -f deploy/k8s/namespace.yaml
kubectl create secret generic matcher-secrets -n matcher \
  --from-env-file=.env --dry-run=client -o yaml | kubectl apply -f -

# 3. 部署（先把 deployment.yaml 的 image tag 設成 $SHA）
kubectl apply -f deploy/k8s/pvc.yaml -f deploy/k8s/service.yaml -f deploy/k8s/deployment.yaml
kubectl rollout status deploy/matcher -n matcher --timeout=300s

# 4. 本機存取（沿用現有 OAuth 回呼）
kubectl port-forward -n matcher svc/matcher 8765:8765
#   → http://localhost:8765
```

## 檔案

| 檔 | 用途 |
|---|---|
| `../Dockerfile` | 單一容器映像 |
| `k8s/namespace.yaml` | namespace `matcher` |
| `k8s/pvc.yaml` | `data/` 持久卷（local-path、RWO、1Gi） |
| `k8s/service.yaml` | ClusterIP（供 port-forward） |
| `k8s/deployment.yaml` | 工作負載（Recreate、envFrom secret、掛 PVC、proxy-headers） |
| `k8s/configmap.example.yaml` | 可選：非機密設定分離（預設不需要） |
| `k8s/ingress.example.yaml` | 範例：網域 + TLS（**使用者自理**，預設不套用） |

## 上正式網域（自理）

1. `.env` 改：`SESSION_SECRET` 換真實亂碼、設 `MATCHER_ENV=production`、移除 `MATCHER_INSECURE_COOKIE` → 重灌 Secret。
2. Google OAuth client 加回呼 `https://<你的網域>/auth/callback`。
3. 填 `k8s/ingress.example.yaml` 的 host / TLS 後套用。

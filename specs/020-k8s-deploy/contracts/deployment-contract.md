# 部署契約（020-k8s-deploy）

本 feature 對外的「契約」是：**容器映像介面**、**K8s 資源外形**、**操作指令序列**。以下是驗收時據以檢查的契約面。

## 1. 容器映像契約

- **Image**：`ghcr.io/timcsy/matcher:<git-sha>`（公開、免 imagePullSecret）
- **Entrypoint/CMD**：監聽 `0.0.0.0:8765`，啟動 `matcher.web.app:create_app`（factory）、帶 `--proxy-headers --forwarded-allow-ips="*"`
- **必含執行期能力**：WeasyPrint 可渲染（pango/cairo）、`pdftotext` 可用（poppler）、CJK 字體可用、Authlib OAuth 可用（**httpx 在執行期**）
- **不含**：`data/`、`.env`、`.git`、`tests/`（由 `.dockerignore` 排除）
- **狀態**：無狀態程式碼；所有可變狀態落在掛載的 `/app/data`

## 2. K8s 資源契約

- `Deployment/matcher`：`replicas:1`、`strategy:Recreate`、`envFrom:[secretRef:matcher-secrets]`、`volumeMounts:[{name:data,mountPath:/app/data}]`、`readinessProbe: httpGet /login :8765`
- `Service/matcher`：`ClusterIP`、`8765→8765`
- `PVC/matcher-data`：`local-path`、`RWO`、≥1Gi
- `Secret/matcher-secrets`：執行期環境變數來源（外部以 `--from-env-file=.env` 建立，**不在 repo**）
- `ingress.example.yaml`：僅範例，預設不套用

## 3. 操作指令契約（冪等、可重複）

```sh
# build + push（image 進 registry）
docker build -t ghcr.io/timcsy/matcher:$(git rev-parse --short HEAD) -t ghcr.io/timcsy/matcher:latest .
gh auth token | docker login ghcr.io -u timcsy --password-stdin
docker push ghcr.io/timcsy/matcher:$(git rev-parse --short HEAD)

# 機密（值來自本機 .env，不入庫）
kubectl create secret generic matcher-secrets --from-env-file=.env --dry-run=client -o yaml | kubectl apply -f -

# 部署
kubectl apply -f deploy/k8s/pvc.yaml -f deploy/k8s/service.yaml -f deploy/k8s/deployment.yaml

# 存取（沿用 OAuth 回呼）
kubectl port-forward svc/matcher 8765:8765
# → http://localhost:8765
```

## 4. 驗收契約（對應 spec Success Criteria）

| 檢查 | 對應 SC |
|---|---|
| `kubectl rollout status deploy/matcher` 5 分鐘內 Ready、`curl -sf localhost:8765/login` 200 | SC-001 |
| 真人從 `localhost:8765` Google 登入成功 + 跑一次配對 + 下載 PDF | SC-002 |
| 跑配對 + 建範本 → `kubectl delete pod -l app=matcher` → 重建後資料仍在 | SC-003 |
| `git grep` 與映像層皆無真實機密值 | SC-004 |
| `git diff` 不含 `src/matcher/**` | SC-005 |

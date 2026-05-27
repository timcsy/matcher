# Phase 1 Data Model：部署資源與環境變數契約

本 feature 無新增應用資料模型（沿用既有 audit / match-record / 範本）。以下是**部署層的實體**與**環境變數契約**。

## 部署資源（K8s）

| 資源 | 名稱 | 重點 |
|---|---|---|
| Deployment | `matcher` | `replicas: 1`、`strategy: Recreate`、image `ghcr.io/timcsy/matcher:<sha>`、`envFrom: secretRef matcher-secrets`、掛 PVC 於 `/app/data`、uvicorn `--proxy-headers --forwarded-allow-ips=*`、containerPort 8765、liveness/readiness 探針打 `/login` |
| Service | `matcher` | `ClusterIP`、port 8765 → targetPort 8765（供 port-forward） |
| PersistentVolumeClaim | `matcher-data` | `local-path`、`ReadWriteOnce`、容量（如 1Gi） |
| Secret | `matcher-secrets` | 由 `.env` 灌入（**不入庫**）；提供全部執行期環境變數 |
| ConfigMap（可選） | `matcher-config` | 非機密設定的覆寫處（初版可不用，值已在 .env） |
| Ingress（範例，不啟用） | `matcher`（example） | 網域/TLS 留空待使用者填 |

## 容器映像

- 基底 `python:3.11-slim-bookworm`；WORKDIR `/app`
- apt：`libpango-1.0-0 libpangocairo-1.0-0 libcairo2 poppler-utils fonts-noto-cjk`
- Python 依賴：`uv sync --frozen --no-dev`（**httpx 需為執行期依賴**，見 research R-3）
- 啟動：`uv run uvicorn matcher.web.app:create_app --factory --host 0.0.0.0 --port 8765 --proxy-headers --forwarded-allow-ips="*"`
- `data/` 不入映像（`.dockerignore`），執行期由 PVC 提供

## 環境變數契約（app 實際讀取）

| 變數 | 機密 | 本機 port-forward 值 | 正式網域（使用者自理）|
|---|---|---|---|
| `GOOGLE_CLIENT_ID` | 否（但放 Secret） | 現用值 | 同 |
| `GOOGLE_CLIENT_SECRET` | **是** | 現用值 | 同 |
| `SESSION_SECRET` | **是** | 可用 dev 值（僅警告） | **真實亂碼**（production 強制） |
| `MATCHER_INSECURE_COOKIE` | 否 | `1`（http localhost） | 移除（https） |
| `MATCHER_ENV` | 否 | 不設 | `production`（觸發 secret 防呆） |
| `ALLOWED_EMAIL_DOMAINS` | 否 | 留空或填校網域 | 建議填校網域 |
| `PARTICIPANT_TOKEN_MAX_AGE` | 否 | 預設（180 天） | 視需要 |

> 註：app 的 OAuth 回呼網址由請求 Host 動態推導（非環境變數）；port-forward 下＝`http://localhost:8765/auth/callback`，與現有註冊相符。

## 持久化路徑（落在 PVC `/app/data`）

- `data/matches/<id>.json`：配對紀錄（含 audit）
- `data/templates/<id>/v<N>.yaml` + `meta.json`：自訂範本與擁有者/可見性

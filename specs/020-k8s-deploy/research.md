# Phase 0 Research：K8s 部署

## R-1：映像如何送到叢集

- **Decision**：本機用 docker build → 推到 **ghcr.io/timcsy/matcher**（公開），叢集 pull。
- **Rationale**：探測發現 context `k3s-tew` 的節點 INTERNAL-IP 為 **45.76.49.244（公網 IP）＝遠端 VPS（Ubuntu 24.04 + containerd）**，並非本機叢集，故 `docker save | k3s ctr import` 之類「本機塞映像」不可行。必須走 registry。`gh` token 已具 `write:packages`、repo `timcsy/matcher` 已公開 → ghcr 公開 image 零額外基礎設施、cluster pull 免 imagePullSecret。
- **登入方式**：`gh auth token | docker login ghcr.io -u timcsy --password-stdin`（不手打/不外露 token）。
- **Alternatives rejected**：(a) `k3s ctr images import`——遠端節點不可行；(b) 自架 registry——YAGNI；(c) Docker Hub——還要另一組帳密，ghcr 已就緒。
- **Tag 策略**：`ghcr.io/timcsy/matcher:<git短sha>` + `:latest`；Deployment 用具體 sha tag（可重現），`imagePullPolicy: IfNotPresent`。

## R-2：基底映像與系統依賴

- **Decision**：`python:3.11-slim-bookworm` + apt 裝 WeasyPrint/PDF/CJK 依賴 + 用 **uv** 安裝 Python 依賴。
- **apt 清單**（沿用 CI 已驗證者）：`libpango-1.0-0 libpangocairo-1.0-0 libcairo2 poppler-utils fonts-noto-cjk`。
- **uv**：複製 `pyproject.toml` + `uv.lock` + `src/` → `uv sync --frozen`（見 R-3 關於 extras）；以 `uv run uvicorn ...` 啟動。
- **Rationale**：與 CI 環境一致（CI 已綠＝這組 apt 足以讓 PDF/CJK 實跑），降低「本機/CI 綠但容器掛」的風險（教訓 10）。
- **Alternatives rejected**：multi-stage 縮圖——可之後優化，初版求簡單可動（YAGNI）。

## R-3：執行期需要 httpx（隱藏需求）⚠️

- **Decision**：把 **httpx 列為執行期依賴**（目前僅在 `[project.optional-dependencies].dev`）。
- **Rationale**：Authlib 的 Starlette OAuth 整合在 `/auth/callback` 交換 token 時透過 **httpx** 發 HTTP；本機/CI 因裝了 dev extras 而正常，但 production 映像若 `--no-dev` 會缺 httpx → **登入會在 callback 失敗**。這是寫 plan 才浮現的隱藏需求（spec-kit research 的價值）。
- **作法**：將 `httpx` 從 `dev` 移到 `[project].dependencies`（`pyproject.toml` 屬專案設定、非 `src/matcher`，不違反 FR-008）。映像以 `uv sync --frozen --no-dev` 安裝即可，不必把 pytest 帶進 production。
- **Alternatives rejected**：映像裝 dev extras——會把 pytest 等測試依賴帶進 production、肥大且語意不清。

## R-4：持久化（PVC）

- **Decision**：`PersistentVolumeClaim`（`local-path`、`ReadWriteOnce`）掛到容器 `/app/data`；Deployment `strategy: Recreate`、`replicas: 1`。
- **Rationale**：預設 StorageClass 為 `local-path`（已確認）。RWO + local-path 綁單節點單 pod；**Recreate**（非 RollingUpdate）避免滾動更新時新舊 pod 同時掛同一 RWO 卷而卡住。單副本對學校規模足夠（YAGNI）。`data/` 為相對路徑、WORKDIR=/app → 卷掛 `/app/data` 即接住既有路徑，**無需改碼**。
- **Alternatives rejected**：多副本 + RWX/NFS——規模用不到、增複雜度。

## R-5：機密與設定

- **Decision**：單一 Secret `matcher-secrets` 由操作者本機 `.env` 灌入（`kubectl create secret generic matcher-secrets --from-env-file=.env`），Deployment 以 `envFrom: secretRef` 注入全部執行期環境變數。
- **Rationale**：`.env` 已含全部所需變數（`GOOGLE_CLIENT_ID/SECRET`、`SESSION_SECRET`、`MATCHER_INSECURE_COOKIE` 等）。`--from-env-file` 自動略過註解/空行。一個 Secret 最簡、且**值完全不入 git/映像**（FR-004）。FR-006「不重建即可改設定」滿足：改 Secret + 重啟即可。
- **Alternatives rejected**：拆 ConfigMap（非機密）+ Secret（機密）——更「正規」但對單一 .env 來源是過度切割（YAGNI）；保留為網域/正式環境時的選項，附註於 quickstart。
- **正式環境註記**：`MATCHER_ENV=production` 時 `SESSION_SECRET` 不可為開發預設（feature 017 boot guard）。本機 port-forward 測試可不設 `MATCHER_ENV`（dev secret 僅警告）。

## R-6：本機存取與 OAuth 回呼

- **Decision**：`kubectl port-forward svc/matcher 8765:8765` → 以 `http://localhost:8765` 存取；容器 uvicorn 監聽 `0.0.0.0:8765`。
- **Rationale**：port-forward 經 API server 隧道到 pod，**遠端叢集一樣可用**。app 的 `request.url_for("auth_callback")` 會依 Host 產生 `http://localhost:8765/auth/callback`，與**現有 OAuth client 已註冊的回呼相符** → 免改 Google 設定即可登入（FR-005）。http localhost → `MATCHER_INSECURE_COOKIE=1`（cookie 不要求 Secure）。
- **Alternatives rejected**：NodePort/直接公網——會用到節點公網 IP、且 OAuth 回呼要改、踩到網域範圍（已排除）。

## R-7：為網域/Ingress 預留（不在本 feature 啟用）

- **Decision**：Deployment 的 uvicorn 加 `--proxy-headers --forwarded-allow-ips="*"`；附 `ingress.example.yaml`（Traefik，網域/TLS 留空待填），**預設不套用**。
- **Rationale**：經 TLS 終結的反向代理時，app 需據 `X-Forwarded-Proto` 產生 `https://...` 回呼，否則 Google 拒絕（spec edge case）。預先加上 proxy-headers，網域那步（使用者自理）才不會卡。對 port-forward 無副作用。
- **Alternatives rejected**：現在就配 Ingress/憑證——使用者明言自理、已排除。

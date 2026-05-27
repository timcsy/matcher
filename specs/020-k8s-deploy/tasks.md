# Tasks: 部署到 K8s（本機 k3s 叢集）

**Feature**: 020-k8s-deploy ｜ **Spec**: ./spec.md ｜ **Plan**: ./plan.md

> 本 feature 為純打包/部署，**不改 `src/matcher`**（唯一例外：`pyproject.toml` 把 httpx 移到執行期依賴，見 research R-3）。「測試」以 quickstart 煙霧驗證（observability）取代程式紅綠測試（constitution gate 已正當化）。

## Phase 1：Setup（前置）

- [ ] T001 確認本機工具就緒：`docker`、`kubectl`（context=`k3s-tew`）、`gh`（已登入、含 write:packages），並確認本機 `.env` 含現用 `GOOGLE_CLIENT_ID/SECRET`、`MATCHER_INSECURE_COOKIE=1`（不修改檔案，只檢查）
- [ ] T002 把 `httpx` 從 `pyproject.toml` 的 `[project.optional-dependencies].dev` 移到 `[project].dependencies`（Authlib OAuth callback 執行期需要；research R-3），`uv lock` 更新 `uv.lock`
- [ ] T003 跑 `uv run --extra dev pytest -q` 確認移動 httpx 後全套件仍綠（無回歸）

## Phase 2：Foundational（所有故事的共同前置——映像與資源定義）

- [ ] T004 [P] 新增 `.dockerignore`（排除 `data/`、`.env`、`.git`、`tests/`、`specs/`、`__pycache__`、`.venv`）
- [ ] T005 新增 `Dockerfile`（根目錄）：基底 `python:3.11-slim-bookworm`、WORKDIR `/app`、apt 裝 `libpango-1.0-0 libpangocairo-1.0-0 libcairo2 poppler-utils fonts-noto-cjk`、安裝 uv、複製 `pyproject.toml`+`uv.lock`+`src/`、`uv sync --frozen --no-dev`、CMD `uv run uvicorn matcher.web.app:create_app --factory --host 0.0.0.0 --port 8765 --proxy-headers --forwarded-allow-ips="*"`
- [ ] T006 本機 build 驗證：`docker build -t matcher:test .` 成功，且 `docker run` 後容器內 `python -c "import weasyprint, httpx"` 不報錯（確認系統依賴與 httpx 到位）
- [ ] T007 [P] 新增 `deploy/k8s/pvc.yaml`：`PersistentVolumeClaim/matcher-data`，`storageClassName: local-path`、`ReadWriteOnce`、1Gi
- [ ] T008 [P] 新增 `deploy/k8s/service.yaml`：`Service/matcher`，`ClusterIP`，port 8765 → targetPort 8765，selector `app=matcher`
- [ ] T009 新增 `deploy/k8s/deployment.yaml`：`Deployment/matcher`，`replicas:1`、`strategy:Recreate`、label `app=matcher`、image `ghcr.io/timcsy/matcher:<sha>`（佔位，build 後帶入）、`imagePullPolicy:IfNotPresent`、`envFrom:[secretRef:matcher-secrets]`、volume 掛 `matcher-data` 於 `/app/data`、`readinessProbe`/`livenessProbe` httpGet `/login`:8765
- [ ] T010 [P] 新增 `deploy/k8s/configmap.yaml`（可選覆寫處，初版可留最小註解說明）與 `deploy/k8s/ingress.example.yaml`（Traefik 範例、host 預設 `match.tew.tw`、TLS 留空待填、預設不套用）
- [ ] T011 [P] 新增 `deploy/README.md`：指向 `specs/020-k8s-deploy/quickstart.md`，摘要 build→push→secret→apply→port-forward 流程

## Phase 3：US1 — 部署可達（P1）🎯 MVP

**目標**：套用資源後工作負載就緒、本機可開首頁。
**獨立驗收**：`kubectl rollout status` 5 分內 Ready 且 `curl -sf http://localhost:8765/login` 回 200（SC-001）。

- [ ] T012 [US1] build + tag：`docker build -t ghcr.io/timcsy/matcher:$(git rev-parse --short HEAD) -t ghcr.io/timcsy/matcher:latest .`
- [ ] T013 [US1] 登入並推送 ghcr：`gh auth token | docker login ghcr.io -u timcsy --password-stdin` → `docker push` 兩個 tag；於 GitHub 確認/設定該 package 為 public
- [ ] T014 [US1] 把 `deploy/k8s/deployment.yaml` 的 image tag 設為步驟 T012 的 `<sha>`
- [ ] T015 [US1] 灌機密：`kubectl create secret generic matcher-secrets --from-env-file=.env --dry-run=client -o yaml | kubectl apply -f -`（值來自本機 `.env`，不入庫）
- [ ] T016 [US1] 套用資源：`kubectl apply -f deploy/k8s/pvc.yaml -f deploy/k8s/service.yaml -f deploy/k8s/deployment.yaml` 並 `kubectl rollout status deploy/matcher --timeout=300s`
- [ ] T017 [US1] 驗收 SC-001：`kubectl port-forward svc/matcher 8765:8765` 後 `curl -sf http://localhost:8765/login` 回 200；異常則查 `kubectl logs deploy/matcher`

## Phase 4：US2 — Google 登入並完成配對（P1）

**目標**：用現有 Google 帳號從 `localhost:8765` 登入、跑一次配對、下載 PDF。
**獨立驗收**：真人登入成功 + 配對結果 + 稽核 PDF（SC-002）。依賴 T002（httpx）已在映像中。

- [ ] T018 [US2] 確認映像含 httpx（T006 已驗）且 `.env` 的 `GOOGLE_CLIENT_ID/SECRET` 為現用值、Secret 已灌（T015）
- [ ] T019 [US2] 真人驗收 SC-002：瀏覽器開 `http://localhost:8765` → Google 登入成功導回 → 跑一次配對 → 下載稽核 PDF（驗證容器內 WeasyPrint/CJK 正常）。**登入由使用者本人操作**（學校帳號分頁）

## Phase 5：US3 — 重啟資料不遺失（P2）

**目標**：pod 重建後配對紀錄與自訂範本仍在。
**獨立驗收**：刪 pod → 重建 → 資料 100% 保留（SC-003）。PVC 已於 T007/T009 接上。

- [ ] T020 [US3] 驗收 SC-003：先跑一筆配對 + 建一個自訂範本 → `kubectl delete pod -l app=matcher` → `kubectl rollout status` → 重新 port-forward，確認「過去紀錄」與該自訂範本仍在

## Phase 6：US4 — 機密不外洩（P2）

**目標**：repo 與映像皆無真實機密值。
**獨立驗收**：稽核版本控制與映像（SC-004）。

- [ ] T021 [P] [US4] 確認 `.gitignore` 已涵蓋 `.env`；`git ls-files` 與 `deploy/k8s/*` 內無真實機密值（manifests 只引用 Secret 名稱）
- [ ] T022 [US4] 驗收 SC-004：`git grep -nIE 'GOCSPX-|gho_'`（追蹤檔）無結果；`docker history` / 映像層不含 `.env`（`.dockerignore` 已排除）

## Phase 7：Polish & 收尾

- [ ] T023 [P] 驗收 SC-005：`git diff main -- src/matcher` 為空（本 feature 0 改動核心）
- [ ] T024 [P] 更新 `knowledge/vision.md`：階段 5 勾選完成、補現狀條目（映像 ghcr、PVC、port-forward 存取、網域自理）
- [ ] T025 [P] 更新 `README.md`：加「部署到 K8s」一節，指向 `deploy/README.md` / quickstart

## Dependencies（完成順序）

```
Setup (T001-T003)
  └─ Foundational (T004-T011：Dockerfile + manifests + README)
       └─ US1 (T012-T017：build/push/secret/apply/驗達)  🎯 MVP
            ├─ US2 (T018-T019：登入+配對)        ← 需映像含 httpx(T002) + secret(T015)
            ├─ US3 (T020：持久化)                ← 需 PVC(T007/T009) 已部署
            └─ US4 (T021-T022：機密稽核)
                 └─ Polish (T023-T025)
```

## 平行機會

- Foundational 內：T004 / T007 / T008 / T010 / T011 可平行（不同檔案）；T005→T006、T009 依序。
- Polish 內：T023 / T024 / T025 可平行。

## MVP 範圍

**US1（T001-T017）** 即可交付一個「部署得起來、本機打得開首頁」的最小可用成果；US2 才補上登入實證，US3/US4 為持久化與機密稽核驗收。

## 格式檢查

所有任務皆含 checkbox + TaskID + （適用時）[P]/[US#] 標籤 + 明確檔案路徑/指令。

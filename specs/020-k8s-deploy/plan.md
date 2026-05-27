# Implementation Plan: 部署到 K8s（本機 k3s 叢集）

**Branch**: `020-k8s-deploy` | **Date**: 2026-05-27 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/020-k8s-deploy/spec.md`

## Summary

把現有 matcher Web 應用打包成單一容器，部署到本機 k3s 叢集：PVC 持久化 `data/`、機密走叢集 Secret（來源操作者本機 `.env`，不入 git/映像）、本機以 `port-forward` 對到 `localhost:8765` 沿用既有 Google OAuth 回呼。**純打包與部署，`src/matcher` 0 改動**。網域/TLS/Ingress 由使用者自理（僅附範例）。

## Technical Context

**Language/Version**: Python 3.11（沿用；映像基底 `python:3.11-slim-bookworm`）
**Primary Dependencies**: 沿用（fastapi、uvicorn[standard]、jinja2、weasyprint、authlib、itsdangerous、PyYAML、openpyxl、Typer）；環境以 **uv** 安裝（沿用工具鏈）
**Storage**: 純檔案系統 `data/`（match 紀錄 JSON + 範本 YAML），掛在 **PVC**（k3s local-path 動態供應）；無 DB
**Testing**: 既有 pytest 全套件（CI 已綠）＋本 feature 的**部署煙霧驗證**（quickstart 手動 runbook：pod ready / 首頁 / 登入 / 持久化）
**Target Platform**: K8s（本機單節點 **k3s**，context `k3s-tew`），容器內 Linux
**Project Type**: Web 應用（部署/打包 feature）
**Performance Goals**: 不適用（單機、單副本即可滿足學校規模）
**Constraints**: 單一容器、無外部 DB、機密不入 git/映像、`src/matcher` 0 改動、沿用現有 OAuth client id
**Scale/Scope**: 單副本、單節點；學校等級流量

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. 測試先行（TDD）**：⚠️ 本 feature **不新增 `src/matcher` 行為**（FR-008），故無「程式行為的紅綠測試」。改以 **observability（原則 V）的可檢驗輸出**滿足精神：quickstart 提供可重複執行的煙霧驗證（pod ready、`curl` 首頁、真人登入、刪 pod 後資料仍在）。既有 pytest 全套件仍須維持綠。→ 已於 Complexity Tracking 記錄此正當偏離。
- **II. 規格優先**：✅ 已有 spec → 本 plan → 後續 tasks。
- **III. 繁體中文文件**：✅ 全部產出繁中。
- **IV. 簡潔優先（YAGNI）**：✅ 單副本、單 Secret、不引入 registry/Helm/Kustomize；只用最小 manifests。Ingress 僅附範例不啟用。
- **V. 可觀測性**：✅ 部署驗收靠可人工檢視的輸出（HTTP 回應、pod 狀態、資料檔存在）。

**Gate 結論**：通過（TDD 偏離已正當化——零程式行為變更的純部署 feature）。

## Project Structure

### Documentation (this feature)

```text
specs/020-k8s-deploy/
├── plan.md              # 本檔
├── research.md          # Phase 0：關鍵決策（映像進 k3s、基底+依賴、PVC、Secret/Config、存取）
├── data-model.md        # Phase 1：部署資源與環境變數契約
├── quickstart.md        # Phase 1：操作 runbook ＋ 驗收步驟
├── contracts/           # Phase 1：環境變數契約 + K8s 資源外形
└── tasks.md             # Phase 2（/speckit.tasks 產出，本指令不建）
```

### Source Code (repository root)

本 feature **不改 `src/`**；新增的是部署成品（repo 根目錄）：

```text
Dockerfile                      # 單一容器映像（apt 系統依賴 + uv 安裝 + uvicorn）
.dockerignore                   # 排除 data/、.env、.git、tests 等
deploy/k8s/
├── pvc.yaml                    # data/ 持久卷宣告（local-path）
├── deployment.yaml             # 應用工作負載（envFrom secret/config、掛 PVC、proxy-headers）
├── service.yaml                # ClusterIP，供 port-forward
├── configmap.yaml              # 非機密設定（MATCHER_INSECURE_COOKIE 等預設）
└── ingress.example.yaml        # 範例（網域/TLS 由使用者自填，預設不套用）
deploy/README.md                # 部署說明（指向 quickstart）
```

**Structure Decision**：部署資源集中於 `deploy/k8s/`；映像定義於根 `Dockerfile`。機密**不**入庫（由 `kubectl create secret --from-env-file=.env` 於本機產生）。`src/matcher`、`tests/` 不動。

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| TDD 無「程式紅綠測試」 | 此為純打包/部署 feature，FR-008 明令 0 程式行為變更，無可寫的單元/整合行為測試 | 強行寫程式測試＝無對應行為可測；改以 quickstart 可重複煙霧驗證（原則 V observability）滿足「行為可檢驗」精神，且既有全套件須維持綠 |

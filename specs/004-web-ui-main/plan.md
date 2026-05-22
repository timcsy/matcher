# Implementation Plan: Web UI 主流程

**Branch**: `004-web-ui-main` | **Date**: 2026-05-22 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/004-web-ui-main/spec.md`

## Summary

新增 `src/matcher/web/` 子套件，使用 FastAPI + HTMX + Jinja2 提供 server-rendered Web UI。重用既有 `src/matcher/` library 進行媒合與資料匯入；媒合紀錄持久化於 `data/matches/*.json`。CLI 新增 `matcher serve` 子命令啟動本地 server。新增 4 個依賴：fastapi、uvicorn[standard]、jinja2、python-multipart。無 auth；繁中介面。

## Technical Context

**Language/Version**: Python 3.11+（沿用）
**Primary Dependencies**: 沿用（Typer、PyYAML、pytest、openpyxl）+ **新增 fastapi ≥ 0.110、uvicorn[standard] ≥ 0.27、jinja2 ≥ 3.1、python-multipart ≥ 0.0.9**
**Storage**: `data/matches/` 下純檔案系統 JSON（每次媒合一檔）；無資料庫
**Testing**: pytest + `fastapi.testclient.TestClient`（同步 HTTP 整合測試，無需 async runner）
**Target Platform**: 跨平台（macOS / Linux / Windows）；瀏覽器目標 Chrome / Firefox / Edge / Safari 近 2 年版本
**Project Type**: library + CLI + Web App（單一 Python 套件 `matcher`）
**Performance Goals**: 結果頁回應 ≤ 5 秒（基準場景）；上傳處理 + 媒合 + 寫紀錄總時間 < 2 秒（內部目標）
**Constraints**: 跨版本確定性沿用；既有 116 測試 100% 通過（SC-008）；audit schema 不變動；無新增第三方依賴於 src/matcher/{rules,filter,allocator,...} 等核心模組
**Scale/Scope**: 單機 / LAN 環境；同時連線數 ≤ 10；媒合紀錄歷史 ≤ 10000 筆（檔案系統可承受）

## Constitution Check

對齊 constitution v1.0.0 五原則：

| 原則 | 本計畫如何遵守 | 狀態 |
|---|---|---|
| I. 測試先行（TDD） | 每個 FR 對應 ≥ 1 個 TestClient 測試；先紅後綠；UI 樣板測試以「response body 含某字串」為斷言 | ✅ |
| II. 規格優先 | spec.md 無 [NEEDS CLARIFICATION]；本 plan 為技術選型集中點 | ✅ |
| III. 繁體中文文件 | 所有 spec/plan/research/contracts 為繁中；UI 文案、錯誤訊息全繁中（FR-019）；template 中可閱讀文字繁中 | ✅ |
| IV. 簡潔優先 | server-rendered HTML（無 Node toolchain / SPA 框架）；只在 web/ 子套件引入 fastapi 等依賴，核心媒合引擎不變；不引入 SQLite / Redis；無 auth | ✅ |
| V. 可觀測性 | 媒合紀錄完整持久化（含失敗時的錯誤詳情）；HTTP 錯誤狀態碼明確（FR-020）；繁中三段式錯誤訊息沿用既有風格 | ✅ |

**Gate 評估**：通過，無 Complexity Tracking 條目。

## Project Structure

### Documentation (this feature)

```text
specs/004-web-ui-main/
├── plan.md
├── spec.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── http-endpoints.md
│   ├── match-record-schema.json
│   └── ui-pages.md
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Source Code (新增/修改)

```text
src/matcher/
├── web/                              # 新：Web app 子套件
│   ├── __init__.py
│   ├── app.py                        # FastAPI app 工廠
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── pages.py                  # GET 頁面（首頁、模板列表、模板詳情、過去媒合）
│   │   ├── match.py                  # POST 新建媒合 / GET 結果 / GET 下載 audit
│   │   └── records.py                # 媒合紀錄列表與單筆查詢
│   ├── store.py                      # MatchStore：persist/list/get 媒合紀錄
│   ├── templates/                    # Jinja2 樣板
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── templates_list.html
│   │   ├── template_detail.html
│   │   ├── new_match.html            # 4 步驟向導（單頁，HTMX swap）
│   │   ├── match_result.html
│   │   ├── records_list.html
│   │   └── partials/
│   │       ├── error.html
│   │       └── upload_field.html
│   └── static/                       # 極簡 CSS / JS（HTMX 透過 CDN）
│       └── style.css
├── cli.py                            # 修：新增 `matcher serve` 子命令
└── （既有核心模組不變）

tests/
├── unit/
│   └── test_web_store.py             # 新（MatchStore 單元測試）
├── integration/
│   ├── test_web_pages.py             # 新（GET 頁面渲染正確）
│   ├── test_web_new_match.py         # 新（完整 4 步驟流程 + audit 等價）
│   ├── test_web_match_records.py     # 新（持久化 + 重新查看）
│   ├── test_web_upload_validation.py # 新（5MB / MIME / 缺欄位等）
│   ├── test_web_backward_compat.py   # 新（CLI 既有功能不變）
│   └── （既有檔案不變）
└── golden/
    └── （階段 3 不新增黃金檔；audit 等價驗證走「Web 路徑跑出的 audit 與 CLI 路徑 audit 五段相同」程式比對，沿用既有 golden）

data/                                 # 媒合紀錄持久化目錄（.gitignore 忽略）
└── matches/
    └── <timestamp>-<uuid>.json
```

**Structure Decision**：Web 層為「在 library 之上的第二個入口」，與 CLI 平行；
完全不動既有核心模組（rules / filter / allocator / pipeline / data_import / template_loader / audit）。
Routes 依資源切三檔（pages / match / records）；HTMX 互動以**樣板部分 swap** 為主，避免單頁應用的複雜度。
`matcher serve` 子命令委派給 `uvicorn.run(app, host, port)`。

## Complexity Tracking

> Constitution Check 全部通過，本段保留空白。

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| （無）| | |

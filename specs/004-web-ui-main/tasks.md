---

description: "Task list for Web UI 主流程"
---

# Tasks: Web UI 主流程

**Input**: Design documents from `/specs/004-web-ui-main/`
**Prerequisites**: plan.md ✅、spec.md ✅、research.md ✅、data-model.md ✅、contracts/ ✅、quickstart.md ✅

**Tests**: 包含。Constitution v1.0.0 原則 I（TDD）為不可妥協條款。

**Organization**：依 spec.md 中 P1 / P2 / P3 三條 user story 分組。

## Format: `[ID] [P?] [Story] Description`

- **[P]**：可平行執行（檔案不同、無前置未完成任務）
- **[Story]**：對應的 user story 標籤（US1 / US2 / US3）

---

## Phase 1：Setup

**目的**：新依賴安裝、目錄骨架。

- [x] T001 在 `pyproject.toml` 的 `dependencies` 新增 `fastapi>=0.110`、`uvicorn[standard]>=0.27`、`jinja2>=3.1`、`python-multipart>=0.0.9`；執行 `uv pip install -e ".[dev]"` 確認安裝
- [x] T002 [P] 建立 `src/matcher/web/` 套件骨架：`__init__.py`、`routes/__init__.py`、`templates/`（空目錄）、`templates/partials/`、`static/`
- [x] T003 [P] 在 `.gitignore` 新增 `data/` 一行（媒合紀錄持久化目錄不入 git）

---

## Phase 2：Foundational（阻塞所有 user story）

**目的**：模板 `default_targets` 擴充、MatchStore、FastAPI app 骨架、共用樣板。

**⚠️ CRITICAL**：本階段未完成前，任何 user story 不可開始。

- [x] T004 [P] 在 `src/matcher/template.py` 擴充 `Template` dataclass：新增選填欄位 `default_targets: tuple = ()`（依 R-012）
- [x] T005 在 `src/matcher/template_loader.py` 的 `parse_template` 中讀取頂層 `default_targets` 欄位（list of dict → tuple of Target）；`dump_template_yaml` 也同步輸出 default_targets（依 T004）
- [x] T006 [P] 修改 `src/matcher/templates/builtin/teacher-class.yaml`：新增 `default_targets:` 段，內容為既有 `examples/teacher-class/roster.targets.yaml` 中的 5 個班級
- [x] T007 [P] 修改 `src/matcher/templates/builtin/study-group.yaml`：新增 `default_targets:` 段，內容為 3 個分組
- [x] T008 修改 `src/matcher/data_import.py` 的 `_load_targets_sidecar`：若旁檔不存在 → 改從傳入的 `template.default_targets` 取得 targets；皆無時才拋既有錯誤；同時調整 `load_roster_csv` / `load_roster_xlsx` 簽章使其接受可選 sidecar 模式（依 T004）
- [x] T009 在 `src/matcher/audit.py` 的 `_template_to_dict` 加入 `default_targets` 序列化（依 T004）
- [x] T010 重生既有 4 個黃金檔：`tests/golden/teacher-class-template.audit.json`、`tests/golden/study-group-template.audit.json`、`tests/golden/teacher-class-csv.audit.json`、`tests/golden/study-group-xlsx.audit.json`（template_snapshot 含 default_targets；assignment 不變）；確認既有 116 測試仍通過

**Checkpoint 1**：core 端 default_targets 整合完成。

- [x] T011 建立 `src/matcher/web/store.py`：`MatchStore` 類別（`save`、`list`、`get`），atomic write（`<id>.json.tmp` → `os.replace`）；錯誤類別 `MatchRecordNotFound`；id 格式 `<YYYY-MM-DDTHH-MM-SS>-<uuid8>`
- [x] T012 [P] 建立 `src/matcher/web/errors.py`：`UploadTooLarge`、`UploadInvalidMime` 兩個 Web 層錯誤類別
- [x] T013 [P] 建立 `src/matcher/web/templates/base.html`：依 contracts/ui-pages.md 共用樣板（含 header / nav / footer / HTMX CDN）
- [x] T014 [P] 建立 `src/matcher/web/templates/partials/error.html` 與 `partials/upload_field.html`（依 ui-pages.md「共用元件」段）
- [x] T015 [P] 建立 `src/matcher/web/static/style.css`：依 ui-pages.md「樣式」段的色彩與排版規格（< 200 行）
- [x] T016 建立 `src/matcher/web/app.py`：FastAPI app 工廠 `create_app() -> FastAPI`；mount `/static`；註冊 Jinja2Templates；註冊三個 routers（pages、match、records，於各 US 階段建立）

**Checkpoint 2**：foundational 完成。

---

## Phase 3：User Story 1 — 完整媒合主流程（P1）🎯 MVP

**Goal**：4 步驟向導跑通教師-班級基準場景，下載 audit 與 CLI 路徑等價。

**Independent Test**：執行 quickstart 第 3、4 節：選 teacher-class → 上傳 `examples/teacher-class/roster.csv` → seed 123456 → 結果頁顯示分配；下載 audit 與 CLI 同 seed 跑出的五段相同。

### 測試（先寫且必須先紅）⚠️

- [x] T017 [P] [US1] `tests/integration/test_web_new_match.py`：(a) `GET /match/new` 200 + 含 4 步驟向導；(b) `POST /match/run`（multipart 上傳 + template_id + seed）→ 302 → `/match/{id}`；(c) `GET /match/{id}` 顯示成功結果頁、含分配表與 audit 下載連結；(d) `GET /match/{id}/audit` 下載的 JSON 五段與 CLI 對應跑出的 audit bytewise 相同
- [x] T018 [P] [US1] `tests/integration/test_web_upload_validation.py`：(a) 上傳 > 5 MB → 400；(b) MIME 不在白名單 → 400；(c) CSV 缺必填欄位 → 結果頁顯示失敗（status=failed），錯誤訊息含「缺漏」與 aliases；(d) seed 非整數 → 400

### 實作

- [x] T019 [US1] 建立 `src/matcher/web/routes/match.py`：含端點 `GET /match/new`、`POST /match/new/step{2,3}`（HTMX swap）、`POST /match/run`、`GET /match/{record_id}`、`GET /match/{record_id}/audit`；run 端點完整流程：驗證 upload → tmp file → `load_roster_csv` 或 `load_roster_xlsx`（依 MIME）→ `run_match` → `MatchStore.save` → tmp unlink → 302（依 T011、T012、T008）
- [x] T020 [P] [US1] 建立 `src/matcher/web/templates/new_match.html` 與 `partials/wizard_step{1,2,3,4}.html`：4 步驟向導，HTMX `hx-post` 觸發 swap
- [x] T021 [P] [US1] 建立 `src/matcher/web/templates/match_result.html`：成功模式（分配表 + 摘要 + 下載按鈕）+ 失敗模式（錯誤訊息 + 重試）
- [x] T022 [US1] 在 `src/matcher/web/app.py` 註冊 match router（依 T019）

**Checkpoint**：US1 完成。MVP 可獨立驗證——quickstart 第 3、4 節通過。

---

## Phase 4：User Story 2 — 模板瀏覽（P2）

**Goal**：模板列表 + 詳情頁能展示內建模板完整內容。

**Independent Test**：`GET /templates` 顯示兩個模板卡片；`GET /templates/teacher-class` 顯示 attributes / rules / ui_fields / default_targets 等完整內容。

### 測試（先寫且必須先紅）⚠️

- [x] T023 [P] [US2] `tests/integration/test_web_pages.py`：(a) `GET /` 200 + 含三個入口；(b) `GET /templates` 200 + 含「teacher-class」與「study-group」；(c) `GET /templates/teacher-class` 200 + 含「R001」「R002」「R003」「default_targets」（中文「預設對象」）；(d) `GET /templates/no-such` 404

### 實作

- [x] T024 [US2] 建立 `src/matcher/web/routes/pages.py`：端點 `GET /`（首頁）、`GET /templates`（列表）、`GET /templates/{id}`（詳情，404 → TemplateNotFound）
- [x] T025 [P] [US2] 建立 `src/matcher/web/templates/index.html`（依 ui-pages.md「首頁」）
- [x] T026 [P] [US2] 建立 `src/matcher/web/templates/templates_list.html`（卡片式列表）
- [x] T027 [P] [US2] 建立 `src/matcher/web/templates/template_detail.html`（四大段：基本資訊 / 屬性 schema / 規則 / UI 欄位+報告欄位+default_targets+preferences_schema）
- [x] T028 [US2] 在 `src/matcher/web/app.py` 註冊 pages router（依 T024）

**Checkpoint**：US2 完成。SC-004 通過。

---

## Phase 5：User Story 3 — 過去媒合紀錄（P3）

**Goal**：媒合紀錄持久化、列表、重看。

**Independent Test**：跑 3 次媒合後 `GET /matches` 看到 ≥ 3 筆；點任一成功紀錄能還原結果頁。

### 測試（先寫且必須先紅）⚠️

- [x] T029 [P] [US3] `tests/unit/test_web_store.py`：`MatchStore.save / list / get` 三個操作；list 依時間遞減；get 不存在 → `MatchRecordNotFound`；同 id 寫兩次 → 第二次覆寫（atomic）
- [x] T030 [P] [US3] `tests/integration/test_web_match_records.py`：(a) 跑兩次媒合 → `GET /matches` 顯示 2 筆；(b) 點最舊的一筆 → `GET /match/{id}` 還原結果頁；(c) 失敗的媒合也出現在列表（status=failed）；(d) `GET /match/{id}/audit` 對失敗紀錄回應 404

### 實作

- [x] T031 [US3] 建立 `src/matcher/web/routes/records.py`：端點 `GET /matches`（呼叫 `MatchStore.list(limit=50)`）（依 T011）
- [x] T032 [P] [US3] 建立 `src/matcher/web/templates/records_list.html`：表格 + 空狀態（依 ui-pages.md）
- [x] T033 [US3] 在 `src/matcher/web/app.py` 註冊 records router（依 T031）

**Checkpoint**：US3 完成。SC-005 通過。

---

## Phase 6：Polish & Cross-Cutting

- [x] T034 在 `src/matcher/cli.py` 新增 `matcher serve` 子命令：參數 `--host`（預設 127.0.0.1）、`--port`（預設 8000）、`--reload`（開發模式）；內部呼叫 `uvicorn.run("matcher.web.app:create_app", factory=True, ...)`
- [x] T035 [P] `tests/integration/test_web_backward_compat.py`：階段 1/2a/2b 既有 CLI 路徑 100% 仍可用（`matcher run --rules ...` / `matcher template list` / `matcher run --template ... --roster-csv ...`）
- [x] T036 [P] 更新 `README.md`：新增「Web UI」段，含 `matcher serve` 用法、瀏覽器流程
- [x] T037 [P] 跑完整 quickstart.md 第 1–8 節，逐項勾選驗證
- [x] T038 [P] 全量回歸：`uv run pytest` 必須全綠（階段 1+2a+2b 既有 116 + 階段 3a 新增 ≈ 25，總計 ≈ 141）

---

## Dependencies & Execution Order

### Phase 相依

- **Setup (1)**：無前置
- **Foundational (2)**：依賴 Setup；阻塞所有 user story；內含兩個 checkpoint（core 完成 + web 骨架完成）
- **US1 (3)**：依賴 Foundational；MVP 核心
- **US2 (4)**：依賴 Foundational；可與 US1 平行（不同 routes / templates）
- **US3 (5)**：依賴 Foundational + MatchStore；可與 US2 平行
- **Polish (6)**：依賴 US1（CLI serve 子命令需 app.py 完整）

### Parallel Opportunities

- T002 / T003（Setup 內 [P]）平行
- T004 / T006 / T007（不同檔案的模板擴充）平行
- T012 / T013 / T014 / T015（不同模組/樣板）平行
- US1 測試 T017 / T018 [P] 平行
- US1 樣板 T020 / T021 平行於 T019 路由實作
- US2 整體可與 US3 平行（不同 routes 檔案）
- Polish 5 個任務全 [P]

---

## Implementation Strategy

### MVP First（只到 US1）

1. Phase 1：Setup（裝依賴 + 建骨架）
2. Phase 2：Foundational（default_targets 擴充 + 重生 4 個黃金檔 + MatchStore + FastAPI 骨架）
3. Phase 3：US1（先紅測試 → 路由實作 → 樣板）
4. **STOP & VALIDATE**：瀏覽器跑通 quickstart 第 3、4 節；驗證 SC-002 / SC-003

### Incremental Delivery

1. Setup + Foundational → 基底就緒
2. US1 → MVP（4 步驟向導跑通基準場景）
3. US2 → 模板瀏覽完整體驗
4. US3 → 過去媒合紀錄
5. Polish → `matcher serve` 命令、向後相容、README、真人實測（SC-001）

### TDD 嚴格度

- 測試先紅後綠
- 4 個既有黃金檔在 T010 一次性重生；不能影響邏輯（assignment 必須不變）
- Bug 修補先補測試

---

## Notes

- [P] 任務 = 不同檔案、無未完成相依
- [Story] 標籤 = 任務歸屬的 user story
- 測試必須**先紅後綠**
- 每完成一個任務或邏輯群組即 commit
- 任一 checkpoint 皆可暫停驗證
- 避免：跨 story 的硬相依、無聲修改既有黃金檔、引入未在 plan 中宣告的依賴
- **SC-001（30 分鐘真人測試）為人工驗證項目**，不在本任務清單內；本 feature 完成後安排

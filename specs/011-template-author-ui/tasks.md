# Tasks: 模板創作工具 UI

**Feature**: 011-template-author-ui
**Branch**: `011-template-author-ui`
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

**TDD 強制**（constitution I）：每個 user story 內，測試任務 MUST 先寫並先紅後再實作。

> **動核心警示**：本 feature 動 `src/matcher/template_loader.py`——是教訓 7 第 3 種合法情境（核心職責擴充）。所有變更需在 plan.md Constitution Check 段論證。**任務拆分時保持「既有方法簽名不變」**（SC-010）。

---

## Phase 1 — Setup

- [ ] T001 建立目錄 `data/templates/` + `.gitkeep`（執行 `mkdir -p data/templates && touch data/templates/.gitkeep`）
- [ ] T002 確認 `.gitignore` 對 `data/templates/*/` 是否需排除——預期不排除（自訂模板可入 git）；若 `data/` 全被 ignore，加 `!data/templates/` 例外
- [ ] T003 確認 FastAPI app 已 mount `static/` 目錄供 `template_form.js` 載入（檢查 `src/matcher/web/app.py`；如未 mount 則加 `app.mount("/static", StaticFiles(directory=...), name="static")`）

---

## Phase 2 — Foundational

阻塞所有 user stories 的共用變更：TemplateRegistry 擴充 + 表單組裝純函式 + 場景樣板常數。

### Tests (TDD — 先紅)

- [ ] T010 [P] 撰寫 `tests/unit/test_template_registry_custom_scan.py::test_scan_empty_custom_dir_works` —— 空 `data/templates/` 不應出錯，registry.list_ids() 同 builtin
- [ ] T011 [P] 撰寫 `tests/unit/test_template_registry_custom_scan.py::test_scan_custom_template_v1` —— 寫入 `tmp/data/templates/my-tpl/v1.yaml`，registry 應含 `my-tpl`、`is_builtin("my-tpl")==False`、`list_versions("my-tpl") == [1]`
- [ ] T012 [P] 撰寫 `tests/unit/test_template_registry_custom_scan.py::test_get_returns_latest_version` —— 寫 v1 + v2 + v3，`get("my-tpl")` 應為 v3 內容、`get_version("my-tpl", 1)` 為 v1 內容
- [ ] T013 [P] 撰寫 `tests/unit/test_template_registry_custom_scan.py::test_save_custom_writes_v1_then_v2` —— 兩次 save_custom 應產生 v1.yaml 與 v2.yaml；版本號自動遞增
- [ ] T014 [P] 撰寫 `tests/unit/test_template_registry_custom_scan.py::test_save_custom_rejects_builtin_id` —— save_custom 試圖用 `teacher-class` id 應 raise ValueError 含「已存在於內建模板」
- [ ] T015 [P] 撰寫 `tests/unit/test_template_registry_custom_scan.py::test_invalidate_picks_up_new_template` —— save → invalidate → list_ids 即見新 id
- [ ] T016 [P] 撰寫 `tests/unit/test_template_registry_custom_scan.py::test_is_builtin_distinguishes_correctly` —— teacher-class==True；自訂==False
- [ ] T017 [P] 撰寫 `tests/unit/test_template_form_assembly.py::test_assemble_simple_form_to_yaml_dict` —— 表單 dict（5 attrs + 2 rules + 3 default_targets）→ assemble_template_yaml → parse_template 可接受
- [ ] T018 [P] 撰寫 `tests/unit/test_template_form_assembly.py::test_auto_description_for_each_rule_type` —— 5 種規則類型各自生成的 description 合理（如「角色年級必須 ≥ 4」）且無技術 token
- [ ] T019 [P] 撰寫 `tests/unit/test_template_form_assembly.py::test_custom_description_overrides_auto` —— form 提供 custom_description 時，使用者版本生效
- [ ] T020 [P] 撰寫 `tests/unit/test_template_form_assembly.py::test_scenario_template_constants_all_valid` —— SCENARIO_TEMPLATES 各預設場景皆能 assemble + parse_template 通過

### Implementation

- [ ] T021 修改 `src/matcher/template_loader.py::TemplateRegistry.__init__` — 加 `custom_dir: Path = Path("data/templates")` 參數（預設值保持向後相容）+ 新增 `_custom_versions: dict[str, dict[int, Template]]` 屬性
- [ ] T022 在 `src/matcher/template_loader.py` 新增 `TemplateRegistry._scan_custom_dir(self) -> None` 方法——掃 `data/templates/<id>/v<N>.yaml`，每個 id 取 max(N) 進主 cache，所有版本進 `_custom_versions`
- [ ] T023 在 `src/matcher/template_loader.py` 新增 `TemplateRegistry.is_builtin(template_id) -> bool`、`list_versions(template_id) -> list[int]`、`get_version(template_id, version) -> Template`、`invalidate() -> None`、`save_custom(tpl_dict: dict) -> tuple[str, int]` 方法
- [ ] T024 修改 `TemplateRegistry.__init__` 末段加 `self._scan_custom_dir()` 呼叫；確保既有 `_scan()`（builtin）先跑、再跑自訂；以「先 builtin 後自訂、衝突時 builtin 優先 cache」順序
- [ ] T025 新增 `src/matcher/web/template_form.py`：含 `assemble_template_yaml(form: dict) -> dict` 純函式 + 子函式 `_build_expr(rule_type, fields)`、`_auto_description(rule_type, fields, attributes_lookup) -> str`
- [ ] T026 在 `template_form.py` 加 `SCENARIO_TEMPLATES` module-level 常數 dict（5 預設場景：blank / club-signup / tutoring / study-group-like / teacher-class-like）
- [ ] T027 驗證 T010-T020 由紅轉綠（執行 `uv run pytest tests/unit/test_template_registry_custom_scan.py tests/unit/test_template_form_assembly.py -q`）

**Checkpoint Phase 2**：核心擴充完成；表單組裝純函式完成；無 UI / endpoint。

---

## Phase 3 — User Story 1 (P1) 🎯 MVP：簡單模式建立模板

**Goal**：`/templates/new` 簡單模式表單可建立 + 驗證 + 儲存 + 自訂模板出現在 `/match/new` 下拉。

**Independent Test**：在新 session 中從零建立社團報名模板（場景樣板「社團報名」起 + 改 id 為 my-club → 驗證 → 儲存），跑通一次媒合。

### Tests (TDD — 先紅)

- [ ] T030 [P] [US1] 撰寫 `tests/integration/test_template_authoring_simple.py::test_get_new_page_default_simple_mode` —— GET `/templates/new` 200 + HTML 含「簡單模式」「進階模式」兩頁籤；預設簡單
- [ ] T031 [P] [US1] 撰寫 `tests/integration/test_template_authoring_simple.py::test_scenario_template_dropdown_prefills_form` —— GET `/templates/new?scenario=club-signup` 應預填 3 屬性 + 2 規則
- [ ] T032 [P] [US1] 撰寫 `tests/integration/test_template_authoring_simple.py::test_validate_endpoint_returns_summary_on_valid` —— POST `/templates/validate` 帶合法簡單模式 form → JSON `{ok: true, summary: {...}}`
- [ ] T033 [P] [US1] 撰寫 `tests/integration/test_template_authoring_simple.py::test_validate_endpoint_returns_errors_on_missing_id` —— 缺 template_id → JSON `{ok: false, errors: [...]}`
- [ ] T034 [P] [US1] 撰寫 `tests/integration/test_template_authoring_simple.py::test_save_creates_v1_yaml_file` —— POST `/templates/save` 合法 form → 200 + `data/templates/<id>/v1.yaml` 檔案存在 + 內容對齊
- [ ] T035 [P] [US1] 撰寫 `tests/integration/test_template_authoring_simple.py::test_save_then_match_new_dropdown_shows_new_template` —— 儲存後 GET `/match/new` 下拉含新 id
- [ ] T036 [P] [US1] 撰寫 `tests/integration/test_template_authoring_simple.py::test_save_persists_across_registry_reinit` —— 儲存後重新 `TemplateRegistry()` 仍可載入（模擬 server 重啟）
- [ ] T037 [P] [US1] 撰寫 `tests/integration/test_template_authoring_simple.py::test_save_rejects_builtin_id` —— POST template_id=`teacher-class` → 409 + 繁中錯誤
- [ ] T038 [P] [US1] 撰寫 `tests/integration/test_template_authoring_simple.py::test_save_rejects_invalid_id_format` —— template_id 含空白或中文 → 400

### Implementation

- [ ] T039 [US1] 修改 `src/matcher/web/routes/templates.py` 新增 `GET /templates/new` 端點：渲染 `template_authoring.html`；query string 取 `scenario`、`mode`、`fork`，傳入 context
- [ ] T040 [US1] 修改 `routes/templates.py` 新增 `POST /templates/validate` 端點：接 form 或 JSON、呼叫 `assemble_template_yaml`（或直接 `yaml.safe_load(raw_yaml)`）+ `parse_template`，回 JSON ok+summary 或 errors
- [ ] T041 [US1] 修改 `routes/templates.py` 新增 `POST /templates/save` 端點：先做 T040 同樣驗證，通過後 + 檢查 builtin 衝突 + 檢查 id 格式 → 呼叫 `registry.save_custom(tpl_dict)` → 200 redirect 到 `/templates/<id>`
- [ ] T042 [US1] 新增 `src/matcher/web/templates/template_authoring.html`：頁籤切換（兩個 `<details>`）、簡單模式表單骨架（基本資訊 + 屬性表格 + 規則卡 + 預設對象表 + prefs 區）、4 個 action 按鈕
- [ ] T043 [US1] 新增 `src/matcher/web/static/template_form.js`：clipboard 複製 + 動態增刪行（屬性表、規則卡、預設對象表）+ 「驗證」「儲存」按鈕透過 fetch 呼叫端點
- [ ] T044 [US1] 修改 `templates_list.html`：把現有 callout 改為 prominent「+ 新增模板」按鈕（指向 `/templates/new`）；列表卡片加「內建/自訂」badge
- [ ] T045 [US1] 執行 `uv run pytest tests/integration/test_template_authoring_simple.py tests/unit/test_template_form_assembly.py tests/unit/test_template_registry_custom_scan.py -q` 確認全綠

**Checkpoint US1 完成**：MVP 可從零建立自訂模板 + 跑通媒合。

---

## Phase 4 — User Story 2 (P2)：進階模式（YAML 編輯器 + AI prompt）

**Goal**：進階模式可貼 YAML + 複製完整 prompt + 驗證 + 儲存。

**Independent Test**：切到進階模式 → 填空 → 複製 prompt 到剪貼簿（驗證內容含整份 guide）→ 貼合法 YAML → 驗證 → 儲存。

### Tests (TDD — 先紅)

- [ ] T050 [P] [US2] 撰寫 `tests/integration/test_template_authoring_advanced.py::test_advanced_mode_renders_yaml_textarea` —— GET `/templates/new?mode=advanced` HTML 含 raw_yaml textarea + AI prompt 填空欄位
- [ ] T051 [P] [US2] 撰寫 `tests/integration/test_template_authoring_advanced.py::test_validate_accepts_raw_yaml_string` —— POST validate 帶 mode=advanced + raw_yaml=合法 YAML → ok:true
- [ ] T052 [P] [US2] 撰寫 `tests/integration/test_template_authoring_advanced.py::test_validate_returns_error_on_invalid_yaml_syntax` —— 語法錯的 YAML → ok:false + 訊息含「YAML 語法錯誤」
- [ ] T053 [P] [US2] 撰寫 `tests/integration/test_template_authoring_advanced.py::test_validate_returns_error_on_invalid_expr_operator` —— 用了非法 expr 算子（如 `gt`）→ ok:false + 訊息含「未知的規則表達式」
- [ ] T054 [P] [US2] 撰寫 `tests/integration/test_template_authoring_advanced.py::test_save_advanced_mode_persists_yaml_verbatim` —— 進階模式儲存的 YAML 內容與輸入完全一致（除了統一空白格式可能微調）

### Implementation

- [ ] T055 [US2] 在 `template_authoring.html` 加進階模式內容：上半 5 個填空 input（場景/角色/對象/規則/志願）+ 「複製完整 Prompt」按鈕；下半大 textarea（raw_yaml）
- [ ] T056 [US2] 在 `template_form.js` 加 `copyFullPrompt()` 函式：讀 `docs/template-authoring-guide.md` 內容（透過後端端點或預先嵌入）+ 填空欄位 → 組裝 prompt → clipboard API 複製
- [ ] T057 [US2] 新增 `GET /templates/authoring-guide.txt` 端點：直接回 `docs/template-authoring-guide.md` 文字內容；給前端 JS fetch 用
- [ ] T058 [US2] 修改 `POST /templates/validate` 與 `POST /templates/save` 對 `mode=advanced` 的處理分支：直接 `yaml.safe_load(raw_yaml)` → `parse_template`；錯誤捕獲分類（YAMLError vs ValueError）
- [ ] T059 [US2] 執行 `uv run pytest tests/integration/test_template_authoring_advanced.py -q` 確認全綠

---

## Phase 5 — User Story 3 (P3)：編輯既有模板 + 版本歷史 + Fork

**Goal**：自訂模板可編輯（產 v2、v3...）+ `/templates/<id>` 顯示版本歷史 + 內建模板可 Fork。

**Independent Test**：建 v1 → 編輯 → v2 → 查看版本歷史含兩版；teacher-class 點 Fork → 跳新增頁預填內容。

### Tests (TDD — 先紅)

- [ ] T060 [P] [US3] 撰寫 `tests/integration/test_template_editing_versions.py::test_custom_template_detail_shows_edit_button` —— GET `/templates/<custom-id>` HTML 含「編輯」按鈕；指向 `/templates/<id>/edit`
- [ ] T061 [P] [US3] 撰寫 `tests/integration/test_template_editing_versions.py::test_builtin_template_detail_shows_fork_button` —— GET `/templates/teacher-class` HTML 含「Fork 為自訂模板」按鈕；**不**含「編輯」
- [ ] T062 [P] [US3] 撰寫 `tests/integration/test_template_editing_versions.py::test_edit_page_preloads_latest_version` —— 寫 v1 + v2 後 GET `/templates/<id>/edit` 預填 v2 內容
- [ ] T063 [P] [US3] 撰寫 `tests/integration/test_template_editing_versions.py::test_save_existing_id_writes_v_next` —— 已有 v1 + v2 後再 save → 產生 v3.yaml；v1/v2 仍存在
- [ ] T064 [P] [US3] 撰寫 `tests/integration/test_template_editing_versions.py::test_version_history_section_lists_all_versions` —— GET `/templates/<id>` 含 v1 + v2 + v3 列表 + 各自時間
- [ ] T065 [P] [US3] 撰寫 `tests/integration/test_template_editing_versions.py::test_get_specific_version_returns_yaml_content` —— GET `/templates/<id>/versions/1` 回 text/yaml + v1 內容
- [ ] T066 [P] [US3] 撰寫 `tests/integration/test_template_editing_versions.py::test_fork_builtin_prefills_form_with_builtin_content` —— GET `/templates/new?fork=teacher-class` HTML 預填 teacher-class 屬性 + 規則；id 預填為 `teacher-class-fork`
- [ ] T067 [P] [US3] 撰寫 `tests/integration/test_template_editing_versions.py::test_edit_builtin_returns_403` —— GET `/templates/teacher-class/edit` 回 403 + 「內建模板不可編輯」
- [ ] T068 [P] [US3] 撰寫 `tests/integration/test_template_editing_versions.py::test_get_version_for_builtin_returns_404` —— GET `/templates/teacher-class/versions/1` 回 404

### Implementation

- [ ] T069 [US3] 修改 `routes/templates.py::template_detail` —— 注入 `is_builtin`、`versions`、`current_version` 到 context
- [ ] T070 [US3] 修改 `templates/template_detail.html` —— 自訂顯示「編輯」按鈕 + 「版本歷史」段（列出 v1..vN + 時間 + 查看連結）；內建顯示「Fork 為自訂模板」按鈕、不顯示版本段
- [ ] T071 [US3] 新增 `GET /templates/{id}/edit` 端點 —— 自訂模板載 v_max + 渲染 `template_edit.html`（重用 `template_authoring.html` 結構即可，加 `?edit_id=<id>` 預載）；內建 → 403
- [ ] T072 [US3] 新增 `GET /templates/{id}/versions/{version}` 端點 —— 自訂模板回 text/yaml；內建或版本不存在 → 404
- [ ] T073 [US3] 修改 `routes/templates.py::POST /templates/save` —— 偵測「edit 模式」（如 form 中含已存在 id 且 builtin=False）→ 寫 v(N+1)；新增「fork 模式」（form 中 fork_from 欄位）—— 預填內建內容後當新模板儲存
- [ ] T074 [US3] 在 `template_authoring.html` 加 fork 模式預填邏輯（jinja2 `{% if fork_template %}` 段，預填屬性/規則）+ id 預填為 `<fork_id>-fork`
- [ ] T075 [US3] 執行 `uv run pytest tests/integration/test_template_editing_versions.py -q` 確認全綠

---

## Phase 6 — User Story 4 (P4)：以此模板版本再執行

**Goal**：媒合紀錄頁加「以此版本再執行」按鈕；`/match/new?template_snapshot=<rid>` 從 audit.template_snapshot 還原為臨時模板。

**Independent Test**：對任一過去 record 點按鈕 → 跳 `/match/new` 預載 audit 中的模板版本 → 跑新一次。

### Tests (TDD — 先紅)

- [ ] T080 [P] [US4] 撰寫 `tests/integration/test_match_rerun_from_snapshot.py::test_match_result_has_rerun_button` —— 跑一次媒合後 GET `/match/<rid>` HTML 含「以此模板版本再執行」連結
- [ ] T081 [P] [US4] 撰寫 `tests/integration/test_match_rerun_from_snapshot.py::test_match_new_with_template_snapshot_param` —— GET `/match/new?template_snapshot=<rid>` 應 200 + HTML 含「已預載 audit 模板版本」提示
- [ ] T082 [P] [US4] 撰寫 `tests/integration/test_match_rerun_from_snapshot.py::test_match_new_snapshot_renders_dropdown_with_temp_template` —— 模板下拉應含 audit 中模板的 id（或臨時 id 含「snapshot」）
- [ ] T083 [P] [US4] 撰寫 `tests/integration/test_match_rerun_from_snapshot.py::test_match_new_snapshot_for_unknown_record_returns_404` —— `?template_snapshot=no-such-rid` → 404

### Implementation

- [ ] T084 [US4] 修改 `src/matcher/web/templates/match_result.html` —— 結果頁底部 action buttons 加 `<a href="/match/new?template_snapshot={{ record.id }}">以此模板版本再執行</a>`
- [ ] T085 [US4] 修改 `src/matcher/web/routes/match.py::new_match` —— 接受 `template_snapshot: str | None` query param；若提供，讀 record + 從 audit.template_snapshot 還原 Template + 傳入 context；新增提示「已預載 audit 模板版本」
- [ ] T086 [US4] 在 `new_match.html` 加 `{% if from_snapshot %}` 區塊顯示提示文字 + 模板下拉預選此臨時模板
- [ ] T087 [US4] 執行 `uv run pytest tests/integration/test_match_rerun_from_snapshot.py -q` 確認全綠

---

## Phase 7 — 通用驗證端點 + Polish

- [ ] T090 [P] 撰寫 `tests/integration/test_template_validation_endpoint.py::test_validate_simple_form_passes` —— 通用整合測試（簡單模式 ok）
- [ ] T091 [P] 撰寫 `tests/integration/test_template_validation_endpoint.py::test_validate_advanced_yaml_passes` —— 通用整合測試（進階模式 ok）
- [ ] T092 [P] 撰寫 `tests/integration/test_template_validation_endpoint.py::test_no_technical_tokens_in_auto_descriptions` —— 5 種規則類型自動生成的 description 通過 FORBIDDEN_TECHNICAL_TOKENS 正則
- [ ] T093 [P] 規模測試：撰寫 `tests/unit/test_template_registry_custom_scan.py::test_scan_100_custom_templates_under_500ms` —— 寫 100 個自訂模板 → measure `TemplateRegistry()` 啟動時間 ≤ 500ms（SC effort baseline）
- [ ] T094 [P] 執行完整測試 `uv run pytest -q` —— 既有 281 + 新增 ≥ 15 全綠（預期 ≥ 296）
- [ ] T095 [P] 依 quickstart.md 10 個步驟在瀏覽器手動驗收一次（含重啟 server 驗證 SC-003）
- [ ] T096 修改 `README.md`「Web UI」段「PDF 報告」子段下加「自訂模板創作」段（≤ 5 行說明）
- [ ] T097 修改 `templates_list.html` 把舊 callout 文字更新為 prominent button（如 Phase 3 T044 未完整覆蓋的部分）
- [ ] T098 確認 `git status` 僅含預期變動：核心限 `template_loader.py` + 其他 Web 層 + spec + 測試 + README + `data/templates/.gitkeep`

---

## Dependencies

```
Phase 1 (Setup) ─→ Phase 2 (Foundational) ─→ Phase 3 (US1 MVP) ─┬→ Phase 4 (US2)
                                                                 ├→ Phase 5 (US3)
                                                                 └→ Phase 6 (US4)
                                                                            ↓
                                                                  Phase 7 (Polish)
```

- US2、US3、US4 在 US1 後可**並行**進行（不同檔/不同樣板段）
- Phase 2 完成後即可獨立測 TemplateRegistry 與 form 組裝邏輯（無 UI）

## Parallel Execution Examples

**Phase 2 測試批次**：T010-T020 全部 [P]（單元測試獨立檔案/函式）。

**Phase 2 實作**：
- T021 → T022 → T023 → T024 同檔序列
- T025 → T026 同檔序列
- T021/T025 不同檔可 [P]

**Phase 3 測試批次**：T030-T038 全部 [P]。

**Phase 3 實作**：
- T039 → T040 → T041 同檔序列
- T042（HTML）+ T043（JS）+ T044（HTML 模板列表）可 [P]

**Phase 4-6 各自內部測試批次**：全部 [P]。

**Phase 7**：T090-T095 全部 [P]；T096-T098 序列收尾。

## Implementation Strategy

**MVP**：Phase 1 + Phase 2 + Phase 3（US1）—— 約 27 個任務、估 8-12 小時。完成後即可從零建立自訂模板 + 跑通媒合。

**v2 增量**：Phase 4（US2）—— 進階 YAML 模式 + AI prompt，估 2-3 小時。

**v3 增量**：Phase 5（US3）—— 編輯 + 版本歷史 + Fork，估 4-5 小時（本 feature 最複雜的 UI 工作）。

**v4 增量**：Phase 6（US4）—— audit-snapshot 再執行，估 1-2 小時（大部分功能 audit 已有）。

**收斂**：Phase 7—— 通用驗證 + 規模測試 + 文件，估 1-2 小時。

**總計**：~50 個任務、新增 ≥ 25 個自動化測試（遠超 SC-008 的 ≥ 15 門檻）、估 16-25 小時（spec-kit 系列最大 feature）。

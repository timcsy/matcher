# Tasks: Web UI 直接填名單

**Feature**: 012-web-roster-form
**Branch**: `012-web-roster-form`
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

**TDD 強制**（constitution I）：每個 user story 內，測試任務 MUST 先寫並先紅後再實作。

> **核心 0 改動硬約束**：所有變動限 `src/matcher/web/`。FR-010 / SC-006 由 git diff 守住。

---

## Phase 1 — Setup（無）

無新依賴、無新檔案夾、無 CI 變更。略過。

---

## Phase 2 — Foundational

阻塞所有 user stories 的共用變更：純函式 + `/match/new` 三選一入口。

### Tests (TDD — 先紅)

- [ ] T001 [P] 撰寫 `tests/unit/test_roster_form_assemble.py::test_assemble_roster_csv_basic` —— 表單 dict（3 位角色 × 3 屬性）→ `assemble_roster_csv_bytes(form, tpl)` 回 utf-8 bytes，可被 `csv.DictReader` 解析；header 含 id + 範本宣告 keys
- [ ] T002 [P] 撰寫 `tests/unit/test_roster_form_assemble.py::test_assemble_roster_csv_filters_empty_rows` —— 含 2 空白行的 form → 自動過濾、輸出只有非空行
- [ ] T003 [P] 撰寫 `tests/unit/test_roster_form_assemble.py::test_assemble_roster_csv_byte_equiv_with_csv_path` —— UI 表單組的 CSV bytes 經 `load_roster_csv` 載入後，與「同樣資料以 CSV 上傳」載出的 Roster bytewise 相等（assignment / qualified_set / filter_trace / allocation_trace / template_snapshot 五段）
- [ ] T004 [P] 撰寫 `tests/unit/test_roster_form_assemble.py::test_assemble_targets_yaml_returns_none_when_default_targets_exists` —— 範本有 default_targets → 函式回 None
- [ ] T005 [P] 撰寫 `tests/unit/test_roster_form_assemble.py::test_assemble_targets_yaml_basic` —— UI 對象段 2 個對象 × 3 屬性 → YAML bytes，可被 `yaml.safe_load` 解析含 `targets:` key

### Implementation

- [ ] T006 新增 `src/matcher/web/roster_form.py`：含 `assemble_roster_csv_bytes(form: dict, template) -> bytes` + `assemble_targets_yaml_bytes(form: dict, template) -> bytes | None` 兩個純函式（沿用 feature 011 `_collect_indexed_rows` 蒐集邏輯）
- [ ] T007 修改 `src/matcher/web/templates/new_match.html`：把現有 form 包入 Alpine `x-data="{ mode: 'upload' }"`，加三選一 radio（上傳 / 直接填 / 從紀錄）；mode=fill 顯示「選範本 + 開始填寫」段；mode=upload 顯示既有上傳 form；from-record 為連結
- [ ] T008 確認 T001-T005 由紅轉綠（`uv run pytest tests/unit/test_roster_form_assemble.py -q`）

**Checkpoint**：純函式就緒；`/match/new` 三選一可切換顯隱。

---

## Phase 3 — User Story 1 (P1) 🎯 MVP：UI 填角色名單跑通

**Goal**：`/match/new/fill?template_id=X` 填寫頁可填角色 → 跑通 M0 → Web/CSV bytewise 等價。

**Independent Test**：選 teacher-class + 填 7 位老師 + M0 → 結果頁正常；audit 與 CSV 上傳路徑 5 段 bytewise 相等。

### Tests (TDD — 先紅)

- [ ] T010 [P] [US1] 撰寫 `tests/integration/test_web_roster_fill_basic.py::test_fill_page_renders_role_attrs_from_template` —— GET `/match/new/fill?template_id=teacher-class` 200 + HTML 含「姓名」「老師專業科目」「年資（年）」三欄標籤 + 「＋ 新增一位」按鈕
- [ ] T011 [P] [US1] 撰寫 `tests/integration/test_web_roster_fill_basic.py::test_fill_page_404_on_unknown_template` —— `?template_id=nope` → 404
- [ ] T012 [P] [US1] 撰寫 `tests/integration/test_web_roster_fill_basic.py::test_post_run_from_form_m0_succeeds` —— POST `/match/run-from-form` 帶 3 位角色 + M0 + seed → 303 重導 `/match/{rid}` + audit.mechanism="M0" + 3 位都被分配
- [ ] T013 [P] [US1] 撰寫 `tests/integration/test_web_roster_fill_basic.py::test_post_run_from_form_audit_bytewise_equals_csv_path` —— 同樣 7 位資料：(a) POST run-from-form (b) CLI runner --roster-csv → 比對 5 段 bytewise 相等
- [ ] T014 [P] [US1] 撰寫 `tests/integration/test_web_roster_fill_basic.py::test_post_run_from_form_filters_empty_rows` —— POST 含 3 位實際資料 + 7 空白行 → 5 段 audit 與「只填 3 位的 CSV」等價
- [ ] T015 [P] [US1] 撰寫 `tests/integration/test_web_roster_fill_basic.py::test_post_run_from_form_requires_at_least_one_role` —— POST 全空角色 → 400 + 「請至少填一位」訊息
- [ ] T016 [P] [US1] 撰寫 `tests/integration/test_web_roster_fill_basic.py::test_new_match_page_has_three_modes` —— GET `/match/new` HTML 含「上傳名單檔」「直接填名單」「從過去紀錄」三項

### Implementation

- [ ] T017 [US1] 修改 `src/matcher/web/routes/match.py` 新增 `GET /match/new/fill` 端點：取 template 後組 context（template、role_attrs、target_attrs、requires_targets、has_prefs_schema、mechanisms）→ render `roster_form_fill.html`；template_id 不存在 → 404
- [ ] T018 [US1] 修改 `routes/match.py` 新增 `POST /match/run-from-form` 端點：(a) 驗證 mechanism、seed、template_id；(b) 呼叫 `assemble_roster_csv_bytes` + 可選 `assemble_targets_yaml_bytes`；(c) 寫 tempfile + sidecar；(d) `load_roster_csv` 載入；(e) M0 → run_match → record → redirect；(f) M1/M2 + prefs_schema → render preferences_form.html (feature 009 既有頁) 含 hidden inputs（暫時直接 render；US3 完整接續測試）
- [ ] T019 [US1] 新增 `src/matcher/web/templates/roster_form_fill.html`：Tailwind + Alpine；含
  - 範本資訊（name + description）+ 「亂數種子」+「抽籤方式」下拉
  - 「① 角色清單」段：依 `role_attrs` 動態渲染每列輸入（含 id 欄 + 每個 attribute key 一欄 + × 移除）；初始 2 列 + 「＋ 新增一位」按鈕
  - 條件渲染「② 對象清單」段：`{% if requires_targets %}`（為 US2 預備；本 US1 路徑下 hidden）
  - 「執行配對」按鈕（POST 到 `/match/run-from-form`）
- [ ] T020 [US1] 新增 `src/matcher/web/static/roster_form.js`（或 inline 在 roster_form_fill.html）：Alpine 元件 `rosterForm()`，state 含 `roles: []`、`targets: []`；方法 `addRole()` / `removeRole(i)` / `addTarget()` / `removeTarget(i)`
- [ ] T021 [US1] 執行 `uv run pytest tests/integration/test_web_roster_fill_basic.py tests/unit/test_roster_form_assemble.py -q` 確認全綠

**Checkpoint US1 完成**：MVP 可用 UI 填名單跑 M0；Web/CSV 等價守住。

---

## Phase 4 — User Story 2 (P2)：自訂範本無 default_targets 時 UI 填對象

**Goal**：範本無 `default_targets` 時，填寫頁顯示「② 對象清單」段；UI 上填的對象也走完整 pipeline。

**Independent Test**：建一個無 default_targets 的自訂範本 → 填寫頁兩段都顯示 → 填 5 角色 + 3 對象 → M0 跑通。

### Tests (TDD — 先紅)

- [ ] T030 [P] [US2] 撰寫 `tests/integration/test_web_roster_fill_targets.py::test_fill_page_hides_targets_section_when_default_targets_exists` —— GET `/match/new/fill?template_id=teacher-class`（有 default_targets）→ HTML **不**含「② 對象清單」段（或該段標題不可見）
- [ ] T031 [P] [US2] 撰寫 `tests/integration/test_web_roster_fill_targets.py::test_fill_page_shows_targets_section_for_custom_template_without_default_targets` —— 預先建一個無 default_targets 的自訂範本 → 訪問 fill 頁 → HTML 含「② 對象清單」+ 依範本對象屬性的欄位
- [ ] T032 [P] [US2] 撰寫 `tests/integration/test_web_roster_fill_targets.py::test_post_run_from_form_with_ui_targets_succeeds` —— POST 含 5 角色 + 3 對象 + M0 → 跑通；audit.roster_snapshot.targets 含此 3 對象

### Implementation

- [ ] T033 [US2] 在 `roster_form_fill.html` 對「② 對象清單」段 `{% if requires_targets %}` 條件啟用；段內動態渲染 + 加減行（沿用 US1 的 Alpine pattern）
- [ ] T034 [US2] `routes/match.py::POST /match/run-from-form` 內呼叫 `assemble_targets_yaml_bytes`，若回非 None → 寫 sidecar yaml 到 tempfile；data_import 會自動撈到
- [ ] T035 [US2] 執行 `uv run pytest tests/integration/test_web_roster_fill_targets.py -q` 確認全綠

---

## Phase 5 — User Story 3 (P3)：M1/M2 銜接 feature 009 填志願頁

**Goal**：範本有 `preferences_schema` + 使用者選 M1/M2 → 跳 `/match/preferences` 頁（feature 009 既有）。

**Independent Test**：選有 prefs 的範本 + UI 填名單 + M1 → 跳到填志願頁 + hidden inputs 已預載。

### Tests (TDD — 先紅)

- [ ] T040 [P] [US3] 撰寫 `tests/integration/test_web_roster_fill_m1_handoff.py::test_m1_with_prefs_template_renders_preferences_form` —— POST `/match/run-from-form` 含名單 + M1 + 範本有 prefs schema → 200 + HTML 為填志願頁（含「填寫志願」標題）+ hidden inputs 含 `roster_bytes_b64`
- [ ] T041 [P] [US3] 撰寫 `tests/integration/test_web_roster_fill_m1_handoff.py::test_m2_with_prefs_template_renders_preferences_form` —— 同上 M2
- [ ] T042 [P] [US3] 撰寫 `tests/integration/test_web_roster_fill_m1_handoff.py::test_m1_without_prefs_template_falls_back_to_failed_record` —— 範本無 prefs schema + M1 → 直接走 pipeline → 失敗 record (MechanismRequiresPreferences)
- [ ] T043 [P] [US3] 撰寫 `tests/integration/test_web_roster_fill_m1_handoff.py::test_handed_off_form_can_submit_preferences_and_run_match` —— 完整端到端：UI 填名單 + M1 → 跳填志願頁 → POST `/match/preferences` 含志願 → 跑通

### Implementation

- [ ] T044 [US3] `routes/match.py::POST /match/run-from-form` 內加分支：mechanism in (M1, M2) AND template.preferences_schema → 直接 render `preferences_form.html`（feature 009 既有樣板），傳入 hidden input 值（template_id、mechanism、seed、roster_bytes_b64、roster_filename、targets_bytes_b64？——若有對象 sidecar 也須攜帶）
- [ ] T045 [US3] 確認 `preferences_form.html` 與 `POST /match/preferences` 對 sidecar targets 的處理路徑——若 UI-filled 路徑帶有 targets sidecar，preferences 提交時也要寫 sidecar
- [ ] T046 [US3] 執行 `uv run pytest tests/integration/test_web_roster_fill_m1_handoff.py -q` 確認全綠

---

## Phase 6 — Polish

- [ ] T050 [P] 撰寫 `tests/integration/test_web_roster_fill_basic.py::test_fill_page_no_technical_tokens` —— 填寫頁 HTML 不含 `preference_rank`、`filter_trace` 等技術 token（沿用清單）
- [ ] T051 [P] 撰寫 `tests/integration/test_web_roster_fill_basic.py::test_25_roles_render_and_submit` —— 規模測試：25 位角色 → 跑通
- [ ] T052 [P] 執行完整測試 `uv run pytest -q` —— 既有 322 + 新增 ≥ 10 全綠（預期 ≥ 332）
- [ ] T053 [P] 確認核心 0 改動：`git diff --stat main..HEAD src/matcher/ | grep -v 'src/matcher/web/'` 為空
- [ ] T054 [P] 依 quickstart.md 8 步驟在瀏覽器手動驗收（含 Web/CSV 等價對比、25 角色規模、M1 銜接）
- [ ] T055 確認 `git status` 僅含預期變動：`routes/match.py + roster_form.py + 2 個 template html + 1 個 JS + 3 個 test 檔 + spec/*`

---

## Dependencies

```
Phase 2 (Foundational) ─→ Phase 3 (US1 MVP) ─┬→ Phase 4 (US2)
                                              └→ Phase 5 (US3)

Phase 3-5 → Phase 6 (Polish)
```

- US2 / US3 在 US1 後可並行（不同 user story 不同檔/不同段）

## Parallel Execution Examples

**Phase 2 測試批次**：T001-T005 全部 [P]（同檔不同函式，pytest 並行）。

**Phase 3 測試批次**：T010-T016 全部 [P]。

**Phase 3 實作**：T017 → T018 同檔序列；T019（HTML 樣板）+ T020（JS）可 [P]。

**Phase 4-5 各自內部測試**：批次 [P]。

**Phase 6**：T050-T054 全部 [P]；T055 序列收尾。

## Implementation Strategy

**MVP**：Phase 2 + Phase 3（US1）—— 約 15 個任務、估 4-6 小時。完成後 UI 填名單跑 M0 端到端可用。

**v2 增量**：Phase 4（US2）—— 3 任務、估 1.5 小時（自訂範本無 default_targets 時填對象）。

**v3 增量**：Phase 5（US3）—— 4 任務、估 1.5 小時（M1/M2 銜接 feature 009）。

**收斂**：Phase 6 polish —— 估 30 分鐘。

**總計**：~28 個任務、新增 ≥ 14 個自動化測試（超過 SC-008 的 ≥ 10 門檻）、估 7-10 小時。

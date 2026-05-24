# Tasks: Web UI 動態填志願表單

**Feature**: 009-web-preferences-form
**Branch**: `009-web-preferences-form`
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

**TDD 強制**（constitution I）：每個 user story 內，測試任務 MUST 先寫並先紅後再實作。

> **欄位名稱**：實際 routes 使用 `template_id`、`roster`、`seed`、`mechanism`（沿用 008）；新增 form 欄位 `pref_<role_id>_<rank>`、`roster_bytes_b64`、`roster_filename`、`_action`。

---

## Phase 1 — Setup（無）

無新依賴、無新檔案夾、無 CI 變更。略過。

---

## Phase 2 — Foundational

阻塞所有 user stories 的共用變更——`/match/run` 偵測分支邏輯 + 新樣板骨架 + humanize 工具函式。

- [ ] T001 [P] 撰寫 `tests/unit/test_humanize_target_summary.py::test_target_summary_basic` —— `target_summary({"id":"G1","name":"程式組","capacity":3}) == "程式組（容量 3 人）"`；無 name fallback 用 id；無 capacity 則只顯示名
- [ ] T002 [P] 撰寫 `tests/integration/test_web_preferences_form_flow.py::test_post_run_with_empty_prefs_m1_renders_preferences_form` —— TestClient POST `/match/run` 帶 study-group + 無 prefs CSV + M1，預期 200 + HTML 含「填寫志願」標題 + 表格列出 9 學生
- [ ] T003 在 `src/matcher/web/humanize.py` 新增 `target_summary(target: dict) -> str` 純函式（含 name fallback、capacity 缺省）
- [ ] T004 新增 `src/matcher/web/templates/preferences_form.html` 樣板骨架 — 含 `{% block content %}`、「填寫志願」標題、`{% if targets_for_options %}` 條件渲染、hidden inputs 5 個（template_id/mechanism/seed/roster_bytes_b64/roster_filename）、tbody/thead 表格與 `<select>` 迴圈、「確認執行」與「跳過此步驟」兩個 submit button（`name="_action"`）、「離開不會儲存」提示段
- [ ] T005 修改 `src/matcher/web/routes/match.py::run` — 在 data_import 解析後、`run_match` 之前加入「跳填志願頁」判斷：
  - 若 (tpl.preferences_schema is not None) AND (all role.preferences == () for roles) AND (mechanism in {"M1","M2"})
  - → base64 encode `data`（upload bytes）+ 組 PreferencesFormViewModel context + render `preferences_form.html`（status 200）
  - 否則維持 008 既有路徑
- [ ] T006 驗證 T001-T002 由紅轉綠（執行 `uv run pytest tests/unit/test_humanize_target_summary.py tests/integration/test_web_preferences_form_flow.py::test_post_run_with_empty_prefs_m1_renders_preferences_form -q`）

**Checkpoint**：上傳全空 prefs + M1 會跳到填志願頁；尚無「送出填志願」端點。

---

## Phase 3 — User Story 1 (P1) 🎯 MVP：行政在 UI 上替學生填志願

**Goal**：完成填志願頁的 POST 端點、表單志願組裝為 `Role.preferences`、走既有 pipeline、Web/CSV bytewise 等價。

**Independent Test**：上傳全空 prefs CSV + M1 → 跳填志願頁 → 填完 → 結果頁顯示 M1 處理順序與志願排名；下載 audit 與 CSV preferences 欄路徑跑出的 audit 五段相同。

### Tests (TDD — 先紅)

- [ ] T010 [P] [US1] 撰寫 `tests/integration/test_web_preferences_form_flow.py::test_preferences_form_lists_roles_and_targets` —— GET 後的 HTML 含 9 學生 id + `<select name="pref_S01_1">` 等動態欄位（共 9×3=27 個）+ 候選對象段「程式組（容量 3 人）」
- [ ] T011 [P] [US1] 撰寫 `tests/integration/test_web_preferences_form_flow.py::test_post_preferences_with_valid_choices_succeeds` —— 模擬填志願 POST `/match/preferences`，預期 303 重導 + 結果頁 audit.mechanism=="M1" + audit.allocation_trace 含 preference_rank 1
- [ ] T012 [P] [US1] 撰寫 `tests/integration/test_web_preferences_form_flow.py::test_web_csv_audit_bytewise_equal` —— 同樣 seed + 同樣志願；一邊 POST `/match/preferences`、另一邊 POST `/match/run` 走含 prefs CSV，比對 audit 五段 bytewise 相等
- [ ] T013 [P] [US1] 撰寫 `tests/integration/test_web_preferences_form_flow.py::test_preferences_form_csv_with_partial_prefs_uses_skip_path` —— roster.csv 內**至少一位** role 已有 prefs → POST `/match/run` 不跳填志願頁、直接執行（既有 008 路徑）
- [ ] T014 [P] [US1] 撰寫 `tests/integration/test_web_preferences_form_flow.py::test_preferences_form_hidden_inputs_round_trip` —— 確認 hidden inputs 含正確 base64 + filename + mechanism + seed；POST 時這些值能正確解碼還原

### Implementation

- [ ] T015 [US1] 在 `src/matcher/web/routes/match.py` 新增 `POST /match/preferences` 端點 — `await request.form()` 拿全部欄位；hidden inputs 缺失 → 400 error_page.html；解 base64 → tmp file → 重跑 data_import（同 csv/xlsx 判斷邏輯）
- [ ] T016 [US1] 在 `POST /match/preferences` 內 `_action="submit"` 分支：迴圈 `roster.roles`，為每個 role 蒐集 `pref_<role_id>_1..max_choices` 非空值；用 `dataclasses.replace(role, preferences=tuple(prefs))` 重組；用 `dataclasses.replace(roster, roles=tuple(new_roles))` 重組
- [ ] T017 [US1] `POST /match/preferences` 通過後執行 `run_match(MatcherInput(...))`，沿用既有 `MatcherError` 捕獲與 record 寫入；303 重導 `/match/{rid}`
- [ ] T018 [US1] 修改 `src/matcher/web/templates/preferences_form.html` — 為 `roles_for_form` 每列 render `<select name="pref_{role_id}_{rank}">`；選項為 `targets_for_options`（含「（未選）」第一項）；含 `{% if previous_form_values %}` 預填 selected
- [ ] T019 [US1] 執行 `uv run pytest tests/integration/test_web_preferences_form_flow.py tests/unit/test_humanize_target_summary.py -q` 確認全綠

**Parallel batch**：T010-T014 全部 [P]；T015-T017 同檔序列；T018 與其他樣板無交集可 [P]。

**Checkpoint US1 完成**：MVP 可端到端從上傳 → 填志願 → 結果頁全跑通；Web/CSV 等價守住。

---

## Phase 4 — User Story 2 (P2)：跳過填志願表單（escape hatch）+ 路徑判定

**Goal**：「跳過」按鈕沿用 MechanismRequiresPreferences 失敗路徑；各種路徑判定條件正確。

**Independent Test**：填志願頁 → 點「跳過」→ 失敗結果頁顯示 M1/M2 訊息；含 prefs CSV / M0 路徑不跳頁。

### Tests (TDD — 先紅)

- [ ] T020 [P] [US2] 撰寫 `tests/integration/test_web_preferences_form_skip.py::test_skip_button_triggers_mechanism_requires_preferences_m1` —— POST `/match/preferences` 帶 `_action=skip` + M1，預期 303 + 結果頁 status=failed + 「M1 需要至少一位角色提供志願」
- [ ] T021 [P] [US2] 撰寫 `tests/integration/test_web_preferences_form_skip.py::test_skip_button_m2_message` —— 同上但 M2，訊息「M2 需要至少一位角色提供志願」
- [ ] T022 [P] [US2] 撰寫 `tests/integration/test_web_preferences_form_skip.py::test_m0_with_empty_prefs_does_not_jump_to_form` —— POST `/match/run` 帶 study-group + 無 prefs + M0 → 不跳填志願頁、直接 M0 成功
- [ ] T023 [P] [US2] 撰寫 `tests/integration/test_web_preferences_form_skip.py::test_teacher_class_template_does_not_jump_to_form` —— POST `/match/run` 帶 teacher-class（無 preferences_schema）+ M1 → 不跳填志願頁、走既有 pipeline reject 路徑（exit 17/40）

### Implementation

- [ ] T024 [US2] 在 `POST /match/preferences` 新增 `_action="skip"` 分支：以**未動的 roster**（preferences 全空）執行 `run_match`，沿用 MatcherError 捕獲（M1/M2 必失敗）；303 重導 `/match/{rid}`
- [ ] T025 [US2] 驗證 T005（route dispatch decision）的 3 個非跳頁條件正確：(a) template.preferences_schema is None、(b) any role.preferences、(c) mechanism == "M0"；補強或新增單元測試
- [ ] T026 [US2] 執行 `uv run pytest tests/integration/test_web_preferences_form_skip.py -q` 確認全綠

**Checkpoint US2 完成**：escape hatch 正確、路徑分流明確。

---

## Phase 5 — User Story 3 (P3)：填志願 UI 的透明度 + 驗證 + 邊界

**Goal**：候選對象顯示、技術詞零容忍、表單驗證（同列重複/全空/無 default_targets）、規模測試。

**Independent Test**：填志願頁 HTML 通過技術詞正則；同列重複被擋；無 default_targets 顯示明確錯誤。

### Tests (TDD — 先紅)

- [ ] T030 [P] [US3] 撰寫 `tests/integration/test_web_preferences_form_validation.py::test_no_technical_tokens_in_preferences_form` —— 填志願頁 HTML 不含 `default_targets`、`preferences_schema`、`max_choices`、`preference_rank`、`preferred_order`
- [ ] T031 [P] [US3] 撰寫 `tests/integration/test_web_preferences_form_validation.py::test_post_preferences_rejects_duplicate_in_same_row` —— POST 含 `pref_S01_1=G1` + `pref_S01_2=G1` → 200 + 回填志願頁 + 「同列不可重複選同對象」訊息
- [ ] T032 [P] [US3] 撰寫 `tests/integration/test_web_preferences_form_validation.py::test_post_preferences_rejects_unknown_target_id` —— POST 含 `pref_S01_1=G99`（不在 default_targets）→ 400 或 200 + 錯誤訊息「選了無效的對象」
- [ ] T033 [P] [US3] 撰寫 `tests/integration/test_web_preferences_form_validation.py::test_post_preferences_all_empty_redirects_to_skip_path` —— 所有 `pref_*` 皆空字串 + `_action=submit` → 沿用 skip 路徑（顯示 MechanismRequiresPreferences 失敗）或回填志願頁顯示「至少一位角色須填」（依 plan 決定，testable）
- [ ] T034 [P] [US3] 撰寫 `tests/integration/test_web_preferences_form_validation.py::test_template_without_default_targets_shows_friendly_error` —— 構造臨時模板（或 monkey-patch）含 schema 但無 default_targets + 全空 roster + M1 → 填志願頁顯示「請在 CSV preferences 欄填寫」+ 「回到上一步」
- [ ] T035 [P] [US3] 撰寫 `tests/integration/test_web_preferences_form_validation.py::test_preferences_form_shows_target_summary_with_capacity` —— HTML 含「程式組（容量 3 人）」「自然組（容量 3 人）」「人文組（容量 3 人）」

### Implementation

- [ ] T036 [US3] 修改 `POST /match/preferences` 加入驗證：同列重複（set vs list 長度比較）、unknown id（target id 不在白名單）→ 回填志願頁 + `form_errors` context
- [ ] T037 [US3] 修改 `preferences_form.html` — 加 `{% if form_errors %}` 紅字段；加 `{% if not targets_for_options %}` 顯示 FR-009 錯誤段 + 「回到上一步」按鈕
- [ ] T038 [US3] 修改 `routes/match.py::run` 跳填志願頁分支內，準備 `targets_for_options`：若 `template.default_targets` 為空 tuple → `targets_for_options=None` 讓樣板渲染錯誤段；否則用 `target_summary` 組 list
- [ ] T039 [US3] 執行 `uv run pytest tests/integration/test_web_preferences_form_validation.py -q` 確認全綠

---

## Phase 6 — 規模測試 + Polish

- [ ] T050 [P] 撰寫 `tests/integration/test_web_preferences_form_scale.py::test_50_students_3_choices_renders_and_submits` —— 構造 50 學生 CSV → 跳填志願頁 → HTML 含 150 個 `<select>` → 模擬全部填志願 → POST 成功 → 結果頁 audit.mechanism=="M1"（SC-007）
- [ ] T051 [P] 執行完整測試 `uv run pytest -q` —— 既有 234 + 新增 ≥ 10 全綠（預期 ≥ 244）
- [ ] T052 [P] 依 quickstart.md 9 個步驟在瀏覽器手動驗收一次
- [ ] T053 修改 `README.md` 在「Web UI」段落補一段「填志願表單自動跳轉」說明（≤ 5 行）
- [ ] T054 確認 `git status` 僅含預期變動（`src/matcher/web/{routes/match.py, humanize.py, templates/preferences_form.html}` + 5 個新測試檔 + `specs/009-*/*` + `README.md`）

---

## Dependencies

```
Phase 2 (Foundational) ─→ Phase 3 (US1, MVP) ─┬→ Phase 4 (US2)
                                              └→ Phase 5 (US3)

Phase 3, 4, 5 → Phase 6 (Polish)
```

- US2 與 US3 在 US1 完成後可並行（兩者修改 `POST /match/preferences` 不同分支與不同樣板段）
- US2 主要在 routes 層；US3 主要在樣板層 + 驗證邏輯

## Parallel Execution Examples

**Phase 2 測試批次**：T001 T002 [P]；T003 T004 [P]（不同檔）；T005 序列在 T003-T004 之後（依賴樣板存在）。

**Phase 3 測試批次**：T010 T011 T012 T013 T014 全部 [P]——皆為同檔不同函式（pytest 可並行收集）。

**Phase 3 實作分組**：
- 批 A：T015 → T016 → T017（同檔，序列）
- 批 B [P]：T018（樣板，不同檔）

**Phase 5 測試批次**：T030 T031 T032 T033 T034 T035 全部 [P]。

**Phase 5 實作**：T036 T037 T038 序列（同 routes/templates 連動）。

**Phase 6**：T050 T051 T052 全部 [P]；T053 T054 序列收尾。

## Implementation Strategy

**MVP**：Phase 2 + Phase 3（US1）——約 14 個任務、估 5-7 小時。完成後即可端到端 demo「上傳全空 CSV → 跳填志願頁 → 填完 → 結果」，**符合最大價值**。

**v2 增量**：Phase 4（US2）——escape hatch + 路徑分流，估 1-2 小時。

**v3 增量**：Phase 5（US3）——透明度與驗證，估 2-3 小時。

**收斂**：Phase 6——規模測試與 polish，估 1 小時。

**總計**：~28 個任務、新增 ≥ 16 個自動化測試（超過 SC-010 的 ≥ 10 門檻 60%）、估 9-13 小時。

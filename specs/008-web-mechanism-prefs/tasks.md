# Tasks: Web UI 機制選擇 + 結果頁志願展示

**Feature**: 008-web-mechanism-prefs
**Branch**: `008-web-mechanism-prefs`
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

**TDD 強制**（constitution I）：每個 user story 內，測試任務 MUST 先寫並先紅後再實作。

> **欄位名稱對齊**：實際 routes 使用 `template_id`（非 template_name）、`roster`（非 roster_file）；seed 既有為 `Form(...)`（必填，沿用）；以下任務以真實名稱描述。

---

## Phase 1 — Setup（無）

本 feature 無新依賴、無新檔案結構、無 CI 變更。Setup phase 略過。

---

## Phase 2 — Foundational（共用基礎）

阻塞所有 user stories 的共用變更——主要是 routes/match.py 的 mechanism 表單接收與 pipeline 串接。

- [ ] T001 [P] 撰寫 `tests/integration/test_web_mechanism_form.py::test_match_run_accepts_mechanism_m0` —— TestClient POST `/match/run` 帶 `mechanism=M0` + teacher-class + roster.yaml，預期 303 重導到 `/match/{rid}` 且 record audit.mechanism == "M0"
- [ ] T002 [P] 撰寫 `tests/integration/test_web_mechanism_form.py::test_match_run_rejects_invalid_mechanism` —— TestClient POST `mechanism=M9`，預期 400 + 訊息「不支援的機制」
- [ ] T003 [P] 撰寫 `tests/integration/test_web_mechanism_form.py::test_match_run_normalizes_lowercase` —— POST `mechanism=m1` 與 study-group + roster-m1.csv，預期成功，audit.mechanism == "M1"
- [ ] T004 修改 `src/matcher/web/routes/match.py::run` —— 新增 `mechanism: str = Form("M0")` 參數；接收後 `.strip().upper()` 並白名單驗證；非法值 raise HTTPException(400, "不支援的機制：{x}（請選 M0、M1、M2）")；將驗證後值傳給 `MatcherInput(mechanism=...)` 與 `common dict mechanism=...`，**移除既有兩處硬編碼的 `"M0"`**
- [ ] T005 修改 `src/matcher/web/routes/match.py::new_match` —— 新增 `MECHANISMS` 模組級常數（list of tuple）與 `default_mechanism="M0"` 注入 template context
- [ ] T006 驗證 T001-T003 由紅轉綠（執行 `uv run pytest tests/integration/test_web_mechanism_form.py -q`）

**Checkpoint**：Web 層可正確接收三機制；無 UI、無結果頁變化。

---

## Phase 3 — User Story 1 (P1) 🎯 MVP：行政在 Web 上選機制跑 M1/M2

**Goal**：表單下拉、結果頁機制名稱、處理順序段、志願排名欄齊備；Web/CLI 同 seed bytewise 等價。

**Independent Test**：Web 選 study-group + roster-m1.csv + seed=2026 + M2 → 結果頁顯示三項新增區塊；下載 audit 與 CLI 同樣輸入跑出的 audit 五段相同。

### Tests (TDD — 先紅)

- [ ] T010 [P] [US1] 撰寫 `tests/integration/test_web_mechanism_form.py::test_new_match_form_has_mechanism_select` —— GET `/match/new`，HTML 含 3 個 `<option value="M0|M1|M2">`，M0 為 selected
- [ ] T011 [P] [US1] 撰寫 `tests/integration/test_web_mechanism_form.py::test_result_page_shows_mechanism_label_m2` —— 跑 M2 後 GET `/match/{rid}`，HTML 含「M2 Boston 層級填滿」
- [ ] T012 [P] [US1] 撰寫 `tests/integration/test_web_mechanism_form.py::test_result_page_shows_processing_order_m1m2` —— M1/M2 路徑頁面含「處理順序」段；M0 路徑**不**含
- [ ] T013 [P] [US1] 撰寫 `tests/integration/test_web_mechanism_form.py::test_result_page_shows_preference_rank_column` —— M2 跑出後頁面表格含「志願排名」欄位 + 內容含「第 1 志願」或「抽籤」；M0 路徑**不**含此欄
- [ ] T014 [P] [US1] 撰寫 `tests/integration/test_web_cli_audit_equivalence.py::test_web_cli_m1_bytewise_equal` —— CLI 與 Web 同 study-group + roster-m1.csv + seed=2026 + M1，比對 audit 五段（qualified_set/assignment/filter_trace/allocation_trace/template_snapshot）逐位元組相等
- [ ] T015 [P] [US1] 撰寫 `tests/integration/test_web_cli_audit_equivalence.py::test_web_cli_m2_bytewise_equal` —— 同上但 M2
- [ ] T016 [P] [US1] 撰寫 `tests/integration/test_web_mechanism_form.py::test_no_technical_tokens_in_result_html` —— 結果頁 HTML 不含 `preference_rank`、`processing_order`、`tie_break_random_index`、`fallback_random_index` 等技術 token（沿用既有 FORBIDDEN 正則模式）

### Implementation

- [ ] T017 [US1] 在 `src/matcher/web/humanize.py` 新增純函式 `mechanism_label(mechanism: str) -> str`（回 「M0 純抽籤」/「M1 RSD 隨機輪流挑」/「M2 Boston 層級填滿」）與 `preference_rank_display(rank: int | None, fallback_index: int | None) -> str | None`（M0 → None；rank 非 null → `"第 {N} 志願"`；fallback → `"抽籤"`）
- [ ] T018 [US1] 在 `tests/unit/test_humanize_mechanism.py` 新增單元測試覆蓋 T017 兩函式所有分支（≥ 6 個 case）
- [ ] T019 [US1] 修改 `src/matcher/web/templates/new_match.html` 新增「分配機制」下拉 `<select name="mechanism">` 含 3 個 option 與 `<small>` 說明（請見 contracts/web-routes.md GET /match/new 段）
- [ ] T020 [US1] 修改 `src/matcher/web/routes/match.py::match_detail` —— 注入 `mechanism`、`mechanism_label`、`processing_order_display`（M0 → None；M1/M2 → [(rid, name)]）到 template context
- [ ] T021 [US1] 修改 `src/matcher/web/templates/match_result.html` —— 標題段顯示 `{{ mechanism_label }}`；新增「處理順序」段（`{% if processing_order_display %}`）；分配表新增「志願排名」欄（`{% if mechanism != 'M0' %}`）使用 `preference_rank_display`
- [ ] T022 [US1] 執行 `uv run pytest tests/integration/test_web_mechanism_form.py tests/integration/test_web_cli_audit_equivalence.py tests/unit/test_humanize_mechanism.py -q` 確認全綠

**Parallel batch**：T010–T016 可並行寫測試（皆獨立檔案/函式）；T017–T021 依檔案分組可並行（T017+T019 [P]；T020 與 T021 同檔/相關，序列）。

**Checkpoint US1 完成**：MVP 可端到端跑 M2，行政可在 Web 上看到完整結果。

---

## Phase 4 — User Story 2 (P2)：個別查詢頁顯示志願滿足度

**Goal**：個別查詢頁在 M1/M2 路徑下顯示三分支文案。

**Independent Test**：US1 跑出的 M2 record，逐一打開個別查詢頁 → 看到三種文案之一（第 N 志願 / fallback+有志願 / fallback+無志願）；M0 record 打開個別頁則不出現此段。

### Tests (TDD — 先紅)

- [ ] T030 [P] [US2] 撰寫 `tests/integration/test_web_individual_preference.py::test_shows_preference_rank_when_assigned_to_preferred` —— 跑 M1，挑一位 preference_rank 非 null 的角色，個別頁 HTML 含「您被分到第 N 志願：」
- [ ] T031 [P] [US2] 撰寫 `tests/integration/test_web_individual_preference.py::test_shows_fallback_with_preferences_text` —— 構造 / 找出一位 fallback 抽中 + 有志願 的角色，個別頁含「您原本的志願已被分配給其他人，由公平抽籤分到」
- [ ] T032 [P] [US2] 撰寫 `tests/integration/test_web_individual_preference.py::test_shows_fallback_without_preferences_text` —— 跑 M1 + 混合 roster（含一位無 preferences 的角色），個別頁含「您未在志願清單中，由公平抽籤分到」
- [ ] T033 [P] [US2] 撰寫 `tests/integration/test_web_individual_preference.py::test_m0_individual_page_omits_preference_section` —— 跑 M0，個別頁 HTML **不**含「您被分到第」也**不**含「由公平抽籤分到」
- [ ] T034 [P] [US2] 撰寫 `tests/integration/test_web_individual_preference.py::test_no_technical_tokens_in_individual_html` —— 個別頁 HTML 不含 `preference_rank`、`fallback_random_index`、`preferred_order` 等技術 token

### Implementation

- [ ] T035 [US2] 修改 `src/matcher/web/routes/match.py::individual_view` —— 從 `record.audit` 推導注入 `mechanism`、`preference_rank`（從 `allocation_trace` 中查找該 role_id）、`preferred_count`（從 `roster_snapshot` 中該角色 preferred_order 長度，無則 0）到 template context
- [ ] T036 [US2] 修改 `src/matcher/web/templates/individual_view.html` —— 加入三分支 jinja2 if/elif/else（請見 research.md D4 段；用 `assigned_display` 等既有 context 變數）；外層條件 `{% if mechanism in ('M1', 'M2') %}`
- [ ] T037 [US2] 執行 `uv run pytest tests/integration/test_web_individual_preference.py -q` 確認全綠

**Checkpoint US2 完成**：個別查詢頁支援三分支文案。

---

## Phase 5 — User Story 3 (P3)：Web 路徑的 M1/M2 拒絕與錯誤回應

**Goal**：M1/M2 + 空 prefs 在 Web 顯示友善失敗訊息（沿用 admin 結果頁失敗模式）。

**Independent Test**：選 M1 + 上傳 `examples/study-group/roster.yaml`（全空 prefs）→ 結果頁 status=failed + 訊息含「M1 需要至少一位角色提供志願」。

### Tests (TDD — 先紅)

- [ ] T040 [P] [US3] 撰寫 `tests/integration/test_web_mechanism_reject.py::test_m1_with_empty_prefs_failed_record` —— Web POST M1 + 空 prefs roster，預期 303 + 結果頁顯示 failed + 「M1 需要至少一位角色提供志願」
- [ ] T041 [P] [US3] 撰寫 `tests/integration/test_web_mechanism_reject.py::test_m2_with_empty_prefs_failed_record` —— 同上 M2 + 訊息「M2 需要至少一位角色提供志願」
- [ ] T042 [P] [US3] 撰寫 `tests/integration/test_web_mechanism_reject.py::test_m0_with_prefs_failed_record` —— Web POST M0 + roster-m1.csv，預期失敗 + `PreferencesNotSupported` 訊息（向後相容）

### Implementation

- [ ] T043 [US3] 驗證既有 `routes/match.py::run` 已處理 `MatcherError` 並寫 record.status="failed"——若 T040-T042 仍有任何測試失敗，補強錯誤捕獲（預期既有路徑已涵蓋，僅 mechanism 不再硬編碼後自然支援）
- [ ] T044 [US3] 執行 `uv run pytest tests/integration/test_web_mechanism_reject.py -q` 確認全綠

**Checkpoint US3 完成**：拒絕路徑覆蓋。

---

## Phase 6 — Polish & Cross-cutting

- [ ] T050 [P] 守護測試 `tests/integration/test_core_unchanged.py::test_core_modules_not_modified_in_feature_008` —— 用 `subprocess` 跑 `git diff --name-only main...HEAD -- src/matcher/`，斷言不含 `rules.py|filter.py|allocator.py|pipeline.py|audit.py|errors.py|data_import.py|template_loader.py|rng.py|roster.py`（FR-011/SC-007 守護；feature 完成後此測試永久保留為「歷史快照」或 marker `@pytest.mark.feature_008_guard` 略過）
- [ ] T051 [P] 執行完整測試 `uv run pytest -q` —— 既有 210 + 新增 ≥ 8 全綠（預期 ≥ 218）
- [ ] T052 [P] 依 quickstart.md 8 個步驟在瀏覽器手動驗收一次
- [ ] T053 更新 `README.md` 在「Web UI」段落補一段「分配機制」說明（≤ 5 行）
- [ ] T054 確認 `git status` 僅含預期變動（`src/matcher/web/{routes/match.py, humanize.py, templates/*.html}` + `tests/integration/test_web_*.py` + `tests/unit/test_humanize_mechanism.py` + `specs/008-*/*` + `README.md`）

---

## Dependencies

```
Phase 2 (Foundational) ─┬─→ Phase 3 (US1, MVP)
                        ├─→ Phase 4 (US2)
                        └─→ Phase 5 (US3)

Phase 3, 4, 5 → Phase 6 (Polish)
```

- US1、US2、US3 在 Phase 2 完成後可**並行**進行（三者修改不同樣板/不同測試檔；唯一交集是 routes/match.py 的不同函式）
- 建議交付順序：MVP 為 US1（最大價值）；US2、US3 可後續迭代或同迭代並行

## Parallel Execution Examples

**Phase 2 測試批次**：T001 T002 T003 可同時開（同檔案不同函式可序列；但建議**先寫全部測試**再寫 T004 實作以強化 TDD）。

**Phase 3 測試批次**：T010 T011 T012 T013 T014 T015 T016 全部 [P]——皆為獨立檔案或獨立函式。

**Phase 3 實作分組**：
- 批 A [P]：T017（humanize.py）+ T019（new_match.html）—— 不同檔案
- 批 B：T018（test_humanize_mechanism.py）—— 依 T017
- 批 C：T020 → T021 —— 同檔/相關，序列

**Phase 4 測試批次**：T030 T031 T032 T033 T034 全部 [P]。

**Phase 5 測試批次**：T040 T041 T042 全部 [P]。

**Phase 6**：T050 T051 T052 全部 [P]；T053 T054 序列收尾。

## Implementation Strategy

**MVP**：Phase 2 + Phase 3（US1）——12 個任務，約 4-6 小時。完成後即可端到端跑 M1/M2 Web demo，**符合最大價值**。

**v2 增量**：Phase 4（US2）——個別查詢頁三分支，約 1-2 小時。

**v3 增量**：Phase 5（US3）——拒絕路徑，約 30 分鐘（既有路徑應已涵蓋大半）。

**收斂**：Phase 6——polish 與守護測試。

**總計**：~24 個任務、新增 ≥ 11 個自動化測試（超過 SC-008 的 ≥ 8 門檻）、估 6-9 小時。

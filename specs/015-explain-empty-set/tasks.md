# Tasks — 配對失敗可解釋（資格集合為空）

**Feature**: 015-explain-empty-set
**Branch**: `015-explain-empty-set`
**MVP**：Phase 2 + Phase 3（US1）—— 核心攜帶診斷 + CLI/Web 顯示元兇規則。US2（保留輸入）、US3（R003 修正）可接續。

## 原則
- TDD：每項先寫測試（紅）再實作（綠）
- 核心變動限「可解釋性」三檔：filter.py / errors.py / cli.py（教訓 7）
- 成功配對 audit schema 不變（FR-007 / SC-005）

## Phase 1：Setup
- [x] T001 確認 branch `015-explain-empty-set`、working tree 乾淨、385 測試綠基線

## Phase 2：Foundational（核心攜帶診斷）

**目標**：filter 在空集合時算出 rejection_summary 並附到例外。US1/US2/US3 都依賴它。

### Tests（先紅）
- [x] T010 [P] `tests/unit/test_rejection_summary.py`：給合成 trace + ruleset → rejection_summary 回 {total_pairs, rule_stats（每規則沒過組數）, culprit（最大者）}；全過 → culprit None
- [x] T011 [P] `tests/unit/test_qualified_set_empty_carries_diagnostic.py`：建一個全不通過的 ruleset+roster → filter_qualified 拋 QualifiedSetEmpty，且 err.rule_stats / err.culprit / err.total_pairs / err.trace 有值；exit_code 仍 10；str(err) 訊息不變

### 實作（綠）
- [x] T012 修改 `src/matcher/errors.py`：QualifiedSetEmpty 加 `__init__(message, *, trace, rule_stats, culprit, total_pairs)`，預設空；exit_code 維持 10
- [x] T013 修改 `src/matcher/filter.py`：新增純函式 `rejection_summary(trace, ruleset)`（每組「沒過規則 = 全部 − matched_rules」逐一計數 → rule_stats + culprit + total_pairs）；空集合 raise 前用它算好並附到例外
- [x] T014 執行 `uv run pytest tests/unit/test_rejection_summary.py tests/unit/test_qualified_set_empty_carries_diagnostic.py -q` 綠

**Checkpoint**：核心失敗時帶得出「哪條規則卡幾組」。

---

## Phase 3：User Story 1 — 空集合說清原因（P1）

**Independent Test**：teacher-class 全不通過 → CLI exit 10 印元兇規則描述；Web 失敗顯示元兇 + 各規則計數；皆無技術 token。

### Tests（先紅）
- [x] T020 [P] [US1] `tests/integration/test_cli_empty_set_diagnostic.py`：CLI 跑全不通過名單 → exit 10、stderr 含元兇規則「描述」與「卡住 N/M 組」；不含技術 token
- [x] T021 [P] [US1] `tests/integration/test_web_empty_set_diagnostic.py::test_csv_upload_empty_set_shows_culprit`：CSV 上傳全不通過 → 失敗 record error.diagnostic 有 culprit/rule_stats；結果頁失敗分支顯示元兇規則描述、無技術 token

### 實作（綠）
- [x] T022 [US1] 修改 `src/matcher/cli.py` `_die`：對帶診斷的 QualifiedSetEmpty 多印「最可能原因：<元兇描述>（卡住 N/總 M 組）」+ 各規則計數；退出碼不變
- [x] T023 [US1] 修改 `src/matcher/web/routes/match.py`：`run`（CSV 上傳）catch QualifiedSetEmpty → 失敗 record error 加 `diagnostic`（total_pairs/rule_stats/culprit/rules 描述對照）
- [x] T024 [US1] 修改 `src/matcher/web/templates/match_result.html` 失敗分支：渲染診斷（元兇規則描述 + 各規則卡住數），人類可讀、無技術 token
- [x] T025 [US1] 執行 `uv run pytest tests/integration/test_cli_empty_set_diagnostic.py tests/integration/test_web_empty_set_diagnostic.py -q` 綠

---

## Phase 4：User Story 2 — UI 失敗保留輸入（P2）

**Independent Test**：UI 填名單觸發空集合 → 回到填名單頁、內容還在 + 診斷紅字。

### Tests（先紅）
- [x] T030 [P] [US2] `tests/integration/test_web_empty_set_diagnostic.py::test_fill_form_empty_set_refills_with_diagnostic`：run-from-form 全不通過 → 200 回填名單頁、prefill 含剛填角色/對象、頁面顯示元兇規則診斷、無技術 token

### 實作（綠）
- [x] T031 [US2] 修改 `src/matcher/web/routes/match.py` `run_from_form`：catch QualifiedSetEmpty → 用 `_render_fill_form`（feature 014）回填 prefill_roles/targets + form_error 帶診斷摘要；不存失敗 record
- [x] T032 [US2] 修改 `src/matcher/web/templates/roster_form_fill.html`：form_error 區塊能顯示「元兇規則描述 + 卡住組數」（沿用既有 banner）
- [x] T033 [US2] 執行對應測試綠

---

## Phase 5：User Story 3 — 修 teacher-class R003 中英文不一致（P2）

**Independent Test**：班級 feature 填「雙語」→ R003 通過、配對成功。

### Tests（先紅）
- [x] T040 [P] [US3] `tests/integration/test_teacher_class_r003_chinese.py`：teacher-class 角色+對象（feature=雙語/stem/藝術）→ 配對成功；feature 填英文 bilingual → 該組被 R003 刷掉
- [x] T041 [P] [US3] 既有測試掃描：grep 測試中 teacher-class 對象 feature 寫死 `bilingual/arts` 之處，列出待改清單

### 實作（綠）
- [x] T042 [US3] 修改 `src/matcher/templates/builtin/teacher-class.yaml` R003：`in` set `[bilingual, stem, arts]` → `[雙語, stem, 藝術]`
- [x] T043 [US3] 修改 `examples/teacher-class/roster.targets.yaml`：feature 值 bilingual→雙語、arts→藝術（stem 不變）
- [x] T044 [US3] 修補既有測試中 teacher-class feature 寫死英文之處（test_web_*、unit 等）改中文
- [x] T045 [US3] 重生 teacher-class 相關 golden（teacher-class-baseline / teacher-class-csv / teacher-class-template）；確認 assignment 結構合理、僅值對齊改變
- [x] T046 [US3] 執行 `uv run pytest -q` 全綠

---

## Phase 6：Polish
- [ ] T050 執行 quickstart SC-001~SC-005
- [ ] T051 核心守門：`git diff main --name-only -- 'src/matcher' ':!src/matcher/web' ':!src/matcher/templates'` 只含 filter/errors/cli
- [ ] T052 `uv run pytest -q` 全綠最終確認
- [ ] T053 更新 `knowledge/vision.md`：階段 4h（或併入既有）記「失敗可解釋」+ teacher-class R003 修正
- [ ] T054 評估 `knowledge/experience.md` lesson（如「已算出的診斷資料別在失敗時丟掉」「範本說明與接受值要一致」）

## 任務統計
| Phase | Tasks | 估 |
|---|---|---|
| Setup | 1 | 5 min |
| Foundational | 5 (T010-T014) | 1.5 小時 |
| US1 | 6 (T020-T025) | 2 小時 |
| US2 | 4 (T030-T033) | 1 小時 |
| US3 | 7 (T040-T046) | 1.5 小時（含 golden 重生）|
| Polish | 5 | 1 小時 |
| **Total** | **28** | **~7 小時** |

## Dependencies
```
Setup → Foundational（核心診斷）→ US1（CLI+Web 顯示）
                                   ├→ US2（UI 回填，依賴 US1 診斷 + feature 014 _render_fill_form）
                                   └→ US3（R003 修正，獨立，但 golden 重生最好最後做）
→ Polish
```
US3 與 US1/US2 技術上獨立，但 US3 的 golden 重生建議排最後，避免中途與其他改動互相干擾。

## 並行
- Foundational tests：T010 / T011 同時寫
- US1 tests：T020 / T021 同時寫

## Implementation Strategy
1. Foundational 先做——核心攜帶診斷是一切基礎
2. US1 = MVP：CLI + Web 都能說「哪條規則卡光」
3. US2 接力（UI 回填，沿用 feature 014 機制）
4. US3 最後（R003 + golden 重生，獨立切面，集中處理避免干擾）

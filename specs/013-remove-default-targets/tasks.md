# Tasks — 移除 default_targets 概念

**Feature**: 013-remove-default-targets
**Branch**: `013-remove-default-targets`
**MVP**：Phase 2 + Phase 3（US1 + US2 都是 P1，必須一起完成才有可發布的 MVP；US3 audit 升版是 P2，可作 v2）

## 任務組織原則

- TDD 紅綠重構（Constitution I）：每個實作任務前都有對應測試任務
- US1 與 US2 互相依賴（都動到 data_import / template）→ 共用 Phase 2 Foundational
- US3 audit schema 升版是獨立切面，但要等 US1/US2 落地後再做（測試斷言才能穩定）
- 既有 342 測試必須維持綠：分配 sidecar fixture 任務於 Phase 2

## Phase 1：Setup

- [ ] T001 確認 branch 為 `013-remove-default-targets` 且 working tree 乾淨

## Phase 2：Foundational（blocking）

**目標**：補上所有 examples sidecar、抽出將被刪除的 yaml 內容到 sidecar 檔，讓後續單獨拔 default_targets 時 examples / 既有測試不會立刻爆炸。

- [ ] T010 [P] 建立 `examples/teacher-class/roster.targets.yaml`，內容從 `src/matcher/templates/builtin/teacher-class.yaml` 的 `default_targets:` 段抽出（5 班，原樣不動）
- [ ] T011 [P] 建立 `examples/study-group/roster.targets.yaml`，內容從 `src/matcher/templates/builtin/study-group.yaml` 的 `default_targets:` 段抽出
- [ ] T012 [P] 撰寫 `tests/integration/test_examples_sidecar_roundtrip.py`，斷言：用 examples/teacher-class/roster.csv + roster.targets.yaml 跑 M0 → 結果 assignment 含 5 班、qualified_set 非空（守住 examples 完整性）
- [ ] T013 執行 `uv run pytest tests/integration/test_examples_sidecar_roundtrip.py -q`，確認綠（Phase 2 出口條件）

**Checkpoint**：examples 完整可用，可以開始拔 default_targets。

---

## Phase 3：User Story 1 — 配對時看見對象（P1）

**Story 目標**：UI 填名單頁的對象段永遠顯示；移除 default_targets 在 data model 與內建範本中的存在；data_import 一律要求 sidecar。

**Independent Test**：
1. `curl /match/new/fill?template_id=teacher-class | grep -q "對象清單"` 成功
2. UI POST 5 老師 + 3 班級 → M0 跑通 → audit `roster_snapshot.targets` 含這 3 班
3. CLI 缺旁檔 → 退出碼非零 + 訊息含 "targets.yaml"

### Tests for US1（先寫，紅）

- [ ] T020 [P] [US1] 撰寫 `tests/unit/test_template_loader_no_default_targets.py::test_parse_silently_ignores_default_targets_key`，斷言含 `default_targets:` 的 YAML 仍可 parse、結果 Template 物件無 `default_targets` 屬性
- [ ] T021 [P] [US1] 撰寫 `tests/unit/test_template_loader_no_default_targets.py::test_dump_never_writes_default_targets`，斷言 dump_template 輸出的 dict 不含此鍵
- [ ] T022 [P] [US1] 修改 `tests/integration/test_csv_import.py`：對使用 teacher-class 的測試補 sidecar fixture；新增 `test_load_roster_csv_missing_sidecar_raises_with_clear_message` 斷言錯誤訊息含 "targets.yaml"
- [ ] T023 [P] [US1] 修改 `tests/integration/test_web_roster_fill_targets.py::test_fill_page_hides_targets_section_when_default_targets_exists` → 改名為 `test_fill_page_always_shows_targets_section`，斷言對象段永遠顯示（即使用 teacher-class）
- [ ] T024 [P] [US1] 新增 `tests/integration/test_web_run_csv_without_sidecar.py`：Web 上傳 CSV 但缺 sidecar → HTTP 400，HTML 含「請改用『直接填名單』」或類似指引

### Implementation for US1（紅→綠）

- [ ] T030 [US1] 修改 `src/matcher/template.py`：移除 `Template.default_targets` 欄位
- [ ] T031 [US1] 修改 `src/matcher/template_loader.py`：parse_template 刪除 default_targets 解析迴圈（line 126-152 附近），dump_template 不輸出此鍵（line 326-329）
- [ ] T032 [US1] 修改 `src/matcher/data_import.py::_load_targets`：刪除 fallback 分支（line 278-280），錯誤訊息改為 research D2 文字
- [ ] T033 [US1] 修改 `src/matcher/templates/builtin/teacher-class.yaml`：刪除整段 `default_targets:` 區塊
- [ ] T034 [US1] 修改 `src/matcher/templates/builtin/study-group.yaml`：同上
- [ ] T035 [P] [US1] 修改 `src/matcher/web/template_form.py`：刪除 default_targets 寫入段（line 147-163）
- [ ] T036 [P] [US1] 修改 `src/matcher/web/roster_form.py::assemble_targets_yaml_bytes`：刪除 `if template.default_targets: return None`；改為「未填任何對象 → 回 None」（語意保留，呼叫方依此判斷 400）
- [ ] T037 [P] [US1] 修改 `src/matcher/web/routes/match.py::run_from_form`：刪除 `not tpl.default_targets` 條件分支；對「assemble_targets_yaml_bytes 回 None」一律 400
- [ ] T038 [P] [US1] 修改 `src/matcher/web/routes/match.py::new_match_fill`：刪除 `requires_targets` 計算，樣板 context 不再傳此鍵
- [ ] T039 [P] [US1] 修改 `src/matcher/web/templates/roster_form_fill.html`：刪除 `{% if requires_targets %}` 與 `{% endif %}`，對象段永遠顯示
- [ ] T040 [P] [US1] 修改 `src/matcher/web/routes/pages.py`：刪除 template_detail 內 `for i, t in enumerate(tpl.default_targets or []):` 迴圈
- [ ] T041 [P] [US1] 修改 `src/matcher/web/templates/template_detail.html`：刪除「預設對象」展示段

### 修補既有測試（將因 US1 變動而失敗）

- [ ] T050 [US1] 修補 `tests/unit/test_template_form_assembly.py`：刪除任何 default_targets 相關斷言
- [ ] T051 [US1] 修補 `tests/unit/test_roster_form_assemble.py::test_assemble_targets_yaml_returns_none_when_default_targets_exists`：改為「未填對象時回 None」的新語意
- [ ] T052 [US1] 修補 `tests/integration/test_m2_reject.py`、`test_csv_preferences_reject.py`、`test_cli_mechanism_m1.py` 等使用 teacher-class / study-group 跑 CLI 的測試：補 sidecar fixture
- [ ] T053 [US1] 修補 `tests/integration/test_web_individual_view.py`、`test_web_new_match.py`、`test_match_rerun_from_snapshot.py`、`test_web_pdf_admin.py`、`test_web_pdf_individual.py`、`test_web_pdf_graceful_degrade.py`、`test_pdf_no_technical_tokens.py`、`test_cli_report.py`、`test_template_export_import.py`、`test_template_preferences_reject.py`、`test_web_preferences_form_scale.py`：補 sidecar 或調整斷言
- [ ] T054 [US1] 修補 `tests/integration/test_web_roster_fill_basic.py`、`test_web_roster_fill_m1_handoff.py`：填表時必須一併填對象（因為對象段現在會顯示但 form 沒填會 400）

### US1 出口

- [ ] T060 [US1] 執行 `uv run pytest -q` 確認全綠
- [ ] T061 [US1] 執行 quickstart SC-002（grep）與 SC-004（UI 對象段顯示），手動驗證

---

## Phase 4：User Story 2 — CLI 旁檔機制保持可用（P1）

**Story 目標**：CLI 路徑跑配對時，提供 `.targets.yaml` 旁檔 → 跑通且結果與 feature 012 時代等價（modulo template_snapshot.default_targets 已移除）。

**Independent Test**：
- `matcher run --template teacher-class --roster-csv examples/teacher-class/roster.csv --seed 2026` 跑通
- audit assignment / qualified_set 與「升版前同樣指令」內容等價

**注意**：絕大部分工作已在 Phase 2/3 完成（sidecar 機制本來就在）。US2 只需驗證 + edge case。

### Tests for US2

- [ ] T070 [P] [US2] 新增 `tests/integration/test_cli_roundtrip_with_sidecar.py::test_cli_run_with_sidecar_succeeds`：用 examples/teacher-class CSV + sidecar 跑 CLI → assignment 5 老師被分配
- [ ] T071 [P] [US2] 新增 `tests/integration/test_cli_roundtrip_with_sidecar.py::test_cli_run_without_sidecar_fails_with_clear_message`：刪除 sidecar → 退出碼非零 + stderr 含 "targets.yaml"
- [ ] T072 [P] [US2] 新增 `tests/integration/test_cli_roundtrip_with_sidecar.py::test_cli_xlsx_path_also_requires_sidecar`：xlsx 路徑下同樣要 sidecar

### Implementation for US2

- [ ] T080 [US2] （無新實作；皆隨 US1 落地）執行 `uv run pytest tests/integration/test_cli_roundtrip_with_sidecar.py -q` 確認綠

---

## Phase 5：User Story 3 — audit schema v1.4（P2）

**Story 目標**：audit JSON 的 `schema_version` 升為 `"1.4"`；`template_snapshot` 不含 `default_targets`。

**Independent Test**：
- 任何成功配對的 audit JSON：`schema_version == "1.4"` 且 `"default_targets" not in template_snapshot`

### Tests for US3

- [ ] T090 [P] [US3] 新增 `tests/integration/test_audit_schema_v1_4.py::test_new_audit_has_schema_version_1_4`：跑一次 M0 配對 → audit.schema_version == "1.4"
- [ ] T091 [P] [US3] 新增 `tests/integration/test_audit_schema_v1_4.py::test_template_snapshot_omits_default_targets`：audit.template_snapshot 鍵集合不含 "default_targets"
- [ ] T092 [P] [US3] 新增 `tests/integration/test_audit_schema_v1_4.py::test_roster_snapshot_targets_still_complete`：targets 完整含 id/capacity/attributes

### Implementation for US3

- [ ] T100 [US3] 修改 `src/matcher/audit.py`：
  - 常數 `SCHEMA_VERSION` 或字面值 `"1.3"` → `"1.4"`
  - 刪除 build_audit 內 `template_snapshot["default_targets"] = [t.to_dict() for t in tpl.default_targets]`（line 111-113）
- [ ] T101 [P] [US3] 修補既有 audit 斷言：grep 所有測試中 `'schema_version': '1.3'` 或 `"schema_version": "1.3"` → 改為 `"1.4"`；若有測試斷言 `audit["template_snapshot"]["default_targets"]` 存在 → 改為斷言不存在
- [ ] T102 [US3] 執行 `uv run pytest -q` 確認全綠

---

## Phase 6：Polish

- [ ] T110 [P] 執行 quickstart 全部 5 個 SC 腳本，逐一驗證 SC-001~SC-005
- [ ] T111 [P] grep 整個 `src/matcher` 確認無 `default_targets` 殘留（除註解/docstring 提到歷史脈絡之外）：`grep -rn "default_targets" src/matcher --include='*.py'` → 應只剩 docstring 提及
- [ ] T112 grep 確認 `src/matcher/templates/builtin/*.yaml` 無 `default_targets:` 字串
- [ ] T113 更新 `knowledge/vision.md`：標記階段 4f「移除 default_targets」完成；補相關 SC 條目
- [ ] T114 在 `knowledge/experience.md` 評估是否加 lesson（譬如「拔欄位前先補替代資料管道」這類經驗）

---

## 任務統計

| Phase | Tasks | 預估 |
|---|---|---|
| Setup | 1 (T001) | 5 min |
| Foundational | 4 (T010-T013) | 30 min |
| US1 | 32 (T020-T061) | 4-5 小時（主力工作） |
| US2 | 4 (T070-T080) | 30 min |
| US3 | 4 (T090-T102) | 1 小時 |
| Polish | 5 (T110-T114) | 30 min |
| **Total** | **50** | **~7 小時** |

## Dependencies

```
Setup (T001)
   ↓
Foundational (T010-T013) ─── 建立 examples sidecar，後續才能拔內建 default_targets
   ↓
US1 (T020-T061) ────────── 主力：拔 dataclass + loader + builtin yaml + UI + 所有測試修補
   ↓
US2 (T070-T080) ────────── 驗證 CLI 路徑（無新實作）
   ↓
US3 (T090-T102) ────────── audit schema 升 v1.4
   ↓
Polish (T110-T114)
```

US1 內部：
- T020-T024（tests，[P]）→ 同步寫
- T030-T034 必須 sequential（同檔變動 / 強相依）
- T035-T041 多檔 [P]（不同 web 檔案）
- T050-T054（測試修補，[P]）

## 並行範例

**Phase 2 並行**：T010 + T011 + T012 同時做（三個獨立檔）

**US1 tests 並行**：T020/T021/T022/T023/T024 同時寫（不同測試檔）

**US1 web 實作並行**：T035/T036/T037/T038/T039/T040/T041 同時做（不同 web 檔）

**US1 測試修補並行**：T050/T051/T052/T053/T054 同時做（各自的測試檔）

## Implementation Strategy

1. **Foundational 先做**：補 examples sidecar，避免後續拔 builtin yaml 時 examples 斷掉
2. **US1 主力**：分三波並行
   - 波 1：寫測試（T020-T024）
   - 波 2：改 core 與 web 實作（T030-T041）
   - 波 3：修既有測試（T050-T054）
3. **US2 收尾驗證**：純測試任務，跑完確認 CLI 沒退化
4. **US3 audit 升版**：最後做，避免中途因 schema_version 變動讓 US1 測試擾動
5. **Polish**：對 vision/experience knowledge files 做一次性 update

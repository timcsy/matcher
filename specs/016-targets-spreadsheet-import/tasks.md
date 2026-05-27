# Tasks — 對象名單試算表匯入

**Feature**: 016-targets-spreadsheet-import
**Branch**: `016-targets-spreadsheet-import`
**MVP**：Phase 2（核心對象載入器）+ Phase 3（US1 雙檔上傳）—— 能上傳兩個試算表配對。US2（動態範例）、US3（auto-id）接續。

## 原則
- TDD：每項先寫測試（紅）再實作（綠）
- 核心變動限「資料匯入」職責：`data_import.py`（教訓 7）
- CLI `.targets.yaml` 旁檔向後相容；audit schema 不變；無新依賴

## Phase 1：Setup
- [x] T001 確認 branch `016-targets-spreadsheet-import`、working tree 乾淨、395 測試綠基線

## Phase 2：Foundational（核心對象載入器）

**目標**：data_import 能從 CSV/Excel 載入對象 + load_roster 可注入 targets。US1/US3 依賴它。

### Tests（先紅）
- [x] T010 [P] `tests/unit/test_targets_import.py::test_load_targets_csv_basic` —— 對象 CSV（編號/容量/中文屬性欄）→ tuple[Target]，容量為 int、list_str 正確切分
- [x] T011 [P] `tests/unit/test_targets_import.py::test_load_targets_csv_chinese_headers` —— 表頭用中文顯示名稱 → 對齊範本對象屬性
- [x] T012 [P] `tests/unit/test_targets_import.py::test_load_targets_csv_missing_capacity_col_raises` —— 缺容量欄 → RosterColumnMismatch（訊息含「容量」）
- [x] T013 [P] `tests/unit/test_targets_import.py::test_load_targets_xlsx_basic` —— Excel 對象檔載入
- [x] T014 [P] `tests/unit/test_targets_import.py::test_load_roster_csv_with_injected_targets` —— load_roster_csv(roster, tpl, targets=<tuple>) → 用注入的 targets、不讀旁檔
- [x] T015 [P] `tests/unit/test_targets_import.py::test_load_roster_csv_targets_none_uses_sidecar` —— targets=None 時沿用旁檔（向後相容）

### 實作（綠）
- [x] T016 在 `src/matcher/data_import.py` 新增 `_resolve_target_headers(headers, template)`（拿表頭對齊 template.attributes.targets，重用 resolve_header）
- [x] T017 新增 `load_targets_csv(path, template) -> tuple[Target,...]`：detect_csv_encoding + DictReader + _resolve_target_headers + coerce_value；容量必欄、<1 報錯；重複 id → DuplicateIdentity；缺 id 欄/空 → 自動 T001…（避開已有）
- [x] T018 新增 `load_targets_xlsx(path, template, sheet=None) -> tuple[Target,...]`（沿用既有 xlsx 讀法）
- [x] T019 `load_roster_csv` / `load_roster_xlsx` 加參數 `targets=None`：給定則用、否則 `_load_targets`（旁檔）
- [x] T020 執行 `uv run pytest tests/unit/test_targets_import.py -q` 綠

**Checkpoint**：核心能從試算表載對象、能注入 targets。

---

## Phase 3：User Story 1 — 上傳兩個試算表配對（P1）

**Independent Test**：上傳老師 CSV + 班級 CSV（或 xlsx）→ 配對成功；audit.targets 來自上傳的對象檔；與同資料 YAML 旁檔 audit 等價。

### Tests（先紅）
- [x] T030 [P] [US1] `tests/integration/test_web_two_file_import.py::test_two_csv_files_match_succeeds` —— /match/run 上傳 roster.csv + targets.csv → 配對成功、targets 正確
- [x] T031 [P] [US1] `::test_csv_roster_xlsx_targets_mixed` —— 角色 CSV + 對象 Excel 混搭成功
- [x] T032 [P] [US1] `::test_targets_csv_equivalent_to_yaml_sidecar` —— 同對象資料用 targets.csv vs .targets.yaml → audit.roster_snapshot.targets 等價（SC-005）
- [x] T033 [P] [US1] `::test_no_targets_source_friendly_error` —— 只上傳角色檔、無對象 → 友善錯誤（提示上傳對象試算表或直接填）

### 實作（綠）
- [x] T034 [US1] `src/matcher/web/routes/match.py` `run`：第二檔欄位 `targets_file`（取代/相容既有 targets_yaml）；依副檔名 .csv→load_targets_csv、.xlsx→load_targets_xlsx、.yaml→既有 YAML 旁檔路徑
- [x] T035 [US1] 解析出的 targets 以 `targets=` 注入 `load_roster_csv`/`load_roster_xlsx`；缺對象來源 → 友善錯誤
- [x] T036 [US1] `src/matcher/web/templates/new_match.html` 上傳區：兩個檔案欄位「角色名單」「對象名單」（皆 .csv,.xlsx）
- [x] T037 [US1] 執行 `uv run pytest tests/integration/test_web_two_file_import.py -q` 綠

---

## Phase 4：User Story 2 — 依範本動態產生範例（P1）

**Independent Test**：對 teacher-class 與某自訂範本，下載角色/對象範例 → 表頭=範本屬性中文名 + 格式提示列；上傳頁有下載連結。

### Tests（先紅）
- [x] T040 [P] [US2] `tests/unit/test_example_gen.py::test_target_example_headers_match_template` —— target_example_bytes(teacher-class, csv) 表頭 == 編號,容量,班級名稱,班級需要的科目清單,班級特色
- [x] T041 [P] [US2] `tests/unit/test_example_gen.py::test_role_example_headers_match_template` —— 角色範例表頭 == 編號 + 角色屬性中文名
- [x] T042 [P] [US2] `tests/unit/test_example_gen.py::test_example_has_format_hint_row` —— 第二列含型別提示（數字／多筆用分號隔開／文字）
- [x] T043 [P] [US2] `tests/unit/test_example_gen.py::test_xlsx_example_generates` —— xlsx 格式可產生且 openpyxl 可讀回
- [x] T044 [P] [US2] `tests/integration/test_web_example_endpoints.py::test_download_target_example_csv` —— GET /templates/teacher-class/example/targets.csv → 200 + attachment + 中文表頭
- [x] T045 [P] [US2] `::test_example_syncs_with_custom_template` —— 自訂範本加對象屬性 → 範例表頭含新欄
- [x] T046 [P] [US2] `::test_example_requires_login_and_visibility` —— 未登入 → 導向登入；他人私有範本 → 403

### 實作（綠）
- [x] T047 [US2] 新增 `src/matcher/web/example_gen.py`：`role_example_bytes(tpl, fmt)` / `target_example_bytes(tpl, fmt)`（csv 用標準庫、xlsx 用 openpyxl）；表頭中文 + 格式提示列
- [x] T048 [US2] `src/matcher/web/routes/pages.py` 新增 `/templates/{id}/example/{roles|targets}.{csv|xlsx}` 端點（require_login + can_view）
- [x] T049 [US2] `new_match.html` 上傳區加「下載範例（CSV / Excel）」連結（角色 + 對象），用 Alpine 綁目前 template_id；移除舊 GitHub raw 連結
- [x] T050 [US2] 執行對應測試綠

---

## Phase 5：User Story 3 — 對象檔編號可省略自動產生（P2）

**Independent Test**：對象 CSV 無編號欄 → 載入後對象自動取得 id。

### Tests（先紅）
- [x] T060 [P] [US3] `tests/unit/test_targets_import.py::test_targets_csv_no_id_column_auto_numbers` —— 對象 CSV 無「編號」欄 → 自動 T001/T002…
- [x] T061 [P] [US3] `::test_targets_csv_partial_id_avoids_collision` —— 部分列有 id、部分空 → 自動編號避開已填

### 實作（綠）
- [x] T062 [US3] （多半已在 T017 完成）確認 load_targets_csv/xlsx auto-id 邏輯涵蓋「無 id 欄」與「id 欄存在但某列空」；補齊
- [x] T063 [US3] 執行對應測試綠

---

## Phase 6：Polish
- [x] T070 執行 quickstart SC-001~SC-009
- [x] T071 核心守門：`git diff main --name-only -- 'src/matcher' ':!src/matcher/web' ':!src/matcher/templates'` 只含 data_import
- [x] T072 `uv run pytest -q` 全綠
- [x] T073 更新 `knowledge/vision.md`：階段 8（對象試算表匯入 + 動態範例）完成紀錄
- [x] T074 評估 `knowledge/experience.md` lesson（如「動態產生範例 > 維護靜態檔，且涵蓋自訂」）

## 任務統計
| Phase | Tasks | 估 |
|---|---|---|
| Setup | 1 | 5 min |
| Foundational | 11 (T010-T020) | 2.5 小時 |
| US1 雙檔上傳 | 8 (T030-T037) | 2 小時 |
| US2 動態範例 | 11 (T040-T050) | 2.5 小時 |
| US3 auto-id | 4 (T060-T063) | 30 min |
| Polish | 5 | 1 小時 |
| **Total** | **40** | **~8.5 小時** |

## Dependencies
```
Setup → Foundational（核心對象載入器 + targets= 注入）
         ├→ US1（雙檔上傳，依賴 load_targets_* + targets=）
         ├→ US2（動態範例，獨立於 US1；只需範本 schema）
         └→ US3（auto-id，多半含於 Foundational T017）
→ Polish
```
US2 與 US1 在 Foundational 後可並行（不同檔/不同關注點）。US3 多半隨 Foundational 完成。

## 並行
- Foundational tests T010-T015 同時寫
- US1 tests T030-T033、US2 tests T040-T046 各自同時寫

## Implementation Strategy
1. Foundational 先做：核心對象載入器是 US1/US3 的基礎
2. US1 = MVP：兩個試算表上傳能配對（解掉 YAML 門檻）
3. US2 動態範例：與 US1 並行，補「不知道怎麼填」
4. US3：確認 auto-id 邊界（多含於 Foundational）
5. Polish：核心守門 + knowledge

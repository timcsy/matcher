---

description: "Task list for 資料匯入（CSV / Excel）"
---

# Tasks: 資料匯入（CSV / Excel）

**Input**: Design documents from `/specs/003-data-import/`
**Prerequisites**: plan.md ✅、spec.md ✅、research.md ✅、data-model.md ✅、contracts/ ✅、quickstart.md ✅

**Tests**: 包含。Constitution v1.0.0 原則 I（TDD）為不可妥協條款；每個實作任務之前必須先有對應的失敗測試。

**Organization**：依 spec.md 中 P1 / P2 / P3 三條 user story 分組。

## Format: `[ID] [P?] [Story] Description`

- **[P]**：可平行執行（檔案不同、無前置未完成任務）
- **[Story]**：對應的 user story 標籤（US1 / US2 / US3）
- 路徑皆為相對於 repo 根目錄的絕對結構（依 plan.md「Project Structure」）

---

## Phase 1：Setup

**目的**：新依賴安裝。

- [x] T001 在 `pyproject.toml` 的 `dependencies` 新增 `openpyxl>=3.1`；執行 `uv sync` 或 `uv pip install -e ".[dev]"` 確認安裝成功

---

## Phase 2：Foundational（阻塞所有 user story）

**目的**：錯誤類別、AttributeDecl.aliases 擴充、audit/pipeline 演進、data_import 骨架。

**⚠️ CRITICAL**：本階段未完成前，任何 user story 不可開始。

- [x] T002 在 `src/matcher/errors.py` 新增 4 個錯誤類別：`RosterDecodeError`（exit 30）、`RosterColumnMismatch`（exit 31）、`RosterTypeError`（exit 32）、`RosterSheetAmbiguous`（exit 33）
- [x] T003 [P] 在 `src/matcher/template.py` 擴充 `AttributeDecl`：新增 `aliases: tuple[str, ...] = ()` 欄位
- [x] T004 [P] 在 `src/matcher/template_loader.py` 的 `_parse_attribute_decl` 中讀取 `aliases`（list[str] → tuple[str, ...]）
- [x] T005 在 `src/matcher/audit.py` 升級 schema：`schema_version` 從 `"1.1"` 改為 `"1.2"`；`build_audit_record` 新增 `import_metadata: dict | None` 參數；當 None 時輸出 `null`，否則輸出該 dict
- [x] T006 在 `src/matcher/pipeline.py` 的 `MatcherInput` 新增 `import_metadata: dict | None = None` 欄位；`run_match` 將 import_metadata 傳給 `build_audit_record`
- [x] T007 [P] 建立 `src/matcher/data_import.py` 骨架：函式簽章 `detect_csv_encoding(raw_bytes) -> tuple[str, str]`、`resolve_header(name, decls) -> AttributeDecl | None`、`coerce_value(raw, decl) -> object`、`load_roster_csv(path, template) -> tuple[Roster, dict]`、`load_roster_xlsx(path, template, sheet) -> tuple[Roster, dict]`（先放 `raise NotImplementedError`，實作於 US1 / US2）

**Checkpoint**：foundational 完成；既有 82 測試應仍通過（schema 升 v1.2 會破壞 2 個既有測試的 schema_version 期望值，這 2 個測試將於 T016 重生黃金檔時一併修正）。

---

## Phase 3：User Story 1 — CSV 匯入教師-班級基準場景（P1）🎯 MVP

**Goal**：CSV（三種編碼）匯入後可跑通基準場景，與 YAML 路徑稽核紀錄五段完全相同。

**Independent Test**：`matcher run --template teacher-class --roster-csv examples/teacher-class/roster.csv --seed 123456` 跑通；產出的 audit 與 YAML 路徑 audit 在 qualified_set / assignment / filter_trace / allocation_trace / template_snapshot 五段相同。

### 測試（先寫且必須先紅）⚠️

- [x] T008 [P] [US1] `tests/unit/test_data_import.py`：覆蓋 `detect_csv_encoding`（UTF-8 / UTF-8-SIG / CP950 三輪 + 失敗）、`resolve_header`（key / alias / 不分大小寫 / 空白裁切 / 中文嚴格）、`coerce_value`（str / int / list_str 分號展開 / int 失敗 → RosterTypeError）
- [x] T009 [P] [US1] `tests/integration/test_csv_import.py`：三種編碼皆能跑通；CSV 與 YAML 同資料同 seed 的稽核紀錄五段相同（黃金檔比對 + 程式比對）

### 實作

- [x] T010 [US1] 在 `src/matcher/data_import.py` 實作 `detect_csv_encoding(raw_bytes)`：依序嘗試 utf-8 / utf-8-sig / cp950 解碼；皆失敗則拋 `RosterDecodeError` 並列出已嘗試的編碼（依賴 T002）
- [x] T011 [US1] 在 `src/matcher/data_import.py` 實作 `resolve_header(name, decls)`（依 data-model.md 演算法：strip → 精確比對 key → ASCII 不分大小寫比對 key → aliases 同樣兩輪）與 `coerce_value(raw, decl)`（依模板 type 轉型；失敗 → `RosterTypeError`）（依賴 T003）
- [x] T012 [US1] 在 `src/matcher/data_import.py` 實作 `load_roster_csv(path, template)`：讀 bytes → detect_csv_encoding → csv.DictReader → 表頭對齊（依模板 roles 端的 AttributeDecl + aliases）→ 必填欄位檢查（缺漏 → `RosterColumnMismatch`、重複 → `RosterColumnMismatch`）→ 每列 coerce_value → 組裝 Roster（id 依列序 `R001`、`R002`...）+ ImportMetadata dict（依賴 T010、T011）
- [x] T013 [US1] 修改 `src/matcher/cli.py`：`run_cmd` 新增 `--roster-csv <path>` 參數；擴充三組互斥檢查為「規則來源三選一 × 名單來源三選一」雙層互斥（名單來源：`--roster` / `--roster-csv` / `--roster-xlsx`）；CSV 路徑時呼叫 `load_roster_csv` 並把 ImportMetadata 傳入 `MatcherInput.import_metadata`（依賴 T012、T006）
- [x] T014 [P] [US1] 修改 `src/matcher/templates/builtin/teacher-class.yaml`：在每個 `AttributeDecl` 補上常用中文 aliases——`name: ["姓名", "教師姓名"]`、`speciality: ["專業科目", "專業"]`、`seniority: ["年資"]`、target 端的 `name: ["班級名稱", "班級"]`、`required_subjects: ["需要科目", "科目"]`、`feature: ["特色"]`
- [x] T015 [P] [US1] 建立 `examples/teacher-class/roster.csv`：UTF-8-SIG 編碼、中文表頭、與 `examples/teacher-class/roster.yaml` 完全相同的 10 位老師資料
- [x] T016 [US1] 重生既有黃金檔：`tests/golden/teacher-class-baseline.audit.json`（v1.2 + import_metadata: null）、`tests/golden/teacher-class-template.audit.json`（v1.2 + 新 aliases + import_metadata: null）；同步更新 `tests/unit/test_audit.py` 與 `tests/integration/test_baseline.py` 的 `schema_version == "1.1"` 期望值改為 `"1.2"`、`required` 欄位清單補上 `import_metadata`（依賴 T005、T014）
- [x] T017 [P] [US1] 建立 `tests/golden/teacher-class-csv.audit.json`：以 `matcher run --template teacher-class --roster-csv examples/teacher-class/roster.csv --seed 123456` 跑出後另存（依賴 T013、T015、T016）

**Checkpoint**：US1 完成。MVP 可獨立驗證——quickstart.md 第 1、2 節通過。

---

## Phase 4：User Story 2 — Excel 匯入研習分組（P2）

**Goal**：.xlsx（單表 + 多表）匯入後可跑通；多工作表時 `--sheet` 顯式指定。

**Independent Test**：`matcher run --template study-group --roster-xlsx examples/study-group/roster.xlsx --seed 2026` 跑通；多表場景未指定 `--sheet` 時拋 `RosterSheetAmbiguous`。

### 測試（先寫且必須先紅）⚠️

- [x] T018 [P] [US2] `tests/integration/test_xlsx_import.py`：(a) 單表 .xlsx 跑通與 YAML 等價；(b) 多表 .xlsx 未指定 --sheet → exit 33；(c) 多表 + `--sheet "報名表"` → 跑通；(d) 多表 + 指定不存在工作表 → exit 33；(e) 公式儲存格 → 取計算結果

### 實作

- [x] T019 [US2] 在 `src/matcher/data_import.py` 實作 `load_roster_xlsx(path, template, sheet)`：用 openpyxl `load_workbook(path, read_only=True, data_only=True)`；工作表選擇邏輯（單表自動／多表須顯式／指定不存在皆拋 `RosterSheetAmbiguous`）；其餘流程沿用 csv 路徑的 resolve_header + coerce_value（依賴 T011）
- [x] T020 [US2] 修改 `src/matcher/cli.py`：`run_cmd` 新增 `--roster-xlsx <path>` 與 `--sheet <name>` 參數；併入名單來源三組互斥；xlsx 路徑時呼叫 `load_roster_xlsx`（依賴 T019、T013）
- [x] T021 [P] [US2] 修改 `src/matcher/templates/builtin/study-group.yaml`：在每個 `AttributeDecl` 補中文 aliases——`name: ["姓名", "學生姓名"]`、`grade: ["年級"]`、target 端的 `name: ["分組名稱", "組別"]`、`topic: ["主題"]`、`min_grade: ["最低年級"]`；同時為 preferences 加 alias「志願組別」（透過 ui_field 路徑或新增 preferences 對應 attribute，但 preferences 不在 attributes 中——本任務只更新 attributes 的 aliases）
- [x] T022 [P] [US2] 建立 `examples/study-group/roster.xlsx`：單一工作表、中文表頭、與既有 `examples/study-group/roster.yaml` 同資料 9 位學生；建立腳本檔 `scripts/build_examples_xlsx.py` 用 openpyxl 程式化產出（避免依賴外部工具）
- [x] T023 [P] [US2] 建立 `examples/study-group/roster-multi.xlsx`：3 張工作表（「報名表」「說明」「範例」），「報名表」內含與 T022 同資料；其餘為示範資料；同樣以 `scripts/build_examples_xlsx.py` 產出
- [x] T024 [US2] 重生 `tests/golden/study-group-template.audit.json`：study-group 模板加 aliases 後 template_snapshot 改變，需以 `matcher run --template study-group --roster examples/study-group/roster.yaml --seed 2026 --output ...` 重生（依賴 T021、T016）
- [x] T025 [P] [US2] 建立 `tests/golden/study-group-xlsx.audit.json`：以 `matcher run --template study-group --roster-xlsx examples/study-group/roster.xlsx --seed 2026` 跑出後另存（依賴 T020、T022）

**Checkpoint**：US2 完成。SC-005、quickstart 第 3、4 節通過。

---

## Phase 5：User Story 3 — 匯入錯誤的明確訊息（P3）

**Goal**：4 種匯入錯誤情境 + CSV preferences 拒絕，皆有專屬 exit code 與三段式繁中訊息。

**Independent Test**：執行 `tests/integration/test_import_errors.py`，4 種錯誤情境各得到預期 exit code（30/31/32/33）；CSV preferences 非空 → exit 17。

### 測試（先寫且必須先紅）⚠️

- [x] T026 [P] [US3] `tests/integration/test_import_errors.py`：(a) UTF-16 CSV → exit 30；(b) CSV 缺必填欄位 → exit 31，訊息列出缺漏 + aliases；(c) CSV 重複欄位（兩個「姓名」表頭）→ exit 31；(d) CSV 含「八年」於 int 欄 → exit 32，訊息含列號／欄位／值；(e) 多表 xlsx 未指定 --sheet → exit 33
- [x] T027 [P] [US3] `tests/integration/test_csv_preferences_reject.py`：study-group 模板 + CSV 含非空「志願組別」欄位 → exit 17 + 訊息含「M0 純抽籤」「階段 4」（沿用階段 1 PreferencesNotSupported）

### 實作

- [x] T028 [P] [US3] 建立 fixture 目錄 `tests/fixtures/data_import/`：`utf16.csv`、`missing_column.csv`、`duplicate_column.csv`、`bad_type.csv`、`with_preferences.csv`、`empty.csv`（與 T026/T027 對應）；fixture 由 Python 程式產出（避免編碼/格式手寫錯誤）；以 `tests/fixtures/data_import/__init__.py` 內含 `build_fixtures()` 函式於 conftest 自動建立

**Checkpoint**：US3 完成。SC-002、SC-003、SC-006 通過。

---

## Phase 6：Polish & Cross-Cutting

- [x] T029 [P] `tests/integration/test_backward_compat_v003.py`：階段 1/2a 既有 `--rules + --roster` / `--template + --roster <yaml>` / `--template-file + --roster <yaml>` 三種路徑跑通；audit 中 `import_metadata` 皆為 `null`；schema_version 為 `"1.2"`
- [x] T030 [P] 更新 `README.md`：新增「資料匯入」段，含 CSV / Excel / `--sheet` 用法與三種編碼支援的說明
- [x] T031 [P] 跑完整 quickstart.md 9 節，逐項勾選驗證
- [x] T032 [P] 全量回歸：`uv run pytest` 必須全綠（階段 1+2a 既有 82 + 階段 2b 新增 ≈ 25，總計 ≈ 107）
- [x] T033 [P] 跨平台驗證：在 macOS 上以同 seed 同 CSV 跑兩次，確認 `import_metadata` 與五段稽核完全相同（cross-machine 驗證可在 CI 補做）

---

## Dependencies & Execution Order

### Phase 相依

- **Setup (1)**：無前置，可立即開始
- **Foundational (2)**：依賴 Setup；阻塞所有 user story
- **US1 (3)**：依賴 Foundational；MVP 核心
- **US2 (4)**：依賴 US1（共用 data_import、cli 的名單來源互斥邏輯、aliases 模板更新）
- **US3 (5)**：依賴 US1（核心錯誤路徑大多在 US1 實作中產生）；可與 US2 平行
- **Polish (6)**：依賴 US1（部分項目）

### User Story 相依

- **US1 (P1)**：MVP；完成 Foundational 後可開始
- **US2 (P2)**：依賴 US1 完成 data_import / cli 的基底
- **US3 (P3)**：依賴 US1（錯誤路徑大多在實作 csv 時已建立）；可與 US2 平行

### Within Each User Story

- 測試先寫且先紅
- 錯誤類別 → 共用 helper（detect / resolve / coerce）→ 載入器 → CLI → 範例與黃金檔

### Parallel Opportunities

- T003 / T004（不同檔案的型別擴充）可平行
- T007（data_import 骨架）可與 T003/T004 平行
- US1 內測試 T008 / T009 可平行
- T014 / T015（模板與範例）可平行於核心實作
- US2 內 T021 / T022 / T023 可平行
- US2 / US3 主體可平行
- Polish 6 個任務皆 [P]

---

## Parallel Example：User Story 1 測試一次啟動

```bash
# 在啟動實作前一次寫完所有 US1 測試（會先紅）：
Task: "tests/unit/test_data_import.py"
Task: "tests/integration/test_csv_import.py"
```

---

## Implementation Strategy

### MVP First（只到 US1）

1. Phase 1：Setup（裝 openpyxl）
2. Phase 2：Foundational（errors / aliases / audit schema / pipeline / data_import 骨架）
3. Phase 3：US1（CSV + teacher-class）
4. **STOP & VALIDATE**：跑 quickstart 1+2 節；驗證 SC-001（三路徑等價）、SC-007（既有測試通過）

### Incremental Delivery

1. Setup + Foundational → 基底就緒
2. US1 → MVP（CSV 教師-班級可跑通；YAML 路徑兼容）
3. US2 → Excel + 多工作表
4. US3 → 錯誤路徑全覆蓋
5. Polish → 向後相容驗證、README、quickstart 驗證、跨平台驗證

### TDD 嚴格度

- 每個實作任務開工前，對應測試先紅
- bug 修補先補測試
- audit schema 升 v1.2 → 兩個既有測試需更新 schema_version 期望（T016）；3 個既有黃金檔需重生（T016、T024）——這些不是邏輯變更，僅是 schema 演進的同步更新

---

## Notes

- [P] 任務 = 不同檔案、無未完成相依
- [Story] 標籤 = 任務歸屬的 user story
- 每個 user story 自身可獨立完成與測試
- 測試必須**先紅後綠**
- 每完成一個任務或邏輯群組即 commit（commit 主旨英文、說明段繁中）
- 任一 checkpoint 皆可暫停以驗證故事完整性
- 避免：跨 story 的硬相依、無聲修改既有黃金檔、引入額外第三方依賴（簡潔優先；本階段只新增 openpyxl）

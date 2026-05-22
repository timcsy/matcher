# Implementation Plan: 資料匯入（CSV / Excel）

**Branch**: `003-data-import` | **Date**: 2026-05-22 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-data-import/spec.md`

## Summary

新增 `src/matcher/data_import.py` 模組，提供 `load_roster_csv(path, template)` 與 `load_roster_xlsx(path, template, sheet=None)` 兩個入口；皆回傳與既有 YAML 路徑等價的 `Roster` 物件。CLI 新增 `--roster-csv` / `--roster-xlsx` / `--sheet` 參數，與既有 `--roster <yaml>` 三組互斥。模板 `AttributeDecl` 新增選填 `aliases: list[str]`；兩個內建模板補上中文 aliases。audit schema 升級 v1.1 → v1.2 新增 `import_metadata`（可為 null）。新增依賴：`openpyxl`。

## Technical Context

**Language/Version**: Python 3.11+（沿用）
**Primary Dependencies**: Typer、PyYAML、pytest（沿用）+ **openpyxl ≥ 3.1**（新增，用於 .xlsx）
**Storage**: 無持久化（沿用）
**Testing**: pytest；新增三組 fixture（CSV UTF-8 / UTF-8-SIG / CP950、xlsx 單表、xlsx 多表）；CSV/Excel/YAML 三路徑等價以黃金檔比對
**Target Platform**: 跨平台 CLI（沿用）
**Project Type**: library + CLI（沿用）
**Performance Goals**: 基準場景匯入 + 媒合 ≤ 1 秒（含 openpyxl 載入）
**Constraints**: 跨版本確定性沿用；既有 82 測試 100% 通過（SC-007）；audit schema 升級 v1.2 須向後相容（v1.1 黃金檔重生為 v1.2，邏輯不變）
**Scale/Scope**: 名單 ≤ 1000 列、單一工作表

## Constitution Check

對齊 constitution v1.0.0 五原則：

| 原則 | 本計畫如何遵守 | 狀態 |
|---|---|---|
| I. 測試先行（TDD） | 每個 FR 對應 ≥ 1 個 pytest；CSV/Excel/YAML 等價以黃金檔比對；先紅後綠 | ✅ |
| II. 規格優先 | spec.md 無 [NEEDS CLARIFICATION]；本 plan 為技術選型集中點 | ✅ |
| III. 繁體中文文件 | 所有 spec/plan/research/contracts 為繁中；錯誤訊息三段式繁中（FR-017） | ✅ |
| IV. 簡潔優先 | 編碼偵測用啟發式 3 輪、不引入 chardet；單一 `data_import.py` 模組（不切 importers/ 子套件）；不支援 .xls / .xlsm / 多檔合併；對象端不匯入 | ✅ |
| V. 可觀測性 | import_metadata 進入稽核（編碼、工作表、行數）；4 種新錯誤類別 + 獨立 exit code；CLI 錯誤訊息三段式 | ✅ |

**Gate 評估**：通過，無 Complexity Tracking 條目。

## Project Structure

### Documentation (this feature)

```text
specs/003-data-import/
├── plan.md
├── spec.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cli.md
│   ├── csv-format.md
│   ├── xlsx-format.md
│   └── audit-schema-v1.2.json
├── checklists/
│   └── requirements.md
└── tasks.md      # 由 /speckit.tasks 建立
```

### Source Code (新增/修改)

```text
src/matcher/
├── data_import.py            # 新：load_roster_csv / load_roster_xlsx + 編碼偵測 + 型別轉換
├── template.py               # 修：AttributeDecl 新增 aliases 欄位
├── template_loader.py        # 修：parse_attribute_decl 讀取 aliases
├── templates/builtin/
│   ├── teacher-class.yaml    # 修：補中文 aliases
│   └── study-group.yaml      # 修：補中文 aliases
├── cli.py                    # 修：--roster-csv / --roster-xlsx / --sheet 參數 + 三組互斥擴充為四組
├── pipeline.py               # 修：MatcherInput 新增 import_metadata；run_match 傳入 audit
├── audit.py                  # 修：build_audit_record 接受 import_metadata；schema_version 升 1.2
├── errors.py                 # 修：新增 RosterDecodeError / RosterColumnMismatch / RosterTypeError / RosterSheetAmbiguous
                              # 既有檔案：filter / allocator / rng / roster / rules / io_yaml 不變

tests/
├── unit/
│   ├── test_data_import.py             # 新（編碼偵測 + 型別轉換 + alias 對齊）
│   └── （既有 5 檔不變）
├── integration/
│   ├── test_csv_import.py              # 新（CSV 三編碼、三路徑等價）
│   ├── test_xlsx_import.py             # 新（單表、多表、--sheet）
│   ├── test_import_errors.py           # 新（4 種錯誤情境）
│   ├── test_csv_preferences_reject.py  # 新（CSV preferences 在 M0 拒絕）
│   ├── test_backward_compat_v003.py    # 新（既有路徑仍可用）
│   └── （既有檔案不變）
└── golden/
    ├── teacher-class-baseline.audit.json    # 既有；audit schema 升 v1.2 需重生
    ├── teacher-class-template.audit.json    # 既有；模板加 aliases + schema 升 v1.2 需重生
    ├── study-group-template.audit.json      # 既有；同上需重生
    ├── teacher-class-csv.audit.json         # 新（CSV 路徑黃金檔）
    └── study-group-xlsx.audit.json          # 新（xlsx 路徑黃金檔）

examples/
├── teacher-class/
│   ├── roster.csv                 # 新（UTF-8 BOM、中文表頭）
│   └── roster.xlsx                # 新（單一工作表）
└── study-group/
    ├── roster.csv                 # 新
    └── roster.xlsx                # 新（多工作表示範）
```

**Structure Decision**：匯入層為「YAML 載入器之外的第二條入口」；產出與 YAML 路徑等價的 `Roster` 物件後即匯入既有 pipeline，**過濾／分配引擎完全不變**。CLI 新增三參數但維持同一個 `run_cmd` 函式（不切子應用）。新增依賴 `openpyxl` 僅用於 .xlsx；CSV 走 stdlib。

## Complexity Tracking

> Constitution Check 全部通過，本段保留空白。

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| （無）| | |

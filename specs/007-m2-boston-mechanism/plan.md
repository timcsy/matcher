# Implementation Plan: M2 Boston 分配機制（層級填滿）

**Branch**: `007-m2-boston-mechanism` | **Date**: 2026-05-24 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/007-m2-boston-mechanism/spec.md`

## Summary

在 `src/matcher/allocator.py` 新增 `allocate_m2(qualified_set, preferences_map, capacities, rng, role_order)`；`pipeline.py` dispatch 擴充 M2 分支；錯誤類別 `M1RequiresPreferences` 重新命名為 `MechanismRequiresPreferences`（exit 40 不變，保留 alias 維持向後相容）；`allocation_trace` 條目新增可選欄位 `tie_break_random_index`（M0/M1/M2 非超額為 null）。**無新依賴**、**不升 audit schema 版本**（保持 v1.3，僅新增可選欄位）；Web 層完全不動。

## Technical Context

**Language/Version**: Python 3.11+（沿用）
**Primary Dependencies**: 沿用（無新增）
**Storage**: 無新增
**Testing**: pytest；新增 unit（M2 演算法 + 超額抽籤行為）+ integration（CLI --mechanism M2、向後相容、6 黃金檔重生）
**Target Platform**: 跨平台 CLI（沿用）
**Project Type**: library + CLI + Web App（Web 不變）
**Performance Goals**: M2 處理 9 學生場景 < 1 秒（沿用既有效能標準）
**Constraints**: 既有 188 測試 100% 通過（SC-004）；audit schema v1.3 不升版本；M0/M1 邏輯不變
**Scale/Scope**: 同階段 4a；roles ≤ 1000、targets ≤ 100、層級 ≤ 10

## Constitution Check

對齊 constitution v1.0.0 五原則：

| 原則 | 本計畫如何遵守 | 狀態 |
|---|---|---|
| I. 測試先行（TDD） | 每個 FR 對應 ≥ 1 個 pytest；先寫 M2 演算法的單元測試（紅）→ 實作（綠） | ✅ |
| II. 規格優先 | spec.md 無 [NEEDS CLARIFICATION]；本 plan 為技術選型集中點 | ✅ |
| III. 繁體中文文件 | 所有文件繁中（FR-012） | ✅ |
| IV. 簡潔優先 | 無新增依賴；不引入學術變體（DA、TTC）；alias 而非雙錯誤類別 | ✅ |
| V. 可觀測性 | audit 完整記錄層級、tie-break 隨機 index；訊息明確 | ✅ |

**Gate 評估**：通過，無 Complexity Tracking 條目。

## Project Structure

### Documentation (this feature)

```text
specs/007-m2-boston-mechanism/
├── plan.md
├── spec.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cli.md
│   └── audit-schema-v1.3-extended.json
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Source Code (新增/修改)

```text
src/matcher/
├── allocator.py                  # 修：新增 allocate_m2；既有 m0/m1 不變
├── pipeline.py                   # 修：dispatch 新增 M2 分支；通用化拒絕訊息
├── audit.py                      # 修：build_audit_record 在 M0/M1 路徑下 trace 新增 tie_break_random_index: null
├── errors.py                     # 修：`M1RequiresPreferences` 重新命名為 `MechanismRequiresPreferences`；保留 alias
├── cli.py                        # 修：--mechanism 接受 M2
└── （核心 rules/filter/rng/roster/template/data_import/template_loader 不變）

src/matcher/web/                  # 完全不變

tests/
├── unit/
│   ├── test_allocator_m2.py      # 新（M2 演算法 + 超額抽籤）
│   └── （既有 unit 不變）
├── integration/
│   ├── test_cli_mechanism_m2.py  # 新（M2 跑通 + 黃金檔比對）
│   ├── test_m2_reject.py         # 新（M2 + 空 prefs 拒絕 + 通用訊息）
│   └── （既有 integration 不變）
└── golden/
    ├── study-group-m2.audit.json # 新（M2 路徑黃金檔）
    └── 既有 6 個重生（新增 tie_break_random_index: null）：
        ├── teacher-class-baseline.audit.json
        ├── teacher-class-template.audit.json
        ├── study-group-template.audit.json
        ├── teacher-class-csv.audit.json
        ├── study-group-xlsx.audit.json
        └── study-group-m1.audit.json
```

**Structure Decision**：
- **M2 與 M0/M1 同檔**：三者共用 SeededRandom 與規範化 helpers；不切子套件（簡潔優先）
- **錯誤類別重新命名 + alias**：`MechanismRequiresPreferences` 為主名；`M1RequiresPreferences = MechanismRequiresPreferences`（同類別別名）以維持既有 import 可用
- **audit schema 不升版本**：新增可選欄位 `tie_break_random_index` 為「新增可選欄位 + null」的最節制版本；既有測試斷言皆不需要改 schema version
- **既有 6 黃金檔重生**：批次一次完成；diff 應僅顯示每筆 allocation_trace 條目新增 `tie_break_random_index: null` 一行

## Complexity Tracking

> Constitution Check 全部通過，本段保留空白。

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| （無）| | |

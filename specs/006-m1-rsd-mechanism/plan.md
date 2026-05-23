# Implementation Plan: M1 RSD 分配機制（隨機輪流挑）

**Branch**: `006-m1-rsd-mechanism` | **Date**: 2026-05-23 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/006-m1-rsd-mechanism/spec.md`

## Summary

在既有 `src/matcher/allocator.py` 新增 `allocate_m1(qualified_set, preferences_map, capacities, rng)`；`pipeline.py` 依 `MatcherInput.mechanism` 分派到 M0 或 M1。M1 演算法：以 SeededRandom + Fisher–Yates 對 role list 洗牌得處理順序，再依序逐位選「資格集合 ∩ 仍有名額志願」最高志願（無則從資格集合內有名額者抽一）。audit schema 升 v1.3 加 `processing_order`（M0 為 null）與 `allocation_trace` 條目可選 `preference_rank`。CLI 加 `--mechanism M0|M1` 選項。**無新依賴**；不動 Web 層；既有 5 個黃金檔重生（diff 僅 schema_version + null 欄位）。

## Technical Context

**Language/Version**: Python 3.11+（沿用）
**Primary Dependencies**: 沿用（無新增）
**Storage**: 無新增
**Testing**: pytest；新增 unit 測試（allocator_m1 演算法）+ integration 測試（CLI --mechanism、向後相容、黃金檔重生）
**Target Platform**: 跨平台 CLI（沿用）
**Project Type**: library + CLI + Web App（Web 不變）
**Performance Goals**: M1 處理 9 學生場景 < 1 秒（沿用既有效能標準）
**Constraints**: 既有 169 測試 100% 通過（SC-005）；audit schema v1.2→v1.3 為非破壞性升版；M0 路徑邏輯不變
**Scale/Scope**: 同階段 1；roles ≤ 1000、targets ≤ 100

## Constitution Check

對齊 constitution v1.0.0 五原則：

| 原則 | 本計畫如何遵守 | 狀態 |
|---|---|---|
| I. 測試先行（TDD） | 每個 FR 對應 ≥ 1 個 pytest；先寫 M1 演算法的單元測試（紅）→ 實作（綠） | ✅ |
| II. 規格優先 | spec.md 無 [NEEDS CLARIFICATION]；本 plan 為技術選型集中點 | ✅ |
| III. 繁體中文文件 | 所有 spec/plan/research/contracts 為繁中；錯誤訊息、稽核紀錄繁中（FR-013） | ✅ |
| IV. 簡潔優先 | 無新增依賴；M1 與 M0 同檔（不切子套件）；無學術變體；不引入 strategyproof 證明等多餘抽象 | ✅ |
| V. 可觀測性 | audit 完整記錄處理順序、每人選擇、preference_rank；新錯誤類別 `M1RequiresPreferences` | ✅ |

**Gate 評估**：通過，無 Complexity Tracking 條目。

## Project Structure

### Documentation (this feature)

```text
specs/006-m1-rsd-mechanism/
├── plan.md
├── spec.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cli.md
│   └── audit-schema-v1.3.json
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Source Code (新增/修改)

```text
src/matcher/
├── allocator.py                  # 修：新增 allocate_m1；既有 allocate_m0 不變
├── pipeline.py                   # 修：依 mechanism dispatch；M1 + 空 prefs → 拒絕
├── audit.py                      # 修：build_audit_record 接 processing_order；schema v1.3
├── errors.py                     # 修：新增 M1RequiresPreferences（exit 40）
├── cli.py                        # 修：--mechanism 從固定接受 M0/M1
└── （核心 rules/filter/rng/roster/template/data_import/template_loader 完全不變）

src/matcher/web/                  # Web 層完全不變

tests/
├── unit/
│   ├── test_allocator_m1.py      # 新（M1 演算法 + Fisher-Yates 處理順序）
│   ├── test_pipeline_dispatch.py # 新（mechanism dispatch + 拒絕邏輯）
│   └── （既有 unit 不變）
├── integration/
│   ├── test_cli_mechanism_m1.py  # 新（--mechanism M1 + study-group prefs CSV）
│   ├── test_m0_backward_compat.py # 新（既有 M0 路徑 + audit schema v1.3 + null 欄位）
│   └── （既有 integration 不變）
└── golden/
    ├── study-group-m1.audit.json # 新（M1 路徑黃金檔）
    └── 既有 5 個重生為 v1.3：
        ├── teacher-class-baseline.audit.json
        ├── teacher-class-template.audit.json
        ├── study-group-template.audit.json
        ├── teacher-class-csv.audit.json
        └── study-group-xlsx.audit.json

examples/
└── study-group/
    └── roster-m1.csv             # 新（含 preferences 欄位，用於 M1 演示）
```

**Structure Decision**：
- **M1 與 M0 同檔**：兩者皆是 `allocate_*` 函式、共用 SeededRandom 與 Fisher-Yates；不切子套件（簡潔優先；切的門檻是「第三個機制」）
- **mechanism dispatch 在 pipeline.py**：兩個分派分支（M0、M1）+ 拒絕邏輯（M1 + 空 prefs → 拒絕；M0 + 非空 prefs → 既有拒絕）
- **錯誤類別新增於 errors.py**：`M1RequiresPreferences`（exit 40）；不與既有 30s 系列衝突
- **黃金檔重生為兩條：**
  - 4 個 M0 路徑（baseline/teacher-class-template/teacher-class-csv/study-group-template/study-group-xlsx）→ schema v1.3 + processing_order: null
  - 1 個新 M1 路徑（study-group-m1）→ 完整 M1 audit
- **CLI**：`matcher run --mechanism M0|M1`（預設 M0 維持向後相容）

## Complexity Tracking

> Constitution Check 全部通過，本段保留空白。

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| （無）| | |

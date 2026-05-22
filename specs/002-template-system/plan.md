# Implementation Plan: 模板系統（Template System）

**Branch**: `002-template-system` | **Date**: 2026-05-22 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-template-system/spec.md`

## Summary

新增模板層級抽象，把屬性 schema、規則、UI 欄位宣告、報告欄位宣告打包成單一可分享的 YAML 檔。建立 2 個內建模板（teacher-class、study-group），擴充 CLI 為 `matcher template list/show/export` 三個子命令並於 `matcher run` 接受 `--template` / `--template-file`。所有實作沿用階段 1 的技術棧；新增 `Template` 資料模型、`template_loader` 模組、`template_snapshot` 進入稽核紀錄並保持逐位元組可重現。

## Technical Context

**Language/Version**: Python 3.11+（沿用階段 1）
**Primary Dependencies**: Typer、PyYAML、pytest（沿用，無新增）
**Storage**: 內建模板存於套件資源 `src/matcher/templates/builtin/*.yaml`；自訂模板由使用者提供路徑
**Testing**: pytest；新增黃金檔 `tests/golden/teacher-class-template.audit.json`、`tests/golden/study-group-template.audit.json`
**Target Platform**: 跨平台 CLI（沿用）
**Project Type**: library + CLI（沿用）
**Performance Goals**: 模板載入 + 媒合執行 ≤ 階段 1 的同等場景時間 + 100ms 內（模板載入應接近零成本）
**Constraints**: 跨版本確定性沿用（含 `template_snapshot`）；既有 48 測試 100% 通過（SC-007）；不破壞 audit-schema 既有欄位
**Scale/Scope**: 階段 2 範圍——內建模板 ≤ 10 個、單一模板的規則 ≤ 100 條（沿用階段 1）

## Constitution Check

對齊 constitution v1.0.0 五原則：

| 原則 | 本計畫如何遵守 | 狀態 |
|---|---|---|
| I. 測試先行（TDD） | 每個 FR 對應 ≥ 1 個 pytest；新增模板載入器、CLI 子命令、template_snapshot 重現性、向後相容測試皆先寫測試。 | ✅ |
| II. 規格優先 | spec.md 無 [NEEDS CLARIFICATION]；本 plan 為技術選型集中點。 | ✅ |
| III. 繁體中文文件 | 所有 spec/plan/research/contracts 為繁中；模板內 description / ui_fields[].label 等可讀文字為繁中（FR-015）。 | ✅ |
| IV. 簡潔優先 | 無新增第三方依賴；不引入模板繼承、版本遷移、多語系；模板繪製/報告渲染留給階段 3。 | ✅ |
| V. 可觀測性 | template_snapshot 進入稽核紀錄；模板載入錯誤為明確類別（4 種以上）；CLI 提供 list/show 讓使用者隨時檢視當前狀態。 | ✅ |

**Gate 評估**：通過，無 Complexity Tracking 條目。

## Project Structure

### Documentation (this feature)

```text
specs/002-template-system/
├── plan.md
├── spec.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cli.md
│   ├── template-schema.yaml
│   └── audit-schema-v1.1.json
├── checklists/
│   └── requirements.md
└── tasks.md      # 由 /speckit.tasks 建立
```

### Source Code (新增/修改)

```text
src/matcher/
├── template.py              # 新：Template / TemplateRegistry 模型、parse_template
├── template_loader.py       # 新：載入內建/外部模板、schema_version 驗證
├── templates/builtin/       # 新：內建模板資源
│   ├── teacher-class.yaml
│   └── study-group.yaml
├── cli.py                   # 修：新增 template 子應用、--template / --template-file 參數
├── pipeline.py              # 修：MatcherInput 接受 Template；audit 加 template_snapshot
├── audit.py                 # 修：build_audit_record 接受 template 並輸出 template_snapshot
├── errors.py                # 修：新增 TemplateNotFound / UnknownSchemaVersion / TemplateMissingField / TemplateConflict
└── io_yaml.py               # 修：補上 load_template
                             # 既有檔案：errors / filter / allocator / rng / roster / rules 不變

tests/
├── unit/
│   ├── test_template.py             # 新
│   ├── test_template_loader.py      # 新
│   └── （既有檔案不變）
├── integration/
│   ├── test_template_cli.py         # 新（list / show / export）
│   ├── test_template_run.py         # 新（--template / --template-file 跑通 + 黃金檔）
│   ├── test_template_export_import.py  # 新（匯出→匯入逐位元組相同）
│   ├── test_template_preferences_reject.py  # 新（US3 對應）
│   ├── test_backward_compatibility.py       # 新（SC-007）
│   └── （既有檔案不變）
└── golden/
    ├── teacher-class-template.audit.json    # 新
    ├── study-group-template.audit.json      # 新
    └── teacher-class-baseline.audit.json    # 既有；需更新（audit schema 加了 template_snapshot 欄位）

examples/
├── teacher-class/           # 既有；新增 template-derived expected.audit.json
└── study-group/             # 新
    ├── roster.yaml
    ├── roster-with-preferences.yaml   # 為 US3 拒絕測試而設
    └── expected.audit.json
```

**Structure Decision**：模板層為「規則 + 名單之上的合成層」；既有過濾／分配引擎不變，只在 `pipeline.run_match` 入口加分支：若輸入含 Template，則由 Template 取出 ruleset；audit 一律含 `template_snapshot`（無模板時為 `null`）。CLI 採 Typer 子應用 `matcher template`，三個子命令 list / show / export。

## Complexity Tracking

> Constitution Check 全部通過，本段保留空白。

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| （無）| | |

# Implementation Plan: 移除 default_targets 概念

**Branch**: `013-remove-default-targets` | **Date**: 2026-05-25 | **Spec**: [spec.md](./spec.md)

## Summary

把 `default_targets` 機制從 data model（Template dataclass + audit schema）與內建範本徹底移除。
配對時的對象一律由「UI 填名單頁」或「CSV 旁檔 `.targets.yaml`」提供，使用者透明可見、模板專注規則。

技術手段：(1) 拔 `Template.default_targets` 欄位、(2) `data_import._load_targets` 移除 template fallback、
(3) audit schema 升 v1.4 移除 `template_snapshot.default_targets`、(4) 兩個內建範本 yaml 拔除該段、
(5) 補 examples/*/roster.targets.yaml、(6) 移除 UI fill 頁的 `requires_targets` 條件分支、
(7) 所有受影響測試補 sidecar 或調整斷言。

## Technical Context

**Language/Version**: Python 3.11+（沿用）
**Primary Dependencies**: 沿用（無新增）—— Typer、FastAPI、Jinja2、PyYAML、openpyxl、pytest、httpx[dev]
**Storage**: 沿用 `data/matches/` 純 JSON + `data/templates/` YAML；本 feature 新增 `examples/*/roster.targets.yaml` 範例旁檔
**Testing**: pytest（沿用），既有 342 測試 + 本 feature 新增測試
**Target Platform**: Linux / macOS server（沿用）
**Project Type**: Web + CLI 混合（沿用 Option 2 結構）
**Performance Goals**: 沿用（與既有相同；無新增運算路徑）
**Constraints**:
- audit schema_version 升 v1.4（不向下相容於「期待讀到 template_snapshot.default_targets」的舊讀者）
- 舊 v1.3 紀錄 read-only viewer 仍能讀（會忽略 default_targets 鍵）
- CLI 缺旁檔 → 明確錯誤訊息，非預設 fallback
**Scale/Scope**: 動到 15+ 測試檔；core 變動約 5 個檔（template.py、template_loader.py、data_import.py、audit.py、web/template_form.py）

## Constitution Check

### 原則對照

| 原則 | 評估 | 備註 |
|---|---|---|
| I. TDD | ✅ 通過 | 每個 task 先寫測試（紅）→ 改實作（綠）→ 重構；schema 升版以 audit JSON 斷言為紅 |
| II. 規格優先 | ✅ 通過 | spec.md 已通過 quality checklist；plan/tasks 依序產出 |
| III. 繁體中文 | ✅ 通過 | 所有文件繁體中文；錯誤訊息為使用者面文字也是繁體 |
| IV. 簡潔（YAGNI）| ✅ 通過 | 純移除既有功能；不引入新抽象、無遷移工具（spec.md Assumption 已排除）|
| V. 可觀測性 | ✅ 通過 | 新錯誤訊息含明確檔名建議；audit schema_version 公開揭露版本 |

**結果**：所有 gate 通過，無 Complexity Tracking 條目。

## Project Structure

### Documentation

```text
specs/013-remove-default-targets/
├── plan.md              # 本檔
├── spec.md              # 已有
├── research.md          # Phase 0 輸出
├── data-model.md        # Phase 1 輸出
├── quickstart.md        # Phase 1 輸出
├── contracts/           # Phase 1 輸出
│   ├── template-schema.md       # Template dataclass + YAML 結構契約
│   └── audit-schema-v1.4.md     # audit JSON schema 升版契約
└── tasks.md             # /speckit.tasks 產出
```

### Source Code

```text
src/matcher/
├── template.py                  # ← 移除 Template.default_targets 欄位
├── template_loader.py           # ← parse 忽略 default_targets，dump 不輸出
├── data_import.py               # ← _load_targets 一律要 sidecar
├── audit.py                     # ← schema_version → "1.4"，template_snapshot 不含 default_targets
├── templates/builtin/
│   ├── teacher-class.yaml       # ← 拔 default_targets:
│   └── study-group.yaml         # ← 拔 default_targets:
└── web/
    ├── template_form.py         # ← 拔 default_targets 寫入分支
    ├── roster_form.py           # ← assemble_targets_yaml_bytes 不再有 None 分支（總是回 bytes 或 None 表「未填」）
    ├── routes/match.py          # ← /match/run-from-form 對「未填對象」一律 400
    ├── routes/pages.py          # ← 範本詳細頁不再顯示「預設對象」段
    └── templates/
        ├── roster_form_fill.html  # ← 移除 {% if requires_targets %} 條件
        └── template_detail.html   # ← 移除「預設對象」展示段

examples/
├── teacher-class/
│   ├── roster.csv               # 既有
│   └── roster.targets.yaml      # ★ 新增
└── study-group/
    ├── roster.csv               # 既有
    ├── roster.xlsx              # 既有
    └── roster.targets.yaml      # ★ 新增

tests/                           # 大量補 sidecar fixture 或調整斷言
├── unit/
│   ├── test_template_loader.py
│   ├── test_template_form_assembly.py
│   └── test_roster_form_assemble.py
└── integration/
    ├── test_csv_import.py
    ├── test_web_new_match.py
    ├── test_web_roster_fill_basic.py
    ├── test_web_roster_fill_targets.py
    ├── test_match_rerun_from_snapshot.py
    └── ... （15+ 測試檔，詳見 tasks）
```

**Structure Decision**：沿用既有 Web + CLI 結構（feature 004 起）；本 feature 不增加新目錄，純粹拔欄位 + 改測試。

## Complexity Tracking

無違規，不適用。

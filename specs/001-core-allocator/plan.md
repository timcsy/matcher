# Implementation Plan: 核心媒合引擎（library + CLI）

**Branch**: `001-core-allocator` | **Date**: 2026-05-22 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-core-allocator/spec.md`

## Summary

實作純函式的媒合核心：給定規則檔（YAML）、名單檔（YAML）、整數 seed 與可選的 preferences 參數，依序輸出（a）資格集合、（b）以 M0 純抽籤產生的最終配對、（c）可重現的 JSON 稽核紀錄。技術走 Python 3.11+，CLI 用 Typer，測試用 pytest，YAML 解析用 PyYAML，隨機性用 stdlib `random.Random(seed)` 搭配顯式 Fisher–Yates 洗牌以確保跨版本可重現。

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Typer（CLI）、PyYAML（YAML 解析）、pytest（測試）；不額外引入 schema / validation 套件，所有結構化驗證在 `rules.py` / `roster.py` 內以純 Python 完成
**Storage**: 無持久化資料庫；輸入為使用者提供之 YAML 檔，輸出為標準輸出與 JSON 檔
**Testing**: pytest（單元 + 整合）；契約測試以 JSON 黃金檔比對稽核紀錄逐位元組相同
**Target Platform**: 跨平台 CLI（macOS / Linux / Windows）；Python 3.11/3.12 皆需通過 CI
**Project Type**: library + CLI（單一 Python 套件 `matcher`，附 `matcher` 命令）
**Performance Goals**: 基準場景（10 老師、5 班級、容量 2）於一般筆電 < 5 秒（SC-002）；無需高吞吐
**Constraints**: 跨版本確定性——同樣 (規則 + 名單 + seed + preferences) 在 Python 3.11 與 3.12 下產出逐位元組相同的稽核紀錄（SC-001）；不可使用系統時鐘或全域 `random`
**Scale/Scope**: 階段 1 範圍——名單 ≤ 1000 人、規則 ≤ 100 條；不為更大規模做優化

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

對齊 constitution v1.0.0 的五條原則：

| 原則 | 本計畫如何遵守 | 狀態 |
|---|---|---|
| I. 測試先行（TDD） | 每個 FR 對應至少一個 pytest 測試；先寫測試（紅）→ 實作（綠）→ 重構。golden-file 契約測試確保 SC-001 可重現性。 | ✅ |
| II. 規格優先 | 本 plan 基於已完成的 spec.md（無 [NEEDS CLARIFICATION]）；技術選型集中在 plan，spec 保持技術中立。 | ✅ |
| III. 繁體中文文件 | 所有規格、plan、research、data-model、quickstart、commit 說明段皆為繁中；程式識別字、檔名、commit 主旨用英文。 | ✅ |
| IV. 簡潔優先 | 不過早抽象「模板系統」（屬階段 2）；不為大規模優化；最小相依集（Typer / PyYAML / pytest）；不引入 ORM、依賴注入框架、自訂 DSL parser。 | ✅ |
| V. 可觀測性 | 過濾／分配為兩個純函式介面；錯誤以明確類別（`QualifiedSetEmpty`、`CapacityShortage`…）回報；稽核紀錄為決策路徑的可重播紀錄。 | ✅ |

**Gate 評估**：通過，無 Complexity Tracking 條目。

## Project Structure

### Documentation (this feature)

```text
specs/001-core-allocator/
├── plan.md              # 本檔（/speckit.plan 產出）
├── spec.md              # 規格
├── research.md          # Phase 0 產出（技術選型理由）
├── data-model.md        # Phase 1 產出（實體與型別）
├── quickstart.md        # Phase 1 產出（最小可跑教學）
├── contracts/           # Phase 1 產出（CLI 介面、檔案 schema、稽核 schema）
│   ├── cli.md
│   ├── rules-schema.yaml
│   ├── roster-schema.yaml
│   └── audit-schema.json
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 產出（由 /speckit.tasks 建立，本指令不產生）
```

### Source Code (repository root)

```text
src/matcher/
├── __init__.py
├── filter.py            # 過濾階段：規則 + 名單 → 資格集合
├── allocator.py         # 分配階段（M0 純抽籤）：資格集合 + seed → 配對
├── rules.py             # 規則模型、表達式評估（=、AND/OR/NOT、≥/≤/IN）
├── roster.py            # 名單模型（角色、對象、容量）
├── audit.py             # 稽核紀錄組裝與序列化
├── errors.py            # 明確錯誤類別
├── rng.py               # seedable RNG 與顯式 Fisher–Yates
├── io_yaml.py           # YAML 載入與輸入驗證
└── cli.py               # Typer 應用程式入口

tests/
├── unit/                # 各模組單元測試
│   ├── test_rules.py
│   ├── test_filter.py
│   ├── test_allocator.py
│   ├── test_rng.py
│   └── test_audit.py
├── integration/         # 端對端 CLI 測試
│   ├── test_baseline.py        # 教師-班級基準場景
│   ├── test_edge_cases.py      # 七種邊界情境
│   └── test_reproducibility.py # 同輸入產出位元組相同
└── golden/                     # 黃金檔
    └── teacher-class-baseline.audit.json

examples/
└── teacher-class/
    ├── rules.yaml
    ├── roster.yaml
    └── expected.audit.json

pyproject.toml
README.md
```

**Structure Decision**: 單一 Python 套件 `matcher`，library 與 CLI 共存於同一套件；CLI 透過 Typer 以 `matcher` 命令暴露功能。`examples/` 內附基準場景的可執行資料與預期稽核紀錄，作為 quickstart 與 SC-002 的驗證材料。

## Complexity Tracking

> Constitution Check 全部通過，本段保留空白。

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| （無）| | |

# Implementation Plan: Web UI 機制選擇 + 結果頁志願展示

**Branch**: `008-web-mechanism-prefs` | **Date**: 2026-05-24 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/008-web-mechanism-prefs/spec.md`

## Summary

把 M1（RSD）/ M2（Boston）機制接上 Web UI：`/match/new` 表單新增「分配機制」下拉（M0/M1/M2，預設 M0），結果頁顯示機制名稱、處理順序、志願排名欄；個別查詢頁在 M1/M2 路徑下顯示「您被分到第幾志願」三種文案。**所有變更限於 `src/matcher/web/`**——核心模組 0 改動（教訓 7）。技術上是純樣板 + routes + form 工作，不引入新依賴、不升 audit schema、不引入新錯誤類別。

## Technical Context

**Language/Version**: Python 3.11+（沿用）
**Primary Dependencies**: 沿用（fastapi、uvicorn[standard]、jinja2、python-multipart、PyYAML、openpyxl、Typer、pytest、httpx[dev]）——**無新增**
**Storage**: `data/matches/` 純 JSON（沿用）；無資料庫
**Testing**: pytest + FastAPI TestClient（httpx），整合測試 + 樣板渲染斷言；沿用既有 FORBIDDEN_TECHNICAL_TOKENS 正則
**Target Platform**: Linux server / macOS（uvicorn）；瀏覽器端純 HTML + HTMX（已用）
**Project Type**: Library + CLI + Web service 三入口（library 核心、Typer CLI、FastAPI Web）
**Performance Goals**: 沿用既有（單機 ≤ 100 角色 ≤ 1 秒）；本 feature 為純展示變動，無新效能需求
**Constraints**: **不動 `src/matcher/{rules,filter,allocator,pipeline,audit,errors,data_import,template_loader,rng,roster}`**；繁體中文文案；技術詞零容忍
**Scale/Scope**: ~5 個樣板修改 + 1 個 routes 修改 + ~6-8 個新增測試；估 ~150 LOC 變動

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 原則 | 狀態 | 說明 |
|---|---|---|
| I. TDD 不可妥協 | ✅ | 每個 user story 先寫整合 / 樣板 / 渲染測試，再實作；既有 210 測試持續綠 |
| II. 規格優先 | ✅ | spec → plan → tasks → implement 流程；spec.md 已確認 |
| III. 繁體中文文件 | ✅ | 所有 spec/plan/tasks/PR/commit 說明、UI 文案皆繁中 |
| IV. 簡潔優先 (YAGNI) | ✅ | 不引入新依賴、不升 schema、不抽象「fallback 文案渲染」（單一樣板 if/else 處理）；只在第三次重複出現時才考慮抽象 |
| V. 可觀測性 | ✅ | 錯誤透過既有 `MechanismRequiresPreferences` exit_code 40 結構化回報；Web 路徑沿用 admin 失敗頁；audit 五段保持可下載 |

**Gate 通過。** 無違反項。Complexity Tracking 段不需填寫。

## Project Structure

### Documentation (this feature)

```text
specs/008-web-mechanism-prefs/
├── plan.md              # 本檔
├── spec.md              # 規格（已完成）
├── research.md          # Phase 0 — 4 項決策摘要
├── data-model.md        # Phase 1 — UI 視圖模型（無持久層變動）
├── quickstart.md        # Phase 1 — 5 分鐘端到端跑通指引
├── contracts/
│   └── web-routes.md    # Phase 1 — HTTP 介面契約
├── checklists/
│   └── requirements.md  # ✓ PASS（spec 階段產出）
└── tasks.md             # Phase 2（/speckit.tasks 產出，不在 plan 階段）
```

### Source Code (repository root)

僅 `src/matcher/web/` 內變更：

```text
src/matcher/web/
├── routes/
│   └── match.py                  # ← 修改：POST /match/run 新增 mechanism 參數處理
├── templates/
│   ├── new_match.html            # ← 修改：新增「分配機制」下拉 + 說明
│   ├── match_result.html         # ← 修改：機制名稱、處理順序、志願排名欄（conditional）
│   ├── individual_view.html      # ← 修改：「您被分到第幾志願」段（conditional × 3 分支）
│   └── partials/                 # （視需要新增小片段，目前評估不必要）
└── humanize.py                   # ← 視情況新增「mechanism → 顯示名」「rank → 文案」純函式

tests/integration/
├── test_web_mechanism_form.py        # ← 新增（US1）：表單下拉 + POST + 結果頁
├── test_web_individual_preference.py # ← 新增（US2）：個別查詢頁三分支文案
├── test_web_mechanism_reject.py      # ← 新增（US3）：M1/M2 + 空 prefs 拒絕路徑
└── test_web_cli_audit_equivalence.py # ← 新增（SC-001）：Web/CLI 同 mechanism+seed bytewise 相等

tests/unit/
└── test_humanize_mechanism.py        # ← 視 humanize.py 是否新函式而定
```

**核心 0 改動**：`src/matcher/{rules,filter,allocator,pipeline,audit,errors,data_import,template_loader,rng,roster}.py` 完全不動。FR-011 + SC-007 由 git diff 與 CI 守住（tasks 階段加守護測試）。

**Structure Decision**：沿用既有 single-project 結構（`src/` + `tests/`），不切 backend/frontend——本專案 jinja2 server-rendered，無獨立前端。所有 Web 變動局限 `src/matcher/web/`。

## Complexity Tracking

> 無違反項。本段不適用。

# Implementation Plan: Web UI 直接填名單

**Branch**: `012-web-roster-form` | **Date**: 2026-05-25 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/012-web-roster-form/spec.md`

## Summary

`/match/new` 加「✏️ 直接填名單」入口；填寫頁依範本動態渲染角色（+ 必要時對象）欄位 + 加減行。M0 直接跑 pipeline；M1/M2 + 範本有 `preferences_schema` 透過 hidden inputs 機制接續 feature 009 `/match/preferences` 填志願頁。**核心 0 改動**——本 feature 在 Web 層把 UI 表單轉成 CSV bytes（in-memory）+ 既有 `data_import.load_roster_csv` 載入，產出 audit 與 CSV 上傳路徑 bytewise 等價。

## Technical Context

**Language/Version**: Python 3.11+（沿用）
**Primary Dependencies**: 沿用（fastapi、uvicorn、jinja2、python-multipart、PyYAML、openpyxl、Typer、pytest、httpx[dev]、weasyprint）+ Tailwind Play CDN + Alpine.js（CDN，無 build）——**無新增**
**Storage**: 沿用 `data/matches/` + `data/templates/`；UI 填的名單**不持久化**（in-memory CSV bytes 走既有路徑）
**Testing**: pytest + FastAPI TestClient；沿用 FORBIDDEN_TECHNICAL_TOKENS 正則
**Target Platform**: Linux / macOS uvicorn；瀏覽器端純 HTML + Alpine
**Project Type**: Library + CLI + Web service 三入口
**Performance Goals**: 20 角色 × 5 屬性的填寫頁 ≤ 100ms render；UI 填名單 → audit 與 CSV 路徑 bytewise 等價
**Constraints**:
- **不動核心** `src/matcher/{rules,filter,allocator,pipeline,audit,errors,data_import,template_loader,rng,roster}` — 限定 `src/matcher/web/`
- 繁中文案；技術詞零容忍
- 沿用 4d hidden inputs 機制（避免重複實作）
- list_str 簡化為「分號分隔單行 input」
**Scale/Scope**: ~5 個檔案變動（routes/match.py 加 endpoint + 1 個新樣板 + 1 個新 JS 段 + new_match.html 改三選一 + 既有測試 + 新測試）；估 ~350 LOC

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 原則 | 狀態 | 說明 |
|---|---|---|
| I. TDD 不可妥協 | ✅ | 每個 user story 先寫整合測試（UI 渲染、加減行 POST、M0 跑通、M1 銜接、Web/CSV bytewise 等價）；TDD 紅→綠 |
| II. 規格優先 | ✅ | spec → plan → tasks → implement |
| III. 繁體中文文件 | ✅ | 所有 spec/plan/tasks/PR/commit/UI 文案皆繁中 |
| IV. 簡潔優先 (YAGNI) | ✅ | 無新依賴；不持久化 UI 填的名單（in-memory 轉 CSV bytes 走既有路徑）；不做草稿儲存；不做 CSV+UI 混合；不重新發明 UI（沿用 feature 011 Alpine pattern） |
| V. 可觀測性 | ✅ | UI 表單錯誤經 data_import 結構化錯誤回報；audit 仍是位元組權威；技術詞零容忍守住「綠 ≠ 好」之外的字面 UX |

**Gate 通過。** 無違反項。Complexity Tracking 段不需填寫。

## Project Structure

### Documentation (this feature)

```text
specs/012-web-roster-form/
├── plan.md              # 本檔
├── spec.md              # 規格（已完成）
├── research.md          # Phase 0 — 5 項決策
├── data-model.md        # Phase 1 — UI 表單 view model + CSV 轉換邏輯
├── quickstart.md        # Phase 1 — 8 步驟端到端驗收
├── contracts/
│   └── web-routes.md    # Phase 1 — /match/new 改動 + 新 endpoint
├── checklists/
│   └── requirements.md  # ✓ PASS
└── tasks.md             # Phase 2（/speckit.tasks 產出）
```

### Source Code (repository root)

僅 `src/matcher/web/` 內變更：

```text
src/matcher/web/
├── routes/
│   └── match.py                              # ← 修改：new_match GET 加 mode=fill 分支；新增 POST /match/run-from-form 端點（UI 表單→CSV bytes→既有 pipeline）
├── templates/
│   ├── new_match.html                        # ← 改寫：三選一頁籤（upload / fill / from-record）；用 Alpine x-show
│   └── roster_form_fill.html                 # ← 新增：填寫頁（依範本動態渲染角色 + 對象）
└── static/
    └── roster_form.js                        # ← 新增：Alpine 元件管理角色 / 對象陣列、加減行、提交

tests/integration/
├── test_web_roster_fill_basic.py             # ← 新增（US1）：UI 填角色 → 跑通 → Web/CSV bytewise 等價
├── test_web_roster_fill_targets.py           # ← 新增（US2）：自訂範本無 default_targets → UI 填對象
└── test_web_roster_fill_m1_handoff.py        # ← 新增（US3）：M1 + 範本有 prefs schema → 跳 feature 009 填志願頁
```

**核心 0 改動**：`src/matcher/{rules,filter,allocator,pipeline,audit,errors,data_import,template_loader,rng,roster}.py` 完全不動。FR-010 / SC-006 由 git diff 守住。

**Structure Decision**：沿用既有結構；無新檔案夾。所有變動局限 `src/matcher/web/`。

## Complexity Tracking

> 無違反項。本段不適用。

# Implementation Plan: Web UI 動態填志願表單

**Branch**: `009-web-preferences-form` | **Date**: 2026-05-24 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/009-web-preferences-form/spec.md`

## Summary

讓 Web UI 在偵測到「模板含 `preferences_schema` + 上傳名單 prefs 全空 + 選 M1/M2」時，自動跳到「填志願」中介頁面：單張長表格、每位角色 `max_choices` 個下拉、選項為模板 `default_targets`。填完後組裝為 `Role.preferences` 走既有 pipeline，產出的 audit 與 CSV preferences 欄路徑 bytewise 相等。**核心 0 改動**——所有變更限於 `src/matcher/web/`。技術上是「既有 `/match/run` 端點偵測分支 + 新增 `/match/preferences` 中介端點 + 1 個新樣板 + hidden inputs 攜帶中介狀態」。

## Technical Context

**Language/Version**: Python 3.11+（沿用）
**Primary Dependencies**: 沿用（fastapi、uvicorn[standard]、jinja2、python-multipart、PyYAML、openpyxl、Typer、pytest、httpx[dev]）——**無新增**
**Storage**: `data/matches/` 純 JSON（沿用）；無資料庫；**填志願頁中介狀態不持久化**（hidden inputs 攜帶）
**Testing**: pytest + FastAPI TestClient；沿用既有 FORBIDDEN_TECHNICAL_TOKENS 正則模式
**Target Platform**: Linux server / macOS（uvicorn）；瀏覽器端純 HTML（無 JS framework）
**Project Type**: Library + CLI + Web service 三入口
**Performance Goals**: 50 學生 × 3 志願 = 150 下拉的填志願頁 render < 200ms（伺服器渲染、無 JS）
**Constraints**: **不動 `src/matcher/{rules,filter,allocator,pipeline,audit,errors,data_import,template_loader,rng,roster}`**；繁中文案；技術詞零容忍；hidden inputs 含 base64(roster bytes)，限於 5MB 上傳 → ~6.7MB base64，HTML 頁面可承受
**Scale/Scope**: ~5 個檔案變動（match.py routes + 1 個新樣板 + new_match.html 微調 + humanize 加 1 函式 + 4 個新測試檔）；估 ~300 LOC

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 原則 | 狀態 | 說明 |
|---|---|---|
| I. TDD 不可妥協 | ✅ | 每個 user story 先寫整合測試（GET 中介頁、POST 驗證、Web/CSV 等價）；TDD 紅→綠 |
| II. 規格優先 | ✅ | spec → plan → tasks → implement |
| III. 繁體中文文件 | ✅ | 所有 spec/plan/tasks/PR/commit 說明、UI 文案皆繁中 |
| IV. 簡潔優先 (YAGNI) | ✅ | 無新依賴；hidden inputs 取代 session（避免引入 session 機制與過期 GC）；不抽象「中介狀態管理」（單一檔內處理） |
| V. 可觀測性 | ✅ | 驗證失敗回填志願頁 + 友善訊息；中介狀態錯誤透過既有 error_page.html；audit 五段保持可下載；hidden inputs 內容於 POST 端點視為不可信、重做驗證 |

**Gate 通過。** 無違反項。Complexity Tracking 段不需填寫。

## Project Structure

### Documentation (this feature)

```text
specs/009-web-preferences-form/
├── plan.md              # 本檔
├── spec.md              # 規格（已完成）
├── research.md          # Phase 0 — 5 項決策
├── data-model.md        # Phase 1 — 表單與中介狀態 view model
├── quickstart.md        # Phase 1 — 7 分鐘端到端跑通指引
├── contracts/
│   └── web-routes.md    # Phase 1 — HTTP 介面契約（含新中介端點）
├── checklists/
│   └── requirements.md  # ✓ PASS（spec 階段產出）
└── tasks.md             # Phase 2（/speckit.tasks 產出）
```

### Source Code (repository root)

僅 `src/matcher/web/` 內變更：

```text
src/matcher/web/
├── routes/
│   └── match.py                              # ← 修改：/match/run 加入「跳填志願」分支；新增 /match/preferences POST 端點
├── humanize.py                               # ← 新增 target_summary(target) -> str 純函式
└── templates/
    └── preferences_form.html                 # ← 新增：填志願中介頁面（含候選對象段 + 表格 + 跳過按鈕 + hidden inputs）

tests/integration/
├── test_web_preferences_form_flow.py         # ← 新增（US1）：完整端到端（上傳 → 跳頁 → 填 → 結果）+ Web/CSV bytewise 等價
├── test_web_preferences_form_skip.py         # ← 新增（US2）：escape hatch + 各路徑判定
├── test_web_preferences_form_validation.py   # ← 新增（US1/US3）：同列重複、技術詞零容忍、無 default_targets 錯誤
└── test_web_preferences_form_scale.py        # ← 新增（SC-007）：50 學生 × 3 志願 規模測試

tests/unit/
└── test_humanize_target_summary.py           # ← 新增 target_summary 純函式單元測試
```

**核心 0 改動**：`src/matcher/{rules,filter,allocator,pipeline,audit,errors,data_import,template_loader,rng,roster}.py` 完全不動。FR-011 + SC-009 由 git diff 守住。

**Structure Decision**：沿用既有 single-project 結構；無新檔案夾。所有 Web 變動局限 `src/matcher/web/`。

## Complexity Tracking

> 無違反項。本段不適用。

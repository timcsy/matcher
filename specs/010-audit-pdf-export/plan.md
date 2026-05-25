# Implementation Plan: 稽核報告 PDF 匯出

**Branch**: `010-audit-pdf-export` | **Date**: 2026-05-24 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/010-audit-pdf-export/spec.md`

## Summary

加入 PDF 稽核報告匯出能力。Web 端新增 `GET /match/{rid}/report.pdf` + `GET /match/{rid}/role/{role_id}/report.pdf`；CLI 新增 `matcher report` 子指令。共用同一 PDF 渲染純函式 `render_match_report_pdf(audit, role_id=None) -> bytes`（位於 `src/matcher/web/pdf.py`）——用 WeasyPrint 渲染專為 A4 設計的 jinja2 樣板，嵌入 Noto Sans CJK TC 字體。**核心 0 改動**——新依賴僅 weasyprint；字體檔嵌入 `src/matcher/web/static/fonts/`；WeasyPrint 系統依賴缺失時 graceful degrade。

## Technical Context

**Language/Version**: Python 3.11+（沿用）
**Primary Dependencies**: 沿用 + **新增 weasyprint ≥ 60.0**（含 cssselect2、tinycss2、Pyphen 等遞移依賴皆純 Python；系統需 libpango-1.0、libcairo、harfbuzz）
**Storage**: 沿用 `data/matches/` 純 JSON；字體檔靜態於 `src/matcher/web/static/fonts/`（OFL 授權）
**Testing**: pytest + FastAPI TestClient + Typer CliRunner；新增 PDF 內容斷言（解 PDF 文字流 + 正則）；用 `pypdf`（dev only）做 PDF 內容檢索（如已能用 weasyprint 的 metadata 則優先）
**Target Platform**: Linux server / macOS（uvicorn）；瀏覽器端純 HTML 觸發下載
**Project Type**: Library + CLI + Web service 三入口
**Performance Goals**: 50 學生 × 3 志願 admin PDF 渲染 ≤ 2 秒（SC-006）；檔大小 ≤ 1 MB
**Constraints**: **不動 `src/matcher/{rules,filter,allocator,pipeline,audit,errors,data_import,template_loader,rng,roster}`**；`cli.py` 僅新增子指令 group、不動既有命令；繁中文案；技術詞零容忍延伸至 PDF；WeasyPrint 系統依賴缺失時 graceful degrade（503 / friendly CLI error）
**Scale/Scope**: ~6 個檔案變動（pdf.py 新檔 + 2 樣板新檔 + routes/match.py 加 2 endpoints + cli.py 加 1 子指令 + README 補說明）+ 1 個字體目錄 + 5 個新測試檔；估 ~450 LOC + ~10MB 字體 binary

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 原則 | 狀態 | 說明 |
|---|---|---|
| I. TDD 不可妥協 | ✅ | 每個 user story 先寫測試（PDF content、CLI exit code、Web 端點）；TDD 紅→綠 |
| II. 規格優先 | ✅ | spec → plan → tasks → implement |
| III. 繁體中文文件 | ✅ | 所有 spec/plan/tasks/PR/commit/UI/PDF 文案皆繁中 |
| IV. 簡潔優先 (YAGNI) | ✅ | 不抽象「PDF generator」介面——直接 weasyprint 函式呼叫；不做 logo/簽章/批次匯出（明確排除）；CLI 子指令獨立檔避免動 cli.py 既有結構 |
| V. 可觀測性 | ✅ | WeasyPrint 失敗 → 結構化錯誤回 503（Web）/ exit code ≠ 0（CLI）+ 明確繁中訊息；不靜默掩蓋；audit 仍是位元組權威 |

**新依賴揭露**（constitution 額外約束）：
- `weasyprint >= 60.0` — 唯一可重用既有 jinja2 樣板的成熟 Python PDF 函式庫
- 嵌入字體（Noto Sans CJK TC，~10MB）— 唯一保證跨機器中文渲染一致 + 可搜尋的方案

**Gate 通過。** Complexity Tracking 段不需填寫。

## Project Structure

### Documentation (this feature)

```text
specs/010-audit-pdf-export/
├── plan.md              # 本檔
├── spec.md              # 規格（已完成）
├── research.md          # Phase 0 — 6 項決策
├── data-model.md        # Phase 1 — PDF render input/output model
├── quickstart.md        # Phase 1 — 8 步驟端到端驗收
├── contracts/
│   ├── web-routes.md    # Phase 1 — 2 個新 HTTP 端點契約
│   └── cli-report.md    # Phase 1 — matcher report CLI 契約
├── checklists/
│   └── requirements.md  # ✓ PASS（spec 階段產出）
└── tasks.md             # Phase 2（/speckit.tasks 產出）
```

### Source Code (repository root)

```text
src/matcher/
├── web/
│   ├── pdf.py                                    # ← 新檔：render_match_report_pdf 純函式
│   ├── routes/match.py                           # ← 修改：新增 2 個 GET PDF 端點
│   ├── static/fonts/
│   │   ├── NotoSansCJKtc-Regular.otf            # ← 新增字體檔（OFL 授權）
│   │   ├── NotoSansCJKtc-Bold.otf               # ← 新增字體檔
│   │   └── OFL.txt                              # ← 授權檔
│   └── templates/
│       ├── pdf/
│       │   ├── match_report.html                # ← 新增：admin PDF 樣板（A4 列印版）
│       │   └── individual_report.html           # ← 新增：individual PDF 樣板
│       ├── match_result.html                    # ← 修改：加「下載 PDF 報告」按鈕
│       └── individual_view.html                 # ← 修改：加「下載我的報告 PDF」按鈕
└── cli_report.py                                 # ← 新檔：CLI `matcher report` 子指令（獨立於 cli.py）

# cli.py 修改：僅一行 app.add_typer(report_app, ...) 引入新子指令；不動既有 run / template 等

tests/integration/
├── test_web_pdf_admin.py                         # ← 新增（US1）：admin PDF 下載 + 內容斷言
├── test_web_pdf_individual.py                    # ← 新增（US2）：individual PDF 下載 + 隔離驗證
├── test_web_pdf_graceful_degrade.py              # ← 新增（FR-012/SC-010）：缺依賴 graceful degrade
├── test_cli_report.py                            # ← 新增（US3）：matcher report 指令
└── test_pdf_no_technical_tokens.py               # ← 新增（FR-007/SC-004）：PDF 文字技術詞驗證

tests/unit/
└── test_pdf_render.py                            # ← 新增：純函式 render_match_report_pdf 單元測試
```

**核心 0 改動**：`src/matcher/{rules,filter,allocator,pipeline,audit,errors,data_import,template_loader,rng,roster}.py` 完全不動。`cli.py` 僅 1 行加引入（保守起見），所有 CLI report 邏輯在 `cli_report.py`。FR-011 + SC-008 由 git diff 守住。

**Structure Decision**：沿用既有 single-project 結構；新增 `static/fonts/` 與 `templates/pdf/` 子目錄；新增 `cli_report.py` 兄弟檔。所有 Web 變動局限 `src/matcher/web/`；CLI 變動限於 `src/matcher/cli_report.py` + `cli.py` 1 行新增。

## Complexity Tracking

> 無違反項。本段不適用。

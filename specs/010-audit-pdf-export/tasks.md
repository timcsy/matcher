# Tasks: 稽核報告 PDF 匯出

**Feature**: 010-audit-pdf-export
**Branch**: `010-audit-pdf-export`
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

**TDD 強制**（constitution I）：每個 user story 內，測試任務 MUST 先寫並先紅後再實作。

> **新依賴**：`weasyprint >= 60.0`（pyproject 加入）+ Noto Sans CJK TC 字體檔（手動下載）。系統需 pango/cairo/harfbuzz（README 補說明）。

---

## Phase 1 — Setup

- [ ] T001 在 `pyproject.toml` `[project] dependencies` 新增 `weasyprint>=60.0`；執行 `uv sync` 確認可安裝
- [ ] T002 下載 Noto Sans CJK TC（Regular + Bold）`.otf` 檔至 `src/matcher/web/static/fonts/`，並放 `OFL.txt` 授權檔（從 https://github.com/notofonts/noto-cjk/raw/main/Sans/OTF/TraditionalChinese/ 取得；或用較小的 NotoSansTC-Regular/Bold.ttf subset）
- [ ] T003 在 `README.md` 「Web UI」段下新增「PDF 報告」子段，含系統依賴安裝指引（macOS / Debian）
- [ ] T004 在 `.gitignore` 確認 `*.pdf` **不被** ignore（避免測試產出檔被誤排除）；若已 ignore 則加 `!tests/**/*.pdf` 例外

---

## Phase 2 — Foundational

阻塞所有 user stories 的共用變更——PDF 純函式 + 例外類別 + 樣板骨架。

- [ ] T010 [P] 撰寫 `tests/unit/test_pdf_render.py::test_render_returns_pdf_bytes` —— 餵入最小 audit dict + record_meta，`render_match_report_pdf(...)` 回 bytes 開頭為 `b"%PDF-"`
- [ ] T011 [P] 撰寫 `tests/unit/test_pdf_render.py::test_render_individual_filters_by_role_id` —— role_id=S01 → PDF bytes 含「S01」、不含「S02」（用簡單字節搜尋而非 PDF 解析）
- [ ] T012 [P] 撰寫 `tests/unit/test_pdf_render.py::test_render_raises_value_error_on_missing_audit_keys` —— audit 缺 assignment → raise ValueError
- [ ] T013 [P] 撰寫 `tests/unit/test_pdf_render.py::test_render_raises_pdf_render_unavailable_when_no_weasyprint` —— monkey-patch `_WEASYPRINT_AVAILABLE=False` → raise PdfRenderUnavailable
- [ ] T014 新增 `src/matcher/web/pdf.py`：含 `PdfRenderUnavailable` 例外類別、`_WEASYPRINT_AVAILABLE` lazy flag、`render_match_report_pdf(audit, *, record_meta, role_id=None, template=None) -> bytes` 純函式骨架（先不接 weasyprint，僅 raise NotImplementedError 讓 T010-T013 紅）
- [ ] T015 新增 `src/matcher/web/templates/pdf/match_report.html` 樣板骨架——`@page A4` CSS、`@font-face` 引用本機字體、含 jinja2 變數（{{ record_id }}、{{ template_name }}、{{ mechanism_label }}、{{ allocation_rows }} 等）
- [ ] T016 新增 `src/matcher/web/templates/pdf/individual_report.html` 樣板骨架——同上但含 {{ role_name }}、{{ assigned_target_name }}、preference_rank 三分支文案
- [ ] T017 實作 `src/matcher/web/pdf.py::render_match_report_pdf`：嘗試 `from weasyprint import HTML, CSS`；失敗則 set `_WEASYPRINT_AVAILABLE=False`；成功則用 jinja2 Environment（從 `templates/pdf/` 載樣板）render HTML → `HTML(string=html, base_url=...).write_pdf()`
- [ ] T018 驗證 T010-T013 由紅轉綠

**Checkpoint**：純函式可從 audit dict 產出 PDF bytes；尚無 HTTP 端點。

---

## Phase 3 — User Story 1 (P1) 🎯 MVP：行政下載 admin 結果 PDF

**Goal**：Web 端點 `GET /match/{rid}/report.pdf` 可下載 admin PDF 含完整分配表。

**Independent Test**：跑 M2 媒合 → 結果頁點下載按鈕 → PDF 開啟、中文可搜尋、含分配表。

### Tests (TDD — 先紅)

- [ ] T020 [P] [US1] 撰寫 `tests/integration/test_web_pdf_admin.py::test_download_admin_pdf_returns_pdf_bytes` —— TestClient GET `/match/{rid}/report.pdf` 對成功 record，回 200 + Content-Type `application/pdf` + Content-Disposition attachment + bytes 開頭 `b"%PDF-"`
- [ ] T021 [P] [US1] 撰寫 `tests/integration/test_web_pdf_admin.py::test_admin_pdf_contains_record_id_and_mechanism_label` —— PDF bytes 中（解 stream）含 `<record_id>` 與「M2 Boston 層級填滿」
- [ ] T022 [P] [US1] 撰寫 `tests/integration/test_web_pdf_admin.py::test_admin_pdf_for_failed_record_shows_error` —— 失敗 record → PDF 仍 200 + 含「失敗」或錯誤類別字串
- [ ] T023 [P] [US1] 撰寫 `tests/integration/test_web_pdf_admin.py::test_admin_pdf_button_present_in_result_html` —— GET `/match/{rid}` HTML 含「下載 PDF 報告」+ `href="/match/{rid}/report.pdf"`
- [ ] T024 [P] [US1] 撰寫 `tests/integration/test_web_pdf_admin.py::test_admin_pdf_record_not_found` —— 404 對不存在的 record

### Implementation

- [ ] T025 [US1] 在 `src/matcher/web/routes/match.py` 新增 `GET /match/{record_id}/report.pdf` 端點——讀 record → 組 record_meta dict → 呼叫 `render_match_report_pdf(audit, record_meta=...)` → 回 `Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": ...})`；record 不存在 → 404；PdfRenderUnavailable → 503 + 友善訊息
- [ ] T026 [US1] 修改 `src/matcher/web/templates/match_result.html` ——「下載稽核紀錄」按鈕旁加 `<a class="btn btn-secondary" href="/match/{{ record.id }}/report.pdf">下載 PDF 報告</a>`
- [ ] T027 [US1] 補完 `templates/pdf/match_report.html`：標題段、紀錄資訊段、機制段、{% if processing_order_display %} 處理順序段、分配表（含志願排名欄 conditional）、頁尾稽核摘要
- [ ] T028 [US1] 完善 routes 內的 view model 組裝邏輯——用既有 `mechanism_label` + `preference_rank_display` + `processing_order_display` 工具函式
- [ ] T029 [US1] 執行 `uv run pytest tests/integration/test_web_pdf_admin.py tests/unit/test_pdf_render.py -q` 確認全綠

**Checkpoint US1 完成**：行政可從 Web 下載 admin PDF。

---

## Phase 4 — User Story 2 (P2)：當事人下載 individual PDF

**Goal**：個別查詢頁可下載只含自己的 PDF。

**Independent Test**：跑 M1 → 開 S01 個別頁 → 下載 PDF → 內容只含 S01 + 通過技術詞驗證。

### Tests (TDD — 先紅)

- [ ] T030 [P] [US2] 撰寫 `tests/integration/test_web_pdf_individual.py::test_download_individual_pdf_only_contains_own_data` —— PDF bytes 含 `S01`、不含 `S02`/`S03`...（用簡單 bytes search）
- [ ] T031 [P] [US2] 撰寫 `tests/integration/test_web_pdf_individual.py::test_individual_pdf_button_present_in_individual_view` —— individual_view.html 含「下載我的報告 PDF」連結
- [ ] T032 [P] [US2] 撰寫 `tests/integration/test_web_pdf_individual.py::test_individual_pdf_404_on_failed_record` —— failed record → 404
- [ ] T033 [P] [US2] 撰寫 `tests/integration/test_web_pdf_individual.py::test_individual_pdf_404_on_unknown_role` —— role_id 不在 roster → 404
- [ ] T034 [P] [US2] 撰寫 `tests/integration/test_pdf_no_technical_tokens.py::test_individual_pdf_no_forbidden_tokens` —— PDF bytes（轉成 latin-1 字串以 substring 比對）不含 `preference_rank`、`random_index`、`processing_order`、`filter_trace`、`allocation_trace`、`qualified_set`、`preferences_schema`、`default_targets`、`max_choices`、`preferred_order`

### Implementation

- [ ] T035 [US2] 在 `src/matcher/web/routes/match.py` 新增 `GET /match/{record_id}/role/{role_id}/report.pdf` 端點——沿用既有 individual_view 的 record + role 驗證邏輯；通過後呼叫 `render_match_report_pdf(audit, record_meta=..., role_id=role_id, template=tpl)` → Response
- [ ] T036 [US2] 修改 `src/matcher/web/templates/individual_view.html` ——「下載我的稽核紀錄」按鈕旁加「下載我的報告 PDF」連結
- [ ] T037 [US2] 補完 `templates/pdf/individual_report.html`：學生資訊段、分配結果段（含三分支文案：第 N 志願 / fallback+有志願 / fallback+無志願）、判定過程簡述
- [ ] T038 [US2] 執行 `uv run pytest tests/integration/test_web_pdf_individual.py tests/integration/test_pdf_no_technical_tokens.py -q` 確認全綠

---

## Phase 5 — User Story 3 (P3)：CLI `matcher report`

**Goal**：CLI 從 audit JSON 產 PDF；exit codes 明確；與 Web 內容欄位一致。

**Independent Test**：CLI `matcher report --audit foo.json --output bar.pdf` 跑成功；指定 --role-id 產 individual 版。

### Tests (TDD — 先紅)

- [ ] T040 [P] [US3] 撰寫 `tests/integration/test_cli_report.py::test_cli_report_admin_pdf_success` —— CliRunner 跑 `matcher report --audit <file> --output <pdf>`，exit 0 + 檔案存在 + 含「%PDF-」magic
- [ ] T041 [P] [US3] 撰寫 `tests/integration/test_cli_report.py::test_cli_report_individual_pdf_success` —— 加 `--role-id S01`，exit 0 + PDF 只含 S01
- [ ] T042 [P] [US3] 撰寫 `tests/integration/test_cli_report.py::test_cli_report_invalid_audit_exits_51` —— audit JSON 缺 assignment，exit 51 + stderr 含「缺欄位」
- [ ] T043 [P] [US3] 撰寫 `tests/integration/test_cli_report.py::test_cli_report_unknown_role_exits_52` —— role_id 不存在，exit 52
- [ ] T044 [P] [US3] 撰寫 `tests/integration/test_cli_report.py::test_cli_report_web_content_parity` —— CLI 產的 PDF 與 Web 產的 PDF 含相同的關鍵字串（record_id、mechanism、role_name 等）；不要求 bytewise 同

### Implementation

- [ ] T045 [US3] 新增 `src/matcher/cli_report.py` 含 typer sub-app + `report` 函式：解 `--audit` JSON → 組 record_meta（推導 record_id 從 audit 或 `--record-id` override）→ 呼叫 `render_match_report_pdf` → 寫檔；捕獲 PdfRenderUnavailable → exit 50；ValueError/KeyError → exit 51；role 不存在 → exit 52
- [ ] T046 [US3] 修改 `src/matcher/cli.py` 新增 1 行 `from matcher.cli_report import app as report_app` + 1 行 `app.add_typer(report_app, name="report")`
- [ ] T047 [US3] 執行 `uv run pytest tests/integration/test_cli_report.py -q` 確認全綠

---

## Phase 6 — Graceful Degrade + Polish

- [ ] T050 [P] 撰寫 `tests/integration/test_web_pdf_graceful_degrade.py::test_web_pdf_503_when_weasyprint_unavailable` —— monkey-patch `matcher.web.pdf._WEASYPRINT_AVAILABLE=False`，GET `/match/{rid}/report.pdf` 回 503 + 含「WeasyPrint」+ 「README」字眼
- [ ] T051 [P] 撰寫 `tests/integration/test_web_pdf_graceful_degrade.py::test_other_endpoints_still_work_without_weasyprint` —— 同 monkey-patch，GET `/match/{rid}` 與 `/match/{rid}/audit` 仍正常（既有功能不受影響）
- [ ] T052 [P] 撰寫 `tests/integration/test_cli_report.py::test_cli_report_exits_50_when_weasyprint_unavailable` —— monkey-patch + CliRunner，exit 50 + stderr 含安裝指引
- [ ] T053 [P] 執行完整測試 `uv run pytest -q` —— 既有 256 + 新增 ≥ 10 全綠（預期 ≥ 270）
- [ ] T054 [P] 依 quickstart.md 8 個步驟在瀏覽器 + CLI 手動驗收一次（含實際開啟 PDF 確認中文 + 搜尋）
- [ ] T055 確認 `git status` 僅含預期變動：
  - 新增：`src/matcher/web/pdf.py`、`src/matcher/cli_report.py`、`src/matcher/web/templates/pdf/*.html`、`src/matcher/web/static/fonts/*.otf` + `OFL.txt`、5 個新測試檔、`specs/010-*/*`
  - 修改：`src/matcher/web/routes/match.py`、`src/matcher/web/templates/{match_result,individual_view}.html`、`src/matcher/cli.py`（1 行加引入）、`pyproject.toml`、`README.md`、`uv.lock`
  - **核心 0 改動**：`src/matcher/{rules,filter,allocator,pipeline,audit,errors,data_import,template_loader,rng,roster}.py` 完全未動

---

## Dependencies

```
Phase 1 (Setup) ─→ Phase 2 (Foundational) ─→ Phase 3 (US1 MVP) ─┬→ Phase 4 (US2)
                                                                └→ Phase 5 (US3)

Phase 3+4+5 → Phase 6 (Polish + Graceful Degrade)
```

- Phase 1 是阻塞——需先有 weasyprint + 字體檔，後續所有測試才能跑（除了 T013 用 monkey-patch 的）
- US2 與 US3 在 US1 後可**並行**（不同檔案）

## Parallel Execution Examples

**Phase 2 測試批次**：T010 T011 T012 T013 [P]（同檔不同函式，pytest collect 並行）。

**Phase 3-5 測試批次**：各 phase 內 5 個測試任務全部 [P]。

**Phase 3 實作分組**：
- 批 A：T025 T028（同檔序列）
- 批 B [P]：T026（HTML 樣板）、T027（PDF 樣板）

**Phase 4 實作分組**：類似 Phase 3。

**Phase 6**：T050 T051 T052 T053 T054 全部 [P]；T055 序列收尾。

## Implementation Strategy

**MVP**：Phase 1 + Phase 2 + Phase 3（US1）——18 個任務、估 6-8 小時（含字體下載與 WeasyPrint 整合學習）。完成後即可端到端 demo「上傳 → 跑 → 下載 admin PDF」。

**v2**：Phase 4（US2）——個別 PDF + 隔離驗證，估 2-3 小時。

**v3**：Phase 5（US3）——CLI 子指令，估 1.5-2 小時（含 cli_report.py 新檔）。

**收斂**：Phase 6——graceful degrade + 完整驗證，估 1-1.5 小時。

**總計**：~32 個任務、新增 ≥ 16 個自動化測試（超過 SC-009 的 ≥ 10 門檻 60%）、估 11-15 小時（最大耗時項：字體選定 + WeasyPrint 系統依賴設定）。

# Phase 1 — Data Model：稽核報告 PDF 匯出

本 feature **無新增持久化 schema、無新增 audit/template 欄位**。新增 1 個純函式介面 + 2 個樣板的 view model。

## 1. PDF render 純函式（D4）

```python
def render_match_report_pdf(
    audit: dict,                  # 完整 audit JSON dict（schema v1.3 兼容；v1.0-v1.2 亦能渲染，缺欄位 graceful）
    *,
    record_meta: dict,            # {"id", "created_at", "input_file"}（從 MatchRecord 或 audit.generated_at 取）
    role_id: str | None = None,   # None → admin；str → individual
    template: Optional[Template] = None,  # humanize 規則用；可選
) -> bytes:
    """產出 A4 PDF bytes；admin 版 (role_id=None) 含完整分配表；individual 版含當事人資料。"""
```

**驗證規則**：
- audit 必須有 `assignment` + `roster_snapshot.roles` 兩段（最小集），否則 `raise ValueError`（CLI 捕獲 → exit 51）
- role_id 非 None 時必須在 `audit.roster_snapshot.roles` 中
- WeasyPrint / 字體載入失敗 → `raise PdfRenderUnavailable`（自定 exception，CLI/Web 各自捕獲）

## 2. AdminPdfViewModel（PDF 樣板 context）

`templates/pdf/match_report.html` 的 jinja2 context：

| 欄位 | 型別 | 來源 |
|---|---|---|
| `record_id` | str | record_meta.id |
| `created_at` | str | record_meta.created_at（顯示為「YYYY-MM-DD HH:MM」） |
| `input_file` | str | record_meta.input_file or 「（無）」 |
| `template_name` | str | audit.template_snapshot.name or 「（無模板）」 |
| `template_id` | str | audit.template_snapshot.id（顯示用） |
| `mechanism` | str | audit.mechanism |
| `mechanism_label` | str | humanize.mechanism_label(mechanism) |
| `seed` | int | audit.seed |
| `processing_order_display` | list[tuple] \| None | M0 → None；M1/M2 → [(role_id, name)] |
| `allocation_rows` | list[dict] | 每筆 {role_id, role_name, target_id, target_name, rank_display} |
| `status` | str | record_meta.status（"success" / "failed"） |
| `error_type` / `error_message` | str \| None | 失敗版用 |
| `font_dir` | str | 字體絕對路徑（給 CSS `@font-face` 用） |

## 3. IndividualPdfViewModel

`templates/pdf/individual_report.html` 的 context：

| 欄位 | 型別 | 來源 |
|---|---|---|
| `record_id`, `created_at` | str | 同 admin |
| `template_name`, `mechanism_label` | str | 同 admin |
| `role_id` | str | 參數 |
| `role_name` | str | audit.roster_snapshot.roles[該 role].attributes.name |
| `role_attrs` | list[tuple[str, str]] | (display_name, value) — 用 template.attributes.roles 取 description |
| `assigned_target_id`, `assigned_target_name` | str \| None | audit.assignment[role_id] + target attrs |
| `preference_rank` | int \| None | audit.allocation_trace 中該 role |
| `preferred_count` | int | roster_snapshot 中該 role.preferences 長度 |
| `mechanism` | str | audit.mechanism（用於三分支文案判斷） |
| `filter_trace_subset` | list[dict] | 沿用 `build_individual_audit_subset` |
| `font_dir` | str | 同 admin |

## 4. PdfRenderUnavailable 例外

```python
# src/matcher/web/pdf.py
class PdfRenderUnavailable(Exception):
    """WeasyPrint 套件或系統依賴不可用。"""
    pass
```

**用法**：
- Web 端點捕獲 → 回 503 + 「PDF 渲染功能不可用；請見 README 安裝 WeasyPrint 系統依賴」
- CLI 捕獲 → print 訊息 + exit code 50

## 5. CLI report 子指令參數（contract）

```bash
matcher report --audit <FILE> [--role-id <ID>] [--record-id <ID>] [--created-at <ISO>] --output <PDF>
```

| 旗標 | 必填 | 說明 |
|---|---|---|
| `--audit` | ✓ | audit JSON 檔路徑 |
| `--output` | ✓ | PDF 輸出檔路徑 |
| `--role-id` | – | 缺省 → admin 版；有值 → individual 版 |
| `--record-id` | – | 缺省 → 從 audit 推導或設「（CLI 產生）」 |
| `--created-at` | – | 缺省 → audit.generated_at 或當下時間 |

**Exit codes**：
- 0：成功
- 50：WeasyPrint / 字體不可用
- 51：audit JSON 解析失敗 / 缺核心欄位
- 52：role_id 不在 roster
- 2：旗標缺失（Typer 預設）

## 6. 不變的契約

- record / audit / template schema：完全不變
- 既有所有 HTTP 端點：不變
- 既有所有 CLI 子指令（run / template / serve）：不變；`cli.py` 僅多 1 行引入新子指令
- 既有 HTML 元素 name/id：不變（只在 match_result.html 與 individual_view.html 新增「下載 PDF」按鈕）

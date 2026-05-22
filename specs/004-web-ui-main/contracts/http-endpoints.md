# HTTP Endpoints Contract

**Branch**: `004-web-ui-main` | **Date**: 2026-05-22

所有錯誤訊息為繁中（FR-019）；所有頁面繁中。

---

## 頁面端點（pages.py）

### `GET /`

首頁；列出三個主要入口連結（新建媒合 / 模板列表 / 過去媒合）。

- **回應**：200 + `index.html` 渲染。

### `GET /templates`

模板列表頁。

- **回應**：200 + `templates_list.html`，含 `TemplateRegistry.list_ids()` 結果。

### `GET /templates/{template_id}`

模板詳情頁。

- **回應**：200 + `template_detail.html`，含完整模板內容（attributes / rules / ui_fields / report_fields / default_targets / preferences_schema）。
- **錯誤**：模板不存在 → 404 + 「找不到模板 `{id}`」訊息。

### `GET /matches`

過去媒合列表（最近 50 筆）。

- **回應**：200 + `records_list.html`，含每筆紀錄的 id、時間、模板名、seed、status。

### `GET /match/new`

新建媒合首頁（向導 step 1）。

- **回應**：200 + `new_match.html`（初始狀態：選擇模板）。

### `GET /match/{record_id}`

媒合結果頁。

- **回應**：
  - status=success：200 + `match_result.html`（分配表 + 摘要 + 下載 audit 連結）
  - status=failed：200 + `match_result.html`（錯誤訊息 + 重試連結）
- **錯誤**：MatchRecord 不存在 → 404。

---

## 動作端點（match.py）

### `POST /match/new/step2`

向導：step 1 → step 2 的 HTMX swap。

- **請求**：`template_id=<str>`（從 step 1 表單）。
- **回應**：200 + `partials/wizard_step2.html`（上傳檔欄位）。

### `POST /match/new/step3`

向導：step 2 → step 3。

- **請求**：`template_id` + 上傳檔。
- **驗證**：檔案大小 ≤ 5 MB；MIME ∈ {text/csv, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet}。
- **回應**：
  - 成功：200 + `partials/wizard_step3.html`（seed 欄位）。
  - 失敗：200 + `partials/error.html`（保留上一步狀態 + 錯誤訊息）。

### `POST /match/run`

執行媒合（向導最後一步）。

- **請求**：`template_id` + 上傳檔（再上傳一次，或從暫存 session 取回——本階段為簡化採前者）+ `seed`。
- **行為**：
  1. 驗證上傳檔（同 step3）
  2. 將檔寫到 `tempfile` → 依 MIME 選 `load_roster_csv` 或 `load_roster_xlsx`
  3. 載入 `template`（含 default_targets）
  4. `run_match(MatcherInput(...))`
  5a. 成功 → 構造 `MatchRecord(status=success, audit=...)` → `MatchStore.save`
  5b. 失敗（任何 `MatcherError`） → `MatchRecord(status=failed, error=...)` → `MatchStore.save`
  6. `tmp.unlink()`
  7. 302 → `/match/{record_id}`
- **回應**：302 重定向。

### `GET /match/{record_id}/audit`

下載 audit JSON。

- **回應**：
  - status=success：200 + `Content-Disposition: attachment; filename="{record_id}.audit.json"` + audit JSON 內容（`ensure_ascii=False, sort_keys=True, indent=2`，與 CLI 路徑等價）。
  - status=failed：404 + 訊息「該媒合執行失敗，無稽核紀錄可下載」。
- **錯誤**：MatchRecord 不存在 → 404。

---

## 靜態端點

### `GET /static/{path}`

由 FastAPI `StaticFiles` mount 於 `src/matcher/web/static/`。

---

## 錯誤處理

| 情境 | HTTP code | 渲染 |
|---|---|---|
| 路由不存在 | 404 | 簡單繁中錯誤頁 |
| 上傳超大 | 400 | `partials/error.html` |
| 上傳 MIME 錯誤 | 400 | `partials/error.html` |
| 模板 / 紀錄不存在 | 404 | 簡單繁中錯誤頁 |
| `MatcherError` 子類（匯入失敗、媒合失敗）| 200（結果頁狀態為 failed） | `match_result.html`（錯誤模式） |
| 未預期 500 | 500 | 簡單繁中錯誤頁 + log 完整 traceback |

---

## 不變式（契約測試會驗證）

- 所有頁面 response body **不含**英文技術術語（SC-009）。
- `GET /match/{id}/audit` 下載的 JSON 與 CLI 同樣輸入跑出的 `audit.json` 在五個核心欄位 100% bytewise 相同（SC-003）。
- `GET /matches` 列表依時間遞減；點任一成功紀錄能還原該次結果頁與 audit（SC-005）。
- 上傳 > 5 MB → 400 + 明確訊息（SC-010）。
- 階段 1+2a+2b CLI 端對端測試 100% 仍通過（SC-008、FR-018）。

# Contract — Auth Routes

## GET /login
- 顯示登入頁（`login.html`），含「用 Google 登入」按鈕導向 `/auth/login`
- 已登入 → 導向 `/`

## GET /auth/login
- 啟動 OAuth：產生 state，導向 Google 授權頁
- Authlib `authorize_redirect`

## GET /auth/callback
- Google 導回；驗 state + 換 token + 驗 id_token
- 成功 → session 寫 `email`（+ 產生 `csrf_token`），導向原請求頁或 `/`
- 失敗 / 使用者取消 → 導回 `/login` 並顯示友善訊息（繁中，無技術碼）

## POST /logout
- 清空 session，導向 `/login`
- 需 CSRF token

## require_login（依賴，非端點）
- 受保護端點注入；未登入 → 302 導向 `/login?next=<原路徑>`
- 提供 `current_user(request) -> email | None`

## 受保護端點清單（需登入 + 視情況 owner 檢查）
| 端點 | 保護 |
|---|---|
| `GET /matches` | 登入；列表過濾 owner |
| `GET /match/{id}` | 登入 + owner |
| `GET /match/{id}/audit`、`/report.pdf` | 登入 + owner |
| `GET /match/{id}/role/{rid}`（舊個別路徑）| 登入 + owner |
| `GET /match/new`、`/match/new/fill` | 登入 |
| `POST /match/run`、`/match/run-from-form`、`/match/preferences` | 登入 + CSRF |
| `GET /templates`、`/templates/{id}` | 登入；過濾可見性 |
| `GET /templates/new`、`/templates/{id}/edit` | 登入（edit 需 owner）|
| `POST /templates/save`、`/templates/validate` | 登入 + CSRF |

## 匿名可達端點（不需登入）
| 端點 | 說明 |
|---|---|
| `GET /login`、`/auth/*` | 登入流程 |
| `GET /r/{token}` | 個別查詢（token 驗章）|
| `GET /r/{token}/audit.json`、`/report.pdf` | 個別下載（同 token 綁定）|
| `GET /static/*` | 靜態資源 |

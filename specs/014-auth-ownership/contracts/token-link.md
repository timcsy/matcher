# Contract — 簽章 Token 個別連結

## 產生（渲染結果頁時）
```
token = URLSafeSerializer(SESSION_SECRET, salt="role-link").dumps([match_id, role_id])
url   = f"/r/{token}"
```
- 結果頁「給每位當事人的個別連結」改用此 url
- 每位角色一條，互不通用

## GET /r/{token}（匿名可達）
- 驗章 `loads(token)`：
  - 失敗（竄改 / 亂猜 / 過期—本版不設過期）→ 404（不洩漏原因）
  - 成功 → `[match_id, role_id]`
- 載入 record（match_id）：
  - 不存在 → 404
  - 該 role_id 不在此 record → 404
- 渲染既有 `individual_view.html`（內容不變，只是入口改 token）

## GET /r/{token}/audit.json、GET /r/{token}/report.pdf
- 同樣驗章 → 對應 (match_id, role_id) → 既有個別下載邏輯

## 安全性質
- **不可偽造**：無 SESSION_SECRET 簽不出有效 token（≥128 bit 安全來自 secret）
- **不可枚舉**：知道 match_id + role_id 也簽不出 token
- **綁死單一角色**：A 的 token payload 是 `[match_id, A]`，看不到 B
- **無狀態**：不需索引檔；驗章即得目標（契合無 DB）

## 與舊路徑關係
- 舊 `/match/{id}/role/{rid}`：改為「登入 + owner」才可看（行政預覽）
- 匿名唯一入口 = `/r/{token}`
- SC-003：已知 match_id 無 token → 無法取得任何角色結果

# Research — 登入與資源歸屬

Spec 三釐清題已解。本檔記錄技術抉擇。

## D1：OAuth 函式庫 → Authlib

**Decision**：用 `authlib` 的 Starlette 整合接 Google OIDC。

**Rationale**：
- OAuth2 授權碼流程含 state（防 CSRF）、nonce、token 交換、id_token JWS 驗章——手刻極易漏掉安全細節
- Authlib 廣泛使用、維護良好、有 Starlette/FastAPI 範例
- 純 Python，無系統依賴，不破壞 K8s 簡單部署

**Alternatives**：
- ❌ httpx 手刻：安全風險高，省的依賴不值得
- ❌ fastapi-users / 完整 auth 框架：過重，且預設要 DB，違反「無 DB」

## D2：Session → 簽章 cookie（Starlette SessionMiddleware）

**Decision**：用 Starlette `SessionMiddleware`（itsdangerous 簽章 cookie）存 `{"email": ...}`。

**Rationale**：
- 無伺服器端 session 儲存 → 無 DB、無 Redis，契合檔案系統 ethos
- 簽章保證 cookie 不可竄改；內容只放 email（非敏感）
- cookie 設 `https_only=True`（Secure）、HttpOnly（middleware 預設）、`same_site="lax"`

**Alternatives**：
- ❌ 伺服器端 session（DB/Redis）：引入儲存依賴
- ❌ 自簽 JWT：itsdangerous 已夠，JWT 過度

## D3：個別連結 token → itsdangerous 簽章（無狀態）

**Decision**：token = `URLSafeSerializer(SECRET, salt="role-link").dumps([match_id, role_id])`；連結 `/r/{token}`。開啟時驗章→取出 (match_id, role_id)→渲染該角色個別頁。

**Rationale**：
- **無狀態**：不需 token→資源的索引檔，不需掃描；驗章即解出目標。完美契合無 DB
- 無法偽造（沒有 SECRET 簽不出有效 token）→ 滿足「≥128 bit 安全」（來自 server secret）
- 無法枚舉：role_id 仍在 payload 內但「知道 role_id」不等於「能簽出 token」
- 一條 token 只對應一個 (match_id, role_id)：用 A 的 token 看不到 B（payload 綁死 A）

**注意**：payload 是「簽章非加密」，base64 解可看到 match_id/role_id 明文——這無妨，安全性來自簽章不可偽造，不靠保密 payload。

**Alternatives**：
- ❌ 隨機 token + 索引檔：要維護 token→資源對應檔，並發與清理麻煩
- ❌ 把 token 存進 record 再掃描比對：每次開連結要掃所有 record，慢且醜

## D4：舊式個別路徑 `/match/{id}/role/{role_id}` 處理

**Decision**：保留路徑但**改為需登入且為該配對擁有者**才可看（行政預覽用）；匿名者一律走 `/r/{token}`。

**Rationale**：
- 行政自己想預覽個別頁時，已登入、是 owner，可直接走舊路徑，方便
- 匿名枚舉被擋（未登入 → 導向登入，看不到）
- `/r/{token}` 是唯一的「匿名可達」入口，且綁死單一角色

## D5：CSRF → 綁 session 的 token（雙重提交，無新依賴）

**Decision**：在 session 放一個 `csrf_token`（首次產生），所有 POST 表單渲染成 hidden field；POST 處理前比對 form 的 token == session 的 token，不符回 403。

**Rationale**：
- SameSite=Lax 已擋掉大部分跨站 POST，CSRF token 是縱深防禦
- 綁 session 的 token 實作簡單、無新依賴
- 既有表單（/match/run、run-from-form、/match/preferences、/templates/save 等）逐一加 hidden field

**Alternatives**：
- ❌ starlette-csrf / fastapi-csrf-protect：多一個依賴，自己做夠簡單

## D6：擁有者欄位持久化

**Decision**：
- MatchRecord：JSON 加 `owner`（email）；角色 token 不存（D3 無狀態，按需簽出），個別連結渲染時即時簽
- 自訂範本：版本 YAML 加 `owner` 與 `visibility`（`private`/`public`），預設 `private`

**Rationale**：沿用既有檔案，加欄位最小侵入。`MatchStore.list` 加 `owner` 參數過濾。範本 registry 載入時讀 owner/visibility，列表依「owner == me 或 visibility==public 或 內建」過濾。

**相容**：FR-017 已決定升級清空 `data/`，故無舊資料相容負擔。

## D7：rate-limit（開放註冊的代價）

**Decision**：對 `/auth/*` 與 `/match/run*` 加簡易記憶體 rate-limit（每 IP 每分鐘 N 次）。MVP 用輕量自製中介或 slowapi（評估）；若引入額外依賴則記入 Complexity Tracking。

**Rationale**：開放任何 Google 帳號 + 公開網路 → 需基本濫用防護。記憶體計數對單機足夠；多副本部署再議（屬階段 5 部署範疇）。

**Note**：標為 SHOULD（FR-016），非 P1 阻斷項；可放 Polish。

## D8：環境變數

| 變數 | 用途 |
|---|---|
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | OAuth client（維運者於 Google Cloud 建） |
| `OAUTH_REDIRECT_URI` | callback URL（依部署網域） |
| `SESSION_SECRET` | 簽章 session cookie 與 token 的金鑰 |

皆由環境變數注入，不寫死、不入 repo。本機開發可給預設（僅非 production）。

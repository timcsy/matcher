# Quickstart — 驗證 feature 014

## 環境變數（本機開發）

```bash
export GOOGLE_CLIENT_ID=...        # Google Cloud OAuth client
export GOOGLE_CLIENT_SECRET=...
export OAUTH_REDIRECT_URI=http://localhost:8765/auth/callback
export SESSION_SECRET=dev-only-secret-change-in-prod
```

## SC-001 管理頁需登入、個別連結免登入

```bash
# 未登入訪問管理頁 → 302 /login
curl -s -o /dev/null -w "%{http_code} %{redirect_url}\n" http://127.0.0.1:8765/matches
# 個別 token 連結未登入可開（200）
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8765/r/<valid-token>
```

## SC-002 跨使用者隔離（測試層）

`tests/integration/test_web_auth_ownership.py`：
- A 登入建配對 → B 登入 `/matches` 看不到 → B 開 A 的 `/match/{id}` 得 403

## SC-003 token 不可枚舉

- 已知 match_id，組 `/match/{id}/role/T01`（舊路徑）未登入 → 302/403
- 亂猜 `/r/randomstring` → 404
- 合法 token 換 role_id 重簽不出 → 無效

## SC-004 範本私有/公開

- A 建私有範本 → B 看不到
- A 設公開 → B 看得到、可複製、不可編輯

## SC-005 / SC-006 測試與核心 0 改動

```bash
uv run pytest -q
git diff main --name-only -- 'src/matcher/*.py' ':!src/matcher/web' ':!src/matcher/templates'
# 預期：空（核心未動）
```

## SC-007 公開網路加固

- 所有 POST 表單含 CSRF hidden field；缺 token 的 POST → 403
- session cookie 具 Secure（https_only）、HttpOnly、SameSite=Lax

## E2E（手動，需設好 OAuth）

1. 開 `/` → 未登入導向 `/login`
2. 用 Google 登入 → 回到首頁、頁首顯示 email + 登出
3. 建一次配對 → 結果頁個別連結為 `/r/{token}`
4. 開無痕視窗（未登入）貼上 `/r/{token}` → 看得到該角色結果
5. 無痕視窗試 `/matches` → 導向登入
6. 用另一個 Google 帳號登入 → 看不到第一個帳號的紀錄

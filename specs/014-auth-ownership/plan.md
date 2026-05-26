# Implementation Plan: 登入與資源歸屬

**Branch**: `014-auth-ownership` | **Date**: 2026-05-26 | **Spec**: [spec.md](./spec.md)

## Summary

公開網路部署前的隱私補強。技術手段：

1. **Google OAuth 登入**：用 Authlib 接 Google OIDC；登入成功把 email 寫進**簽章 cookie session**（Starlette SessionMiddleware，無伺服器端 session 儲存、無 DB）。
2. **資源綁擁有者**：MatchRecord JSON 與自訂範本 YAML 各加 `owner` 欄位（範本另加 `visibility`）。列表與存取以「`owner == 當前 email`」過濾／守門。
3. **個別連結改簽章 token**：用 `itsdangerous.URLSafeSerializer` 把 `(match_id, role_id)` 簽章成 token，連結為 `/r/{token}`。驗章才能看，無法偽造、無法枚舉；**無狀態、不需索引檔**。家長免登入即可開。
4. **公開網路加固**：CSRF token（綁 session 的雙重提交）、cookie 設 Secure/HttpOnly/SameSite、OAuth 與執行配對端點基本 rate-limit。
5. **核心 0 改動**：所有變更局限於 `src/matcher/web/` + 設定；CLI 與 `src/matcher/*` 核心不動。

## Technical Context

**Language/Version**：Python 3.11+（沿用）
**Primary Dependencies**：沿用 + **新增 `authlib>=1.3`（Google OAuth/OIDC，業界標準、避免手刻不安全的 OAuth）、`itsdangerous>=2.1`（簽章 session cookie 與 token 簽章；Starlette SessionMiddleware 本就需要）**
**Storage**：沿用檔案系統——`data/matches/*.json`、`data/templates/<id>/v<N>.yaml` 加欄位；**無 DB、無伺服器端 session 儲存**
**Testing**：pytest（沿用）；OAuth 以 monkeypatch 模擬 callback（不打真 Google）；TestClient 帶 session cookie
**Target Platform**：公開網路；前置反向代理終結 HTTPS
**Project Type**：Web + CLI 混合（沿用）
**Performance Goals**：沿用；auth 中介層每請求 O(1) 驗 cookie
**Constraints**：
- 核心 `src/matcher/*`（非 web）0 改動（FR-014 / SC-006）
- 不引入 DB（FR-015）
- token 亂度 ≥128 bit（用 server secret 簽章達成）
- 個別 token 連結免登入（家長路徑），但其餘管理頁強制登入
**Scale/Scope**：動 `src/matcher/web/` 內約 6–8 檔 + pyproject 加 2 依賴；新增 auth 模組、CSRF 工具、token 工具

## Constitution Check

| 原則 | 評估 | 備註 |
|---|---|---|
| I. TDD | ✅ | 每端點先寫測試：未登入導向、跨使用者 403、token 連結匿名可開、枚舉被擋、CSRF 缺失被拒 |
| II. 規格優先 | ✅ | spec.md 已通過 checklist；3 釐清題已解 |
| III. 繁體中文 | ✅ | 文件繁中；登入/錯誤頁面向使用者繁中 |
| IV. 簡潔（YAGNI）| ⚠️→✅ | 新增 2 依賴需理由（見下）；功能採最簡（開放註冊、純個人私有、範本兩段）——已剔除共享/結果分享/email ACL |
| V. 可觀測性 | ✅ | 登入失敗、403、CSRF 失敗皆結構化回應；token 驗章失敗明確 |

**新依賴理由（額外約束要求）**：
- `authlib`：OAuth2/OIDC 流程（state、nonce、token 交換、id_token 驗章）手刻極易出安全漏洞；Authlib 是 Python 生態廣泛使用、經審視的實作。替代方案「用 httpx 手刻」被否決——安全風險不值得省這個依賴。
- `itsdangerous`：簽章 cookie session 與 token 簽章；純 Python、極輕量；Starlette SessionMiddleware 本就依賴它。替代方案「自寫 HMAC 簽章」被否決——itsdangerous 已是該問題的標準解。

**結論**：gate 通過。新依賴於 Complexity Tracking 記錄。

## Project Structure

### Documentation

```text
specs/014-auth-ownership/
├── plan.md              # 本檔
├── spec.md              # 已有
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   ├── auth-routes.md         # 登入/登出/callback 端點契約
│   ├── ownership-rules.md     # 擁有者過濾 / 403 規則
│   └── token-link.md          # 簽章 token 連結契約
└── tasks.md             # /speckit.tasks 產出
```

### Source Code

```text
src/matcher/web/
├── auth.py                  # ★ 新增：OAuth client 設定、login/logout/callback、require_login 依賴、current_user
├── security.py              # ★ 新增：CSRF token 產生/驗證、token 連結簽章/驗章（itsdangerous）
├── app.py                   # ← 加 SessionMiddleware、註冊 auth router、CSRF、cookie 設定
├── store.py                 # ← MatchRecord 加 owner + role tokens；list 支援 owner 過濾
├── routes/
│   ├── auth.py              # ★ 新增：/login /logout /auth/callback
│   ├── match.py             # ← 管理端點加 require_login + owner 檢查；新增 /r/{token} 匿名路由；個別連結改 token
│   ├── records.py           # ← /matches 只列 owner 自己的
│   └── pages.py             # ← 範本 owner + visibility；列表過濾；建/編檢查 owner
└── templates/
    ├── base.html            # ← 頁首顯示登入者 / 登出鈕
    ├── login.html           # ★ 新增：登入頁
    ├── match_result.html    # ← 個別連結改 /r/{token}
    └── （各 POST 表單加 CSRF hidden field）

src/matcher/web/template_store（或 pages 內）  # ← 範本 owner/visibility 持久化（YAML 欄位或 sidecar meta）

pyproject.toml               # ← 加 authlib、itsdangerous
```

**Structure Decision**：沿用 Web + CLI 結構。auth 為新的周邊整合層，集中在 `src/matcher/web/{auth,security}.py` + routes 守門；核心與 CLI 完全不碰（教訓 7）。

## Complexity Tracking

| 違規 / 新增 | 為何需要 | 否決的較簡方案 |
|---|---|---|
| 新增 `authlib` 依賴 | OAuth2/OIDC 安全流程不可手刻 | 「httpx 手刻 OAuth」——安全風險過高 |
| 新增 `itsdangerous` 依賴 | 簽章 session + token；Starlette 本就需要 | 「自寫 HMAC」——重造輪子、易錯 |

兩者皆純 Python、無系統依賴，不影響「K8s 簡單部署」。

# Data Model — 登入與資源歸屬

## 變更概覽

| 實體 | 變更 |
|---|---|
| Session（新）| 簽章 cookie，內容 `{email, csrf_token}` |
| MatchRecord | 新增 `owner`（email 字串） |
| 自訂範本（版本 YAML）| 新增 `owner`（email）、`visibility`（`private`/`public`，預設 private）|
| 個別連結 token（新，無狀態）| `URLSafeSerializer` 簽章 `[match_id, role_id]` |

無 DB。無新增持久化檔案類型（皆既有 JSON/YAML 加欄位）。

## Session

```jsonc
// 簽章 cookie（itsdangerous），非伺服器端儲存
{
  "email": "admin@example.com",   // Google 登入後的 email
  "csrf_token": "<隨機字串>"        // 首次登入/造訪時產生
}
```
- 未登入：無此 cookie 或無 email
- 登出：清空 session

## MatchRecord（變更後）

```jsonc
{
  "schema_version": "match-record/1.0",   // 紀錄檔 schema（與 audit schema 不同，維持不變或視需要）
  "id": "2026-...-xxxx",
  "owner": "admin@example.com",            // ★ 新增
  "created_at": "...",
  "template_id": "...",
  "seed": 123456,
  "input_file": "...",
  "mechanism": "M0",
  "status": "success",
  "audit": { ... },                        // audit schema v1.4，不變
  "error": null
}
```
- 角色 token **不存檔**（D3 無狀態，渲染時即時簽章產生）

## 自訂範本版本檔（變更後）

```yaml
# data/templates/<id>/v<N>.yaml
schema_version: "1.0"
id: my-template
owner: "admin@example.com"     # ★ 新增
visibility: private            # ★ 新增：private | public（預設 private）
name: ...
# ... 其餘不變
```
- 內建範本（teacher-class、study-group）：無 owner，視為「對所有登入者可見、可複製」

## 個別連結 token（無狀態簽章）

```
token = URLSafeSerializer(SESSION_SECRET, salt="role-link").dumps([match_id, role_id])
連結  = /r/{token}
```
- 驗章：`loads(token)` 成功 → `[match_id, role_id]`；失敗（竄改/亂猜）→ 404/403
- 一 token 綁死一個 (match_id, role_id)

## 可見性 / 存取規則

| 資源 | 誰能看（管理視角）| 誰能看（匿名）|
|---|---|---|
| 配對紀錄完整頁 `/match/{id}` | 僅 owner（登入）| 不可 |
| 個別頁 `/r/{token}` | — | 任何持有效 token 者 |
| 個別頁舊路徑 `/match/{id}/role/{rid}` | 僅 owner（登入）| 不可 |
| 自訂範本（private）| 僅 owner | 不可 |
| 自訂範本（public）| 所有登入者（可複製不可編輯）| 不可 |
| 內建範本 | 所有登入者 | 不可 |
| `/matches` 列表 | 只列 owner 自己的 | 導向登入 |
| 範本列表 | owner 自己的 + public + 內建 | 導向登入 |

## State Transitions

- 範本 visibility：`private ⇄ public`（僅 owner 可切換）
- Session：未登入 → 登入（OAuth callback）→ 登出（清 session）

## 升級處理

FR-017：升級時清空 `data/matches/`、`data/templates/`，無舊資料遷移。

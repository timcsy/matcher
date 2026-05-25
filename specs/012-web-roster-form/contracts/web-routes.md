# Web Routes Contract — feature 012

修改 1 個既有端點 + 新增 2 個端點。

## GET /match/new（修改）

**變更**：HTML 加 Alpine `x-data="{mode: 'upload'}"`，模式三選一 radio 切換顯示。

**回應**：HTML 200。預設 mode='upload' 行為與既有相同（不破壞）。

## GET /match/new/fill（新增）

**變更**：填寫頁。

**Query**：
| 欄位 | 必填 |
|---|---|
| `template_id` | ✓ |

**回應**：
- template_id 缺 / 不存在 → 400/404
- 成功 → HTML 200 render `roster_form_fill.html`，context 含 `template`、`role_attrs`、`target_attrs`、`requires_targets`、`has_prefs_schema`、`mechanisms`

## POST /match/run-from-form（新增）

**變更**：接收 UI 填寫表單；轉成 CSV bytes → 走既有 pipeline。

**請求**（multipart/form 或 form-urlencoded）：見 data-model §1 表格。

**回應**：

| 情境 | Status | 內容 |
|---|---|---|
| 範本不存在 | 404 | error_page.html |
| 機制非法 / seed 非整數 | 400 | error_page.html |
| 角色行全部空白（沒填） | 400 | error_page.html「請至少填一位角色」|
| mechanism=M0 | 303 | Location: `/match/{rid}`（同 /match/run） |
| mechanism in (M1,M2) + template.preferences_schema | 200 | render `preferences_form.html`（feature 009 既有頁），含 hidden inputs（同 4d 機制） |
| mechanism in (M1,M2) + 範本無 schema | 303 | failed record (MechanismRequiresPreferences) → Location: `/match/{rid}` |

## /match/preferences（既有，不動）

feature 009 的 POST `/match/preferences` 直接接收本 feature 透過 hidden inputs 跳轉來的請求（與既有 「上傳 CSV + M1/M2」路徑等價）。沒有新增分支。

## 不變的契約

- 既有 `/match/new` GET 預設行為（mode='upload'）：完全相同
- `/match/run`（既有 CSV 上傳）：不動
- `/match/preferences`（feature 009）：不動
- 既有所有 record / audit endpoint：不動
- record / audit schema：不變

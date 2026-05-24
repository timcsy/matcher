# Web Routes Contract — feature 009

本 feature 修改既有 `/match/run` + 新增 `/match/preferences` 端點。

## POST /match/run（行為擴充）

**變更**：在解析 roster 之後、執行 pipeline 之前，新增「跳填志願頁」判斷分支。

**請求**：沿用 008（multipart/form-data：template_id、seed、roster、mechanism）。

**回應分支**：

| 條件 | Status | 內容 |
|---|---|---|
| 模板無 `preferences_schema` | 同 008 | 沿用既有路徑 |
| 任一 role.preferences 非空 | 同 008 | 沿用既有路徑（CSV preferences 欄已填） |
| `mechanism == "M0"` | 同 008 | 沿用既有路徑 |
| 模板有 schema + 全空 + M1/M2 + **有** `default_targets` | 200 | render `preferences_form.html`（正常填志願頁） |
| 模板有 schema + 全空 + M1/M2 + **無** `default_targets` | 200 | render `preferences_form.html`（顯示 FR-009 錯誤段 + 「回到上一步」） |

## POST /match/preferences（新增）

**變更**：新增端點。

**請求**（application/x-www-form-urlencoded）：

| 欄位 | 型別 | 必填 | 規則 |
|---|---|---|---|
| `template_id` | str | ✓ | hidden input；重新查 TemplateRegistry 驗證 |
| `mechanism` | str | ✓ | hidden input；規範化大寫；∈ {M1, M2} |
| `seed` | int | ✓ | hidden input |
| `roster_bytes_b64` | str | ✓ | hidden input；base64 字串；解碼後跑 data_import |
| `roster_filename` | str | ✓ | hidden input；含副檔名以判斷 csv/xlsx |
| `pref_<role_id>_<rank>` | str | – | 動態欄位；空字串視為「未選」；非空值須在 default_targets id 集合中 |
| `_action` | str | ✓ | `"submit"` 或 `"skip"` |

**回應**：

| 情境 | Status | 內容 |
|---|---|---|
| `_action == "skip"` | 303 | Location: `/match/{rid}`；record.status="failed"，error=MechanismRequiresPreferences |
| `_action == "submit"` + 驗證失敗（同列重複 / 非白名單 id） | 200 | 回填志願頁 + `form_errors` |
| `_action == "submit"` + 全空 prefs | 200 | 回填志願頁 + 「請至少為一位角色填 1 個志願」錯誤 |
| `_action == "submit"` + 驗證通過 + pipeline 成功 | 303 | Location: `/match/{rid}` |
| `_action == "submit"` + pipeline 拒絕（如 PreferencesNotSupported——不應發生但保險） | 303 | Location: `/match/{rid}`（顯示失敗結果頁） |
| hidden inputs 缺失 / template_id 失效 / base64 解碼失敗 | 400 | error_page.html「填志願表單資料異常，請回到上一步重新上傳」 |

## GET /match/new（小幅微調）

**變更**：無變更（既有 008 表單即足夠；填志願步驟在 POST 後才出現）。

## 不變的契約

- `/match/{rid}`、`/match/{rid}/audit`、`/match/{rid}/role/{role_id}`：完全不變
- record JSON schema `match-record/1.0`：不升版
- audit JSON schema `1.3`：不升版、不新欄位
- 既有 HTML 元素的 name / id：不改名

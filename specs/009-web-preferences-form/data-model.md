# Phase 1 — Data Model：Web UI 動態填志願表單

本 feature **無新增持久化 schema、無新增 audit/template 欄位**。所有資料皆暫存於 HTML form hidden inputs（單次 request 生命週期內），執行時組裝為既有 `Role.preferences`。

## 1. PreferencesFormViewModel（新增）

`GET-via-POST /match/run`（觸發跳頁時）與 `POST /match/preferences`（驗證失敗回填頁時）注入 `preferences_form.html` 的 context：

| 欄位 | 型別 | 來源 | 說明 |
|---|---|---|---|
| `template_id` | str | 第一次 POST 表單 | 嵌入 hidden input |
| `template_name` | str | template_loader 查詢 | 顯示用 |
| `mechanism` | str | 第一次 POST 表單 | 嵌入 hidden input + 顯示用「M1 RSD / M2 Boston」 |
| `seed` | int | 第一次 POST 表單 | 嵌入 hidden input |
| `roster_bytes_b64` | str | base64(原始 upload bytes) | 嵌入 hidden input |
| `roster_filename` | str | upload.filename | 嵌入 hidden input + 顯示「已上傳：roster.csv」 |
| `roles_for_form` | list[dict] | data_import 解析後的 roster.roles | 每筆含 `{id, display_name}` |
| `targets_for_options` | list[dict] | template.default_targets（或 None） | 每筆含 `{id, display_name, capacity, summary}` 供下拉與候選對象段 |
| `max_choices` | int | template.preferences_schema.max_choices | 控制每列下拉數 |
| `form_errors` | list[str] | （驗證失敗時）錯誤訊息 | 紅字顯示 |
| `previous_form_values` | dict[str, str] | （驗證失敗時）使用者已填的志願 | 重新預填 select selected |

**渲染規則**：
- 若 `targets_for_options` 為 None（模板無 default_targets）→ 樣板顯示 FR-009 錯誤訊息 + 「回到上一步」按鈕
- 「候選對象段」迴圈 `targets_for_options` 顯示 `{display_name}（容量 {capacity} 人）`
- 每列 `roles_for_form` × `max_choices` 個 `<select name="pref_{role_id}_{rank}">` 含 (id="", label="（未選）") + 各 target 選項

## 2. PreferencesFormSubmitInput（新增）

`POST /match/preferences` 接受的表單：

| 欄位 | 型別 | 必填 | 規則 |
|---|---|---|---|
| `template_id` | str | ✓ | hidden input；後端必須重新查 TemplateRegistry 驗證仍存在 |
| `mechanism` | str | ✓ | hidden input；規範化大寫；∈ {M1, M2}（M0 不會走此路徑） |
| `seed` | int | ✓ | hidden input |
| `roster_bytes_b64` | str | ✓ | hidden input；base64 字串 |
| `roster_filename` | str | ✓ | hidden input；含副檔名用以判斷 csv/xlsx |
| `pref_<role_id>_<rank>` | str | – | 動態欄位；空字串視為「未選」；非空值須在 targets_for_options 中 |
| `_action` | str | ✓ | `"submit"` 或 `"skip"`；後者觸發 escape hatch |

**驗證流程**（伺服器端 POST 內，順序）：
1. 解 base64 → 暫存 tmp file → 重跑 data_import（含同樣 mechanism 偵測；任何失敗 → 沿用既有 error_page.html）
2. 重查 template（若 template_id 失效 → TemplateNotFound）
3. 依 `_action` 分支：
   - `skip`：保持 roster.roles 的 preferences 為空 → 跑 pipeline（必然失敗於 M1/M2 + `MechanismRequiresPreferences`）
   - `submit`：迴圈 roster.roles，為每個 role 蒐集 `pref_<role_id>_1..max_choices` 的值（過濾空字串）；驗證：
     - (a) 同列無重複（用 set 比 len）
     - (b) 該值在 `default_targets` id 集合中
     - (c) 全 roles 蒐集後，至少 1 個 role 有 ≥ 1 個 pref（否則回填志願頁，提示等同 skip 路徑）
   - 通過後用 `dataclasses.replace(role, preferences=tuple(...))` 重組 roles → 重組 roster → 跑 pipeline
4. 寫 record、重導到 `/match/{rid}`

## 3. RouteDispatchDecision（既有 `/match/run` 新增的判斷邏輯）

| 條件組合 | 結果 |
|---|---|
| 任一 roles.preferences 非空 | 不跳填志願頁、直接執行（008 既有路徑） |
| mechanism == "M0" | 不跳填志願頁、直接執行 |
| 模板無 preferences_schema | 不跳填志願頁、直接執行（既有 PreferencesNotSupported 拒絕邏輯沿用） |
| 模板無 default_targets（但有 schema）+ 上述三條件以外 | 跳填志願頁但顯示 FR-009 錯誤訊息 |
| 三條件皆符合（schema + 全空 + M1/M2）+ 有 default_targets | **跳填志願頁正常 render** |

## 4. 不變的契約

- record JSON schema `match-record/1.0`：**不**升版
- audit JSON schema `1.3`：**不**升版、**不**新欄位
- `Template`、`Role`、`Target` dataclass：**不**新欄位
- 既有所有端點的回應結構：**不**變
- 既有 HTML 元素的 name / id：**不**改名

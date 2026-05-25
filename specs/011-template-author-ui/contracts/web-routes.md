# Web Routes Contract — feature 011

5 個新端點 + 3 個既有端點微調。

## GET /templates/new

新增。Render `template_authoring.html`。

**Query params**：

| 欄位 | 用途 |
|---|---|
| `fork=<builtin-id>` | 「Fork 內建模板」入口——預填內建模板內容 + 預設 id `<原id>-fork` |
| `mode=advanced` | 預設顯示「進階模式」頁籤（缺省為簡單） |

**回應**：HTML 200。

## GET /templates/{id}/edit

新增。Render `template_edit.html`，預載最新版本內容。

**回應**：
- 自訂模板 → 200，預載 v_max 內容
- 內建模板 → 403 + 「內建模板不可編輯；請使用 Fork」
- id 不存在 → 404

## POST /templates/validate

新增。驗證單一表單 / YAML 是否合法。**不寫入**。

**請求**（multipart/form 或 application/json）：

| 欄位 | 必填 | 說明 |
|---|---|---|
| `mode` | ✓ | `"simple"` 或 `"advanced"` |
| `template_id` | ✓ | kebab-case |
| `raw_yaml` (advanced) | ✓ (advanced) | YAML 字串 |
| `<simple-mode 各欄位>` | – | 見 data-model.md §3 |

**回應**：JSON 200。

```json
{
  "ok": true,
  "summary": {
    "id": "club-signup",
    "name": "社團報名",
    "attribute_count": {"roles": 3, "targets": 3},
    "rule_count": 2,
    "has_preferences_schema": false,
    "default_target_count": 3
  }
}
```

或失敗：

```json
{
  "ok": false,
  "errors": ["規則 R001 的 ge 算子 value 必須為整數", "..."]
}
```

## POST /templates/save

新增。驗證 + 寫入新版本。

**請求**：同 `/templates/validate` + 隱含「儲存」意圖。

**回應**：
- 200 + JSON `{"ok": true, "id": "...", "version": N, "redirect_to": "/templates/<id>"}`
- 400 + JSON `{"ok": false, "errors": [...]}`（驗證失敗）
- 409 + JSON `{"ok": false, "errors": ["模板 id 已存在於內建模板，不可覆蓋；請改名或選擇 Fork"]}`（id 衝突內建）

## GET /templates/{id}/versions/{version}

新增。回單一版本的 YAML 內容（純文字）。

**回應**：
- 自訂模板 + 版本存在 → 200 + `text/yaml`
- 自訂模板 + 版本不存在 → 404
- 內建模板 → 404（內建無版本概念）

## GET /templates/{id}（修改）

新增 context 欄位 + 樣板分支：

- `is_builtin: bool`
- `versions: list[(int, str)]` 版本號 + mtime
- `current_version: int | None`

樣板：
- 自訂模板：顯示「編輯」按鈕 + 版本歷史段
- 內建模板：顯示「Fork 為自訂模板」按鈕；無版本歷史

## GET /templates（修改）

模板列表頁：

- 「想做新場景的模板」callout 改為 prominent 「+ 新增模板」按鈕（指向 `/templates/new`）
- 列表卡片區分「內建」與「自訂」（可用 badge 標記）

## GET /match/{rid}（修改）

結果頁底部新增「以此模板版本再執行」按鈕：

```html
<a href="/match/new?template_snapshot={{ rid }}" class="btn btn-secondary">以此模板版本再執行</a>
```

## GET /match/new（修改）

支援新 query param：

| Query | 行為 |
|---|---|
| `?template_snapshot=<rid>` | 讀 record → 從 audit.template_snapshot 還原為臨時 Template → 渲染表單時下拉「預選」此臨時模板（label 含「（以歷史 audit 還原）」），不持久化 |
| `?template_id=<id>` | 既有：預選此 id |
| 兩者同時 | template_snapshot 優先 |

## 不變的契約

- 既有 record / audit / template schema：完全不變
- 既有 `/match/run`, `/match/{rid}/audit`, `/match/{rid}/role/{rid}/audit.json` 等：不變
- 既有所有 CLI 子指令：不變

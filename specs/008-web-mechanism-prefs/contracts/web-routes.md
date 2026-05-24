# Web Routes Contract — feature 008

本 feature 修改既有 routes（不新增端點）；以下記錄變更後的 HTTP 契約。

## GET /match/new

**變更**：模板 context 新增 `mechanisms` 與 `default_mechanism`。

**回應**：HTML 200。表單新增：

```html
<label for="mechanism">分配機制</label>
<select id="mechanism" name="mechanism">
  <option value="M0" selected>M0 純抽籤</option>
  <option value="M1">M1 RSD（隨機輪流挑）</option>
  <option value="M2">M2 Boston（層級填滿）</option>
</select>
<small>無志願選 M0；有志願選 M1（隨機輪流挑）或 M2（先填高志願）</small>
```

## POST /match/run

**變更**：接受新欄位 `mechanism: str = Form("M0")`。

**請求**（multipart/form-data）：

| 欄位 | 型別 | 必填 | 預設 | 規則 |
|---|---|---|---|---|
| `template_name` | str | ✓ | — | 既有 |
| `roster_file` | file | ✓ | — | 既有 |
| `seed` | int | – | None | 既有 |
| `mechanism` | str | – | "M0" | `.strip().upper()` 後須 ∈ {M0, M1, M2} |

**回應**：

| 情境 | Status | 內容 |
|---|---|---|
| 機制非法 | 400 | error_page.html「不支援的機制：X（請選 M0、M1、M2）」 |
| M1/M2 + 全空 prefs | 200 | match_result.html 失敗模式，顯示「{M1\|M2} 需要至少一位角色提供志願」與「改用 mechanism=M0」建議；audit 仍寫入 record |
| M0 + 任一非空 prefs | 200 | match_result.html 失敗模式，顯示既有 PreferencesNotSupported 訊息 |
| 成功 | 303 | Location: `/match/{rid}` |

## GET /match/{rid}（結果頁）

**變更**：模板 context 新增 `mechanism`、`mechanism_label`、`processing_order_display`、`allocation_rows[i].preference_rank_display`。

**回應**：HTML 200，新增區塊：

1. **機制名稱段**（標題下方）：`<h2>分配階段（{{ mechanism_label }}）</h2>`
2. **處理順序段**（M1/M2 時顯示）：`<p>處理順序：S03（王小明） → S01（…） → …</p>`
3. **分配表新增欄**（M1/M2 時顯示）：「志願排名」欄，每行為「第 N 志願」或「抽籤」

M0 路徑：(2) 與 (3) 隱藏。

## GET /match/{rid}/role/{role_id}（個別查詢頁）

**變更**：模板 context 新增 `mechanism`、`preference_rank`、`preferred_count`。

**回應**：HTML 200，M1/M2 路徑下新增段：

| 條件 | 顯示文案 |
|---|---|
| `preference_rank` 非 null | 「您被分到第 N 志願：{對象顯示名}」 |
| `preference_rank` 為 null + `preferred_count > 0` | 「您原本的志願已被分配給其他人，由公平抽籤分到 {對象顯示名}。」 |
| `preference_rank` 為 null + `preferred_count == 0` | 「您未在志願清單中，由公平抽籤分到 {對象顯示名}。」 |
| `mechanism == "M0"` 或未分配 | （整段不渲染） |

## 不變的契約

- record JSON schema `match-record/1.0`：**不**升版
- audit JSON schema `1.3`：**不**升版、**不**新欄位
- 既有所有端點的非新增欄位：**不**改型別、**不**改預設
- 既有 HTML 元素的 name / id：**不**改名（向後相容自動化測試）

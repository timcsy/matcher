# UI Pages Contract

**Branch**: `004-web-ui-main` | **Date**: 2026-05-22

定義各頁面的版面、內容、與互動。所有可閱讀文字繁中。

---

## 共用：base.html

頁面骨架：

```text
<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <title>{% block title %}matcher{% endblock %} — matcher</title>
  <link rel="stylesheet" href="/static/style.css">
  <script src="https://unpkg.com/htmx.org@1.9.10"></script>
</head>
<body>
  <header>
    <h1><a href="/">matcher</a></h1>
    <nav>
      <a href="/templates">模板</a>
      <a href="/match/new">新建媒合</a>
      <a href="/matches">過去媒合</a>
    </nav>
  </header>
  <main>{% block content %}{% endblock %}</main>
  <footer>matcher（核心媒合引擎）— Apache 2.0</footer>
</body>
</html>
```

---

## 首頁 `/`（index.html）

- 標題：「matcher：以可解釋規則與公平程序媒合對象」
- 三個大區塊（卡片式）：
  - **新建媒合**：「選模板、上傳名單、執行」CTA 連到 `/match/new`
  - **模板列表**：「瀏覽內建情境」連到 `/templates`
  - **過去媒合**：「重新查看 / 下載稽核」連到 `/matches`
- 底部提示：「執行前請瀏覽『模板』了解判斷規則」

---

## 模板列表 `/templates`（templates_list.html）

- 卡片式列出每個內建模板：
  ```
  [teacher-class] 教師-班級配對
  依專業與班級需要科目配對任課教師
  [瀏覽] [立即使用]
  ```
- 「立即使用」連到 `/match/new?template_id=<id>`

---

## 模板詳情 `/templates/{id}`（template_detail.html）

四大段：

1. **基本資訊**：id、名稱、描述、版本
2. **屬性 schema**：roles 與 targets 兩段，每個屬性的 key、type、required、繁中 description、aliases
3. **規則**：表格列出每條規則的 id + 自然語言說明
4. **UI 欄位 / 稽核報告欄位 / preferences schema**（若有）

頁底「立即使用此模板」按鈕。

---

## 新建媒合 `/match/new`（new_match.html + partials）

四步驟向導，單頁 + HTMX swap：

1. **Step 1**：選模板（下拉或卡片）；可由 `?template_id=` 預選。
   - 進度條：●○○○
2. **Step 2**：上傳名單檔（CSV 或 Excel）；附「下載範例 CSV」連結。
   - 進度條：●●○○
   - 附簡短說明：「檔案需含模板宣告的屬性欄位；中文表頭可用」
3. **Step 3**：輸入隨機種子（整數）；附說明「相同種子可重現結果」。
   - 進度條：●●●○
4. **Step 4**：確認並執行；顯示已選模板、檔案、seed 摘要。
   - 進度條：●●●●

任一步失敗 → 顯示 `partials/error.html`（紅色框 + 三段式錯誤 + 「重試」按鈕）。

---

## 結果頁 `/match/{record_id}`（match_result.html）

### 成功模式

- 頂部標題：「媒合完成」+ 時間
- 媒合摘要卡片：模板名 / seed / 資格集合大小 / 已分配人數
- **分配表**：表格（角色顯示名 → 對象顯示名）
- 操作按鈕：
  - 「下載稽核紀錄」（GET /match/{id}/audit）
  - 「再執行一次」（連到 /match/new 並預填當前模板）
  - 「回到媒合列表」

### 失敗模式

- 頂部標題：「媒合失敗」+ 時間
- 錯誤訊息卡片：error.type、exit_code、繁中三段式訊息
- 輸入摘要：模板名 / 上傳檔名 / seed
- 操作按鈕：「重試」（連到 /match/new 並預填當前模板）

---

## 過去媒合列表 `/matches`（records_list.html）

表格列出最近 50 筆：

| 時間 | 模板 | seed | 狀態 | 操作 |
|---|---|---|---|---|
| 2026-05-22 14:30 | 教師-班級配對 | 123456 | ✅ 成功 | [查看] [下載 audit] |
| 2026-05-22 14:00 | 研習分組 | 2026 | ❌ 失敗（編碼） | [查看] |

依時間遞減；空狀態：「尚未執行任何媒合。[新建第一次媒合]」

---

## 共用元件

### `partials/error.html`

```html
<div class="error-box">
  <strong>錯誤：{{ error.type }}</strong>
  <p>{{ error.message }}</p>
  {% if error.suggestion %}<p class="suggestion">建議：{{ error.suggestion }}</p>{% endif %}
</div>
```

### `partials/upload_field.html`

```html
<label>
  名單檔（CSV 或 .xlsx，≤ 5 MB）：
  <input type="file" name="roster" accept=".csv,.xlsx" required>
</label>
<small>檔案需含模板宣告的屬性欄位；表頭可用中文或英文。</small>
```

---

## 樣式（style.css）

極簡：

- 字體：system-ui
- 主色：#2c5282（藍）；強調色：#38a169（綠）；錯誤色：#c53030（紅）
- 卡片式佈局；最大寬度 1024px；padding 1rem
- 響應式：mobile 視為次要目標（行政常用桌機）
- 無 CSS 框架

---

## 不變式（測試會驗證）

- 任一頁面 response body 為合法 HTML（含 lang="zh-Hant"）
- 任一頁面**不含**「seed」「audit」等技術術語直譯——須翻譯為「隨機種子」「稽核紀錄」（SC-009 例外：頁面下方的範例 CLI 指令區段可保留英文）
- 任一錯誤頁含「重試」或「回到首頁」連結

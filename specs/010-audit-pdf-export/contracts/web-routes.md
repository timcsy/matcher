# Web Routes Contract — feature 010

新增 2 個端點；既有端點不變。

## GET /match/{record_id}/report.pdf

**新增**：admin 版 PDF 下載。

**回應**：

| 情境 | Status | 內容 |
|---|---|---|
| record 不存在 | 404 | JSON 或樣板：「找不到該次媒合的紀錄」 |
| record 為 failed status | 200 | admin PDF（失敗版，含錯誤訊息） |
| record 成功 | 200 | admin PDF；headers：`Content-Type: application/pdf`、`Content-Disposition: attachment; filename="{record_id}.report.pdf"` |
| WeasyPrint 不可用 | 503 | text/plain 或 HTML：「PDF 渲染功能不可用——請見 README 安裝 WeasyPrint 系統依賴（macOS: brew install pango）」 |

## GET /match/{record_id}/role/{role_id}/report.pdf

**新增**：individual 版 PDF 下載。

**回應**：

| 情境 | Status | 內容 |
|---|---|---|
| record 不存在 | 404 | 「找不到該次媒合的紀錄」 |
| role_id 不在 record | 404 | 「您不在這次媒合的名單中」 |
| record 為 failed | 404 | 「該次媒合執行失敗，無個別查詢資料」 |
| WeasyPrint 不可用 | 503 | 同 admin |
| 成功 | 200 | individual PDF；filename：`{record_id}-{role_id}.report.pdf` |

## GET /match/{record_id}（修改：HTML 樣板）

**變更**：`match_result.html` 在 admin 結果頁的「下載稽核紀錄」按鈕旁新增「下載 PDF 報告」連結，指向 `/match/{rid}/report.pdf`。

## GET /match/{record_id}/role/{role_id}（修改：HTML 樣板）

**變更**：`individual_view.html` 在「下載我的稽核紀錄」按鈕旁新增「下載我的報告 PDF」連結，指向 `/match/{rid}/role/{role_id}/report.pdf`。

## 不變的契約

- 既有所有端點：完全不變
- record / audit schema：不升版
- 既有 HTML 元素 name/id：不改名（僅新增 anchor）

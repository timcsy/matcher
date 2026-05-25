# Quickstart — feature 012 Web UI 直接填名單

8 步驟端到端驗收。

## 0. 啟動

```bash
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib uv run uvicorn matcher.web.app:app --port 8417 --reload
```

開 `http://localhost:8417/match/new`

## 1. 三選一入口（US1）

頁面應顯示三個並列按鈕：
- 📂 上傳名單檔（預設）
- ✏️ 直接填名單
- 📌 從過去紀錄（連結到 /matches）

點「✏️ 直接填名單」→ 切換顯示「選範本」段。

## 2. 跳填寫頁

選範本 teacher-class → 點「開始填寫」→ 跳 `/match/new/fill?template_id=teacher-class`。

驗收：填寫頁顯示
- 標題「填寫名單」
- 「① 角色清單」段，預設 2 列；每列依範本宣告含 3 欄輸入（姓名 / 老師專業科目 / 年資（年））+ × 移除按鈕
- 「＋ 新增一位」按鈕
- 因 teacher-class 有 default_targets → **不顯示**「② 對象清單」段
- 機制下拉（純抽籤 / 輪流挑 / 依志願先後填滿）
- 亂數種子輸入
- 「執行配對」按鈕

## 3. 填 7 位老師（US1）

點「＋ 新增一位」5 次（總共 7 列）。隨意填入：
| 姓名 | 專業 | 年資 |
|---|---|---|
| 王老師 | 國文 | 8 |
| ... | ... | ... |

填亂數種子 `2026`、機制「純抽籤」→ 點「執行配對」。

驗收：跳結果頁、配對表 7 位、分配到 teacher-class 預設班級。

## 4. Web/CSV 等價（SC-002）

把步驟 3 的 7 位老師寫成 CSV：

```csv
id,姓名,專業科目,年資
T01,王老師,國文,8
...
```

CLI 跑：
```bash
uv run matcher run --template teacher-class --roster-csv test.csv --seed 2026 --output cli.json
```

下載步驟 3 的 audit JSON → 比對五段（qualified_set / assignment / filter_trace / allocation_trace / template_snapshot）逐位元組相同。

## 5. 自訂範本無 default_targets（US2）

1. 到 `/templates/new` 建一個自訂範本（無預設對象段，因為 UI 已拿掉）
2. 回 `/match/new` → 直接填名單 → 選此自訂範本
3. 填寫頁應同時顯示「① 角色清單」+「② 對象清單」兩段
4. 填好兩段 → 跑通

## 6. M1/M2 接續填志願頁（US3）

選一個有 preferences_schema 的範本（如自訂範本含志願功能）→ 填名單 → 選「輪流挑」→ 執行 → 應跳 `/match/preferences` 填志願頁（feature 009）→ 填志願 → 跑通。

## 7. 規模測試

填 25 位角色 → 跑通；填 50 位 → UI 顯示提示「建議改用 CSV 上傳」（不阻擋）。

## 8. 自動化測試

```bash
uv run pytest -q
```

預期：既有 322 + 新增 ≥ 10 全綠。

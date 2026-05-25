# Quickstart — feature 010 PDF 報告匯出

8 步驟端到端驗收 + Web/CLI 三入口。

## 0. 前置

```bash
# 安裝系統依賴
brew install pango          # macOS
# apt install libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b  # Debian/Ubuntu

uv sync                      # 含 weasyprint
```

## 1. 啟動 Web

```bash
uv run uvicorn matcher.web.app:app --port 8765 --reload
```

## 2. 跑一次 M2 媒合

`/match/new` → study-group + roster-m1.csv + seed=2026 + M2 → 執行。

## 3. 下載 admin PDF（US1）

結果頁應有「下載 PDF 報告」按鈕。點擊 → 取得 `<record_id>.report.pdf`。

驗收項：
- 用 Adobe Reader / 系統預覽開啟成功
- 第一頁含標題「媒合報告」+ 模板名 + 紀錄編號 + 時間 + 「M2 Boston 層級填滿」+ seed=2026
- 處理順序段顯示
- 分配表 9 列含「志願排名」欄
- 用 PDF 閱讀器搜尋「程式組」、「第 1 志願」應命中（非 outline glyph）

## 4. 下載 individual PDF（US2）

任一學生個別查詢頁 → 點「下載我的報告 PDF」→ 取得 `<rid>-S01.report.pdf`。

驗收項：
- 含學生姓名、被分到的對象、第幾志願（或抽籤）
- **不**含其他學生姓名
- 通過技術詞零容忍（PDF 內無 `preference_rank` / `processing_order` / `filter_trace` 等英文 token）

## 5. CLI admin PDF（US3）

```bash
uv run matcher report \
  --audit /tmp/web-audit.json \
  --output /tmp/cli-admin.pdf
```

驗收項：
- exit 0；stdout 含「PDF 已寫入 /tmp/cli-admin.pdf」
- 內容欄位與 Web 下載的 admin PDF 100% 相同（不要求 bytewise）

## 6. CLI individual PDF

```bash
uv run matcher report \
  --audit /tmp/web-audit.json \
  --role-id S01 \
  --output /tmp/cli-s01.pdf
```

驗收項：與 Web 個別 PDF 內容欄位相同。

## 7. 失敗路徑驗證

- audit 缺欄位：`uv run matcher report --audit /tmp/empty.json --output x.pdf` → exit 51 + 「audit 缺欄位」
- role_id 不存在：`--role-id S99` → exit 52
- WeasyPrint 未裝（手動模擬：在無 pango 環境跑）→ exit 50 + 安裝指引

## 8. 自動化測試

```bash
uv run pytest -q
```

預期：既有 256 + 新增 ≥ 10 全綠。

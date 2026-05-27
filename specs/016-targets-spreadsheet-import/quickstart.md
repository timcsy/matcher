# Quickstart — 驗證 feature 016

## SC-001/002 兩個試算表匯入（CSV + Excel 混搭）
- 上傳頁選 teacher-class → 上傳老師 CSV + 班級 CSV（或 xlsx）→ 配對成功
- 班級檔欄位：編號/容量/班級名稱/班級需要的科目清單/班級特色

## SC-003 中文表頭自動對齊
- 班級檔表頭用中文（班級名稱、需要科目…）→ 正確對齊範本對象屬性

## SC-004 對象檔無編號欄 → 自動編號
- 班級檔不含「編號」欄 → 載入後對象自動取得 T001…

## SC-005 試算表 vs YAML 旁檔等價
- 同一份對象資料：一次用對象 CSV、一次用 .targets.yaml → audit.roster_snapshot.targets 等價

## SC-006 CLI 旁檔仍正常
- `matcher run --template teacher-class --roster-csv examples/teacher-class/roster.csv --seed 2026`
  （沿用 roster.targets.yaml 旁檔）→ exit 0

## SC-008/009 動態範例
- `GET /templates/teacher-class/example/targets.csv` → 表頭 = 編號,容量,班級名稱,班級需要的科目清單,班級特色 + 提示列
- 自訂範本加一個對象屬性 → 重新下載 → 表頭含新欄
- 上傳頁有角色/對象的 CSV/Excel 範例下載連結

## SC-007 全測試
```bash
uv run pytest -q
# 核心僅動 data_import
git diff main --name-only -- 'src/matcher' ':!src/matcher/web' ':!src/matcher/templates' | grep -v data_import || echo "核心僅動 data_import ✅"
```

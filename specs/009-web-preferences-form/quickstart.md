# Quickstart — feature 009 Web UI 填志願表單

7 分鐘端到端跑通 + 驗收 3 條路徑（正常填、skip、CSV 已含 prefs）。

## 0. 前置

- 已 `uv sync`
- 在 repo root

## 1. 啟動 Web

```bash
uv run uvicorn matcher.web.app:app --port 8765 --reload
```

開 `http://localhost:8765`

## 2. 準備「無志願欄」CSV（測試 US1）

```bash
cat > /tmp/students-no-prefs.csv <<'EOF'
id,姓名,年級,志願組別
S01,小明,5,
S02,小華,4,
S03,小美,6,
S04,小強,5,
S05,小芳,4,
EOF
```

## 3. 正常填志願路徑（US1）

1. 點「新建媒合」
2. 模板選 `study-group`
3. 上傳 `/tmp/students-no-prefs.csv`
4. 隨機種子 `2026`
5. 機制選 **M1 RSD**
6. 點「執行媒合」→ **應跳到填志願中介頁面**

期待看到：
- 標題「填寫志願」
- 「候選對象」段：「程式組（容量 3 人）」「自然組（容量 3 人）」「人文組（容量 3 人）」
- 表格 5 列（5 學生），每列 3 個下拉（「您的第 1/2/3 志願」）
- 表格上方提示「離開頁面不會自動儲存」
- 底部「確認執行」+ 「跳過此步驟，以全空志願執行」按鈕

填志願（範例）：
- 小明 S01：程式組 / 自然組 /（未選）
- 小華 S02：程式組 /（未選）/（未選）
- 小美 S03：人文組 / 程式組 /（未選）
- 小強 S04：自然組 / 程式組 /（未選）
- 小芳 S05：自然組 /（未選）/（未選）

點「確認執行」→ 跳到結果頁、顯示「分配階段（M1 RSD 隨機輪流挑）」、處理順序段、志願排名欄。

## 4. 驗收 Web/CSV bytewise 等價

把步驟 3 的志願寫到 CSV：

```bash
cat > /tmp/students-with-prefs.csv <<'EOF'
id,姓名,年級,志願組別
S01,小明,5,G1;G2
S02,小華,4,G1
S03,小美,6,G3;G1
S04,小強,5,G2;G1
S05,小芳,4,G2
EOF
```

CLI 跑：

```bash
uv run matcher run --template study-group \
  --roster-csv /tmp/students-with-prefs.csv \
  --seed 2026 --mechanism M1 \
  --output /tmp/cli-prefs.json
```

下載步驟 3 的 audit（結果頁「下載稽核紀錄」），比對：

```bash
uv run python -c "
import json
a = json.load(open('/tmp/cli-prefs.json'))
b = json.load(open('/path/to/web-audit.json'))
for k in ('qualified_set','assignment','filter_trace','allocation_trace','template_snapshot'):
    print(k, '=' if json.dumps(a[k], sort_keys=True) == json.dumps(b[k], sort_keys=True) else '≠')
"
```

5 個全 `=` 即通過 SC-001。

## 5. Skip 路徑（US2）

回到 `/match/new`，同樣上傳 `students-no-prefs.csv` + M1 → 跳到填志願頁 → 點「跳過此步驟」→ 結果頁顯示失敗：「M1 需要至少一位角色提供志願」。

## 6. CSV 已含 prefs 不跳頁（US2）

`/match/new` 上傳 `/tmp/students-with-prefs.csv` + M1 → **不跳填志願頁**、直接執行（既有 008 行為）。

## 7. M0 不跳頁

`/match/new` 上傳 `students-no-prefs.csv` + M0（即使模板有 schema）→ **不跳填志願頁**、直接執行。

## 8. 驗證 UI 文案無技術詞

任一填志願頁載入後，用瀏覽器「檢視原始碼」搜尋：
- `default_targets`、`preferences_schema`、`max_choices`、`preference_rank`、`preferred_order`
- 全部應 0 命中

## 9. 自動化測試

```bash
uv run pytest -q
```

預期：既有 234 + 新增 ≥ 10 全綠。

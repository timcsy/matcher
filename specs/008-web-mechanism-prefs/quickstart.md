# Quickstart — feature 008 Web UI 機制選擇

5 分鐘端到端跑通 M2 並驗收三種文案。

## 0. 前置

- 已安裝 uv、已 `uv sync`（沿用既有環境）
- 在 repo root

## 1. 啟動 Web

```bash
uv run uvicorn matcher.web.app:app --port 8765 --reload
```

開瀏覽器 → `http://localhost:8765`

## 2. 跑 M2

1. 點「新建媒合」
2. 模板選 `study-group`
3. 上傳 `examples/study-group/roster-m1.csv`
4. 隨機種子填 `2026`
5. **「分配機制」下拉選 `M2 Boston（層級填滿）`** ← 本 feature 新增
6. 點「執行」

## 3. 結果頁應看到

- 標題：「分配階段（M2 Boston 層級填滿）」
- **處理順序段**：「處理順序：S01（…） → S02（…） → ...」
- 分配表多一欄「志願排名」，內容為「第 1 志願」「第 2 志願」或「抽籤」

## 4. 個別查詢頁

點任一被媒合者 → 個別查詢頁應出現以下其一：

- 「您被分到第 1 志願：研習 A」（preference_rank=1）
- 「您原本的志願已被分配給其他人，由公平抽籤分到 研習 C」（fallback + 有志願）
- 「您未在志願清單中，由公平抽籤分到 研習 D」（fallback + 無志願）

## 5. 驗收 M0 路徑（向後相容）

回到 `/match/new`，選 `teacher-class` 模板 + `roster.yaml` + mechanism `M0`（預設）→ 結果頁**不**出現「處理順序」段；分配表**不**出現「志願排名」欄；個別查詢頁**不**出現「您被分到第幾志願」段。

## 6. 驗收拒絕路徑

`/match/new` 選 `study-group` + 上傳 `examples/study-group/roster.yaml`（全空 prefs）+ mechanism `M1` → 結果頁顯示失敗：「M1 需要至少一位角色提供志願」與「改用 mechanism=M0」建議。換選 M2 重跑 → 訊息為「M2 需要至少一位角色提供志願」。

## 7. 驗收 Web/CLI 等價

```bash
# CLI 跑同模板、同 seed、同 mechanism
uv run matcher run \
  --template study-group \
  --roster-csv examples/study-group/roster-m1.csv \
  --seed 2026 \
  --mechanism M2 \
  --output /tmp/cli-m2.json
```

下載步驟 2 跑出的 audit JSON（Web 結果頁有「下載 audit」按鈕）→ 比對五個核心欄位：

```bash
uv run python -c "
import json
a = json.load(open('/tmp/cli-m2.json'))
b = json.load(open('/path/to/downloaded-audit.json'))
for k in ('qualified_set','assignment','filter_trace','allocation_trace','template_snapshot'):
    s_a = json.dumps(a[k], sort_keys=True, ensure_ascii=False)
    s_b = json.dumps(b[k], sort_keys=True, ensure_ascii=False)
    print(k, '=' if s_a == s_b else '≠')
"
```

5 個全 `=` 即通過 SC-001。

## 8. 自動化測試

```bash
uv run pytest -q
```

預期：既有 210 + 新增 ≥ 8 全綠。

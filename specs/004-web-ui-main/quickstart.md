# Quickstart：Web UI 主流程

**Branch**: `004-web-ui-main` | **Date**: 2026-05-22

---

## 前置條件

- Python 3.11+ 與 uv
- 已安裝本套件（`uv pip install -e ".[dev]"`，含新依賴 fastapi / uvicorn / jinja2 / python-multipart）

---

## 1. 啟動本地 server

```bash
uv run matcher serve
# 預設綁定 127.0.0.1:8000
```

或開發模式（自動重載）：

```bash
uv run matcher serve --reload
```

預期 stdout：

```text
INFO:     Uvicorn running on http://127.0.0.1:8000
```

---

## 2. 開啟瀏覽器

訪問 <http://127.0.0.1:8000/>，應看到首頁三個主要入口。

---

## 3. 跑通教師-班級基準場景

1. 點「新建媒合」
2. Step 1：選「教師-班級配對」
3. Step 2：上傳 `examples/teacher-class/roster.csv`
4. Step 3：輸入 seed `123456`
5. Step 4：確認 → 執行
6. 結果頁應顯示 10 位老師對應到 5 個班級的分配表（5 秒內）

預期：頁面顯示分配表 + 「下載稽核紀錄」按鈕。

---

## 4. 下載稽核並驗證等價（SC-003）

```bash
# 下載 Web 路徑的 audit
curl http://127.0.0.1:8000/match/<record_id>/audit -o /tmp/web-audit.json

# CLI 同樣輸入跑一次
uv run matcher run \
  --template teacher-class \
  --roster-csv examples/teacher-class/roster.csv \
  --seed 123456 \
  --output /tmp/cli-audit.json

# 比對五個核心欄位
uv run python -c "
import json
w = json.load(open('/tmp/web-audit.json'))
c = json.load(open('/tmp/cli-audit.json'))
for k in ['qualified_set','assignment','filter_trace','allocation_trace','template_snapshot']:
    assert w[k] == c[k], f'{k} differs'
print('✅ 五段完全相同')
"
```

預期：「✅ 五段完全相同」。

---

## 5. 模板瀏覽

訪問 <http://127.0.0.1:8000/templates>，應看到 teacher-class 與 study-group 兩張卡片；
點 teacher-class → 看完整 schema、規則、UI 欄位、預設對象。

---

## 6. 過去媒合列表

訪問 <http://127.0.0.1:8000/matches>，應看到剛剛跑的那筆紀錄；點「查看」可重現結果頁。

---

## 7. 錯誤情境測試

### 7a. 上傳超大檔（> 5 MB）

```bash
uv run python -c "
with open('/tmp/big.csv', 'w') as f:
    f.write('id,姓名,專業科目,年資\n')
    for i in range(200000):
        f.write(f'T{i:06d},X,Y,5\n')
"
# 透過瀏覽器嘗試上傳 → 預期 400 + 「檔案過大」訊息
```

### 7b. 格式錯誤 CSV（缺欄位）

上傳一份僅含「姓名,年資」（缺專業科目）的 CSV → 結果頁顯示失敗、訊息含「缺漏 `speciality`」。

---

## 8. 跑測試

```bash
uv run pytest                                       # 全部測試
uv run pytest tests/integration/test_web_*          # Web 整合測試
uv run pytest tests/unit/test_web_store.py
```

預期：全部通過（階段 1+2a+2b 既有 116 + 階段 3a 新增 ≈ 25）。

---

## 對應 spec.md 章節

| Quickstart 步驟 | 對應 Acceptance / SC |
|---|---|
| 1. 啟動 server | FR-001 |
| 3. 跑通主流程 | US1 Acceptance #1、SC-002 |
| 4. SC-003 等價驗證 | SC-003 |
| 5. 模板瀏覽 | US2、SC-004 |
| 6. 過去媒合 | US3、SC-005 |
| 7. 錯誤情境 | SC-006、SC-010 |
| 8. 跑測試 | SC-008 |

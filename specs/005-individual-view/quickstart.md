# Quickstart：個別查詢視圖

**Branch**: `005-individual-view` | **Date**: 2026-05-23

---

## 前置條件

- Python 3.11+ 與 uv
- 已安裝本套件（`uv pip install -e ".[dev]"`，無新依賴）

---

## 1. 啟動 server 並跑一次媒合

```bash
uv run matcher serve --port 47291 &
sleep 2

# 用瀏覽器 or curl 跑一次教師-班級媒合
curl -X POST http://127.0.0.1:47291/match/run \
  -F template_id=teacher-class \
  -F seed=123456 \
  -F roster=@examples/teacher-class/roster.csv
# 取得 redirect 後的 record_id（從 server log 或瀏覽器網址）
```

或乾脆透過瀏覽器跑：
http://127.0.0.1:47291/match/new

---

## 2. 行政視圖看「個別查詢連結」

開啟 `http://127.0.0.1:47291/match/<record_id>`。

預期：頁面下方有 `<details>` 區段「個別查詢連結（共 10 位）」；展開後看到 10 列表格（姓名 / role_id / 連結）。

---

## 3. 開啟個別查詢頁

從 admin 視圖點任一個別查詢連結，或直接訪問：

```text
http://127.0.0.1:47291/match/<record_id>/role/T01
```

預期：
- 「您的姓名 / 專業 / 年資」基本資訊
- 「您被分到：三年丁班」（或對應結果）
- 「媒合過程說明」列出每條規則的繁中描述（已做代名詞替換）+ 通過/不通過
- 頁面不含「filter_trace」「role.speciality」等技術詞
- 下方「下載我的稽核紀錄」連結

---

## 4. 下載個別 audit 子集

```bash
curl http://127.0.0.1:47291/match/<record_id>/role/T01/audit.json | jq .
```

預期：JSON 含 `role_attributes`、`assignment`、`filter_trace_subset`（10 條，每個 target 一條）、`allocation_step`。

---

## 5. 驗證可重現性（SC-005）

```bash
curl -s http://127.0.0.1:47291/match/<record_id>/role/T01 > /tmp/a.html
curl -s http://127.0.0.1:47291/match/<record_id>/role/T01 > /tmp/b.html
diff /tmp/a.html /tmp/b.html && echo "✅ 完全相同"
```

預期：印出「✅ 完全相同」。

---

## 6. 錯誤情境

```bash
# 不存在的 record
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:47291/match/no-such-id/role/T01
# 預期：404

# 存在的 record 但 role 不在名單
curl -s http://127.0.0.1:47291/match/<record_id>/role/T999 | grep "不在這次媒合"
# 預期：含「您不在這次媒合的名單中」

# 失敗紀錄
# 先跑一個失敗的 (例如缺欄位 CSV) 取得 record_id_failed
curl -s http://127.0.0.1:47291/match/<record_id_failed>/role/T01 | grep "執行失敗"
```

---

## 7. 技術詞零容忍驗證（SC-002）

```bash
curl -s http://127.0.0.1:47291/match/<record_id>/role/T01 > /tmp/page.html
grep -E "filter_trace|allocation_trace|qualified_set|random_index|exit_code|role\.\w+|target\.\w+" /tmp/page.html \
    && echo "❌ 含技術詞" || echo "✅ 無技術詞"
```

預期：印出「✅ 無技術詞」。

---

## 8. 跑測試

```bash
uv run pytest                                       # 全部測試
uv run pytest tests/unit/test_web_humanize.py
uv run pytest tests/unit/test_web_individual_subset.py
uv run pytest tests/integration/test_web_individual_view.py
```

預期：全部通過（既有 142 + 階段 3b 新增 ≈ 15）。

---

## 對應 spec.md 章節

| Quickstart 步驟 | 對應 Acceptance / SC |
|---|---|
| 1-2. admin 視圖連結 | US2、SC-004 |
| 3. 個別查詢頁 | US1、FR-002 |
| 4. 下載 audit 子集 | FR-012、SC-006 |
| 5. 可重現性 | SC-005 |
| 6. 錯誤情境 | US3、SC-003 |
| 7. 技術詞零容忍 | FR-003、SC-002 |
| 8. 跑測試 | SC-007、SC-008 |

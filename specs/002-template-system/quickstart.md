# Quickstart：模板系統

**Branch**: `002-template-system` | **Date**: 2026-05-22

最小可跑示範：列出模板 → 用內建模板執行媒合 → 匯出/匯入驗證冪等。

---

## 前置條件

- Python 3.11+ 與 uv
- 已安裝本套件（`uv pip install -e ".[dev]"`）

---

## 1. 列出可用模板

```bash
uv run matcher template list
```

預期輸出：

```text
ID             名稱            一句話描述
-------------  --------------  ----------------------------------------
teacher-class  教師-班級配對   依專業與班級需要科目配對任課教師
study-group    研習分組        依年級與容量限制分配學生到研習組別
```

---

## 2. 檢視模板完整內容

```bash
uv run matcher template show teacher-class
```

預期輸出含：基本資訊、屬性 schema、規則列表、UI 欄位宣告、報告欄位宣告。

```bash
uv run matcher template show study-group
```

預期輸出**包含** `preferences_schema` 區塊（標示為「未來機制使用，本階段不啟用」）。

---

## 3. 以模板執行教師-班級基準場景

```bash
uv run matcher run \
  --template teacher-class \
  --roster   examples/teacher-class/roster.yaml \
  --seed     123456 \
  --output   /tmp/audit-via-template.json
```

預期：

- exit 0
- stdout 含「=== 模板 === ID：teacher-class」段
- `/tmp/audit-via-template.json` 含 `template_snapshot` 欄位（teacher-class 完整內容）

---

## 4. 驗證模板匯出-匯入冪等（SC-003）

```bash
# 匯出
uv run matcher template export teacher-class --output /tmp/tc.yaml

# 用匯出檔再跑一次
uv run matcher run \
  --template-file /tmp/tc.yaml \
  --roster        examples/teacher-class/roster.yaml \
  --seed          123456 \
  --output        /tmp/audit-via-file.json

# 兩份應逐位元組相同
diff /tmp/audit-via-template.json /tmp/audit-via-file.json && echo "✅ 完全相同"
```

預期：`diff` 無輸出。

---

## 5. 「研習分組」場景（含 preferences 拒絕）

```bash
# 5a. 不帶 preferences → 純抽籤通過
uv run matcher run \
  --template study-group \
  --roster   examples/study-group/roster.yaml \
  --seed     2026 \
  --output   /tmp/study-audit.json
# 預期 exit 0

# 5b. 帶 preferences → 在 M0 機制下被拒絕（SC-006）
uv run matcher run \
  --template study-group \
  --roster   examples/study-group/roster-with-preferences.yaml \
  --seed     2026
# 預期 exit 17
# 訊息含「此機制（M0 純抽籤）不接受志願輸入」「階段 4」
```

---

## 6. 向後相容驗證（SC-007）

```bash
# 階段 1 的呼叫方式必須完全不變
uv run matcher run \
  --rules  examples/teacher-class/rules.yaml \
  --roster examples/teacher-class/roster.yaml \
  --seed   123456 \
  --output /tmp/legacy.json
# 預期 exit 0；audit 中 template_snapshot 為 null
```

---

## 7. 跑測試

```bash
uv run pytest                     # 全部測試（含階段 1 既有 48 個）
uv run pytest tests/unit/test_template.py
uv run pytest tests/integration/test_template_run.py
uv run pytest tests/integration/test_backward_compatibility.py
```

預期：全部通過。

---

## 對應 spec.md 章節

| Quickstart 步驟 | 對應 Acceptance / SC |
|---|---|
| 1. list | US2 Acceptance #1、SC-001 |
| 2. show | US2 Acceptance #2、SC-001 |
| 3. 以模板執行 | US1 Acceptance #1、SC-002 |
| 4. 匯出-匯入冪等 | US2 Acceptance #3、SC-003 |
| 5a. 研習分組無 prefs | US1 Acceptance #2、SC-002 |
| 5b. 研習分組帶 prefs | US3 Acceptance #1、SC-006 |
| 6. 向後相容 | SC-007 |
| 7. 跑測試 | SC-009 |

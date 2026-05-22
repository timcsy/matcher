# Quickstart：資料匯入（CSV / Excel）

**Branch**: `003-data-import` | **Date**: 2026-05-22

---

## 前置條件

- Python 3.11+ 與 uv
- 已安裝本套件（`uv pip install -e ".[dev]"`，含 openpyxl 新依賴）

---

## 1. CSV 匯入：教師-班級基準場景

```bash
uv run matcher run \
  --template  teacher-class \
  --roster-csv examples/teacher-class/roster.csv \
  --seed      123456 \
  --output    /tmp/audit-csv.json
```

預期：

- exit 0
- stdout 含「=== 資料來源 ===」段，標示 csv / utf-8-sig / row_count
- audit JSON 中 `import_metadata.source_type == "csv"`、`schema_version == "1.2"`

## 2. CSV 三路徑等價驗證（SC-001）

```bash
# 以 YAML 名單跑
uv run matcher run --template teacher-class \
                   --roster examples/teacher-class/roster.yaml \
                   --seed 123456 --output /tmp/audit-yaml.json

# 以 CSV 名單跑
uv run matcher run --template teacher-class \
                   --roster-csv examples/teacher-class/roster.csv \
                   --seed 123456 --output /tmp/audit-csv.json

# 比對核心五段
uv run python -c "
import json
a = json.load(open('/tmp/audit-yaml.json'))
b = json.load(open('/tmp/audit-csv.json'))
for key in ['qualified_set', 'assignment', 'filter_trace', 'allocation_trace', 'template_snapshot']:
    assert a[key] == b[key], f'{key} differs'
print('✅ 五段完全相同')
"
```

預期：印出「✅ 五段完全相同」。

## 3. Excel 匯入：研習分組（單一工作表）

```bash
uv run matcher run \
  --template   study-group \
  --roster-xlsx examples/study-group/roster.xlsx \
  --seed       2026 \
  --output     /tmp/audit-xlsx.json
```

預期：

- exit 0
- stdout 含「=== 資料來源 === xlsx ...」段
- audit `import_metadata.source_type == "xlsx"`

## 4. Excel 多工作表場景

```bash
# 多工作表檔（範例：含「報名表」「說明」「範例」三張）
uv run matcher run --template study-group \
                   --roster-xlsx examples/study-group/roster-multi.xlsx \
                   --seed 2026
# 預期 exit 33；訊息列出三張工作表名稱

uv run matcher run --template study-group \
                   --roster-xlsx examples/study-group/roster-multi.xlsx \
                   --sheet "報名表" \
                   --seed 2026 --output /tmp/a.json
# 預期 exit 0
```

## 5. 編碼錯誤路徑

```bash
# 構造一份 UTF-16 編碼的 CSV
uv run python -c "
with open('/tmp/utf16.csv', 'wb') as f:
    f.write('姓名,專業科目,年資\n王老師,國文,8\n'.encode('utf-16'))
"

uv run matcher run --template teacher-class \
                   --roster-csv /tmp/utf16.csv --seed 1
# 預期 exit 30；訊息列出已嘗試的編碼
```

## 6. 型別錯誤路徑

```bash
# 構造一份含「八年」的 CSV
uv run python -c "
with open('/tmp/badtype.csv', 'w', encoding='utf-8') as f:
    f.write('姓名,專業科目,年資\n王老師,國文,八年\n')
"

uv run matcher run --template teacher-class \
                   --roster-csv /tmp/badtype.csv --seed 1
# 預期 exit 32；訊息指出列號、欄位、值
```

## 7. preferences 拒絕路徑（CSV）

研習分組 CSV 含非空 preferences：

```csv
姓名,年級,志願組別
小明,5,G1;G2;G3
```

```bash
uv run matcher run --template study-group \
                   --roster-csv /tmp/pref.csv --seed 1
# 預期 exit 17（沿用階段 1 PreferencesNotSupported）
```

## 8. 向後相容

```bash
# 階段 1/2a 既有 YAML 路徑必須完全不變
uv run matcher run --rules examples/teacher-class/rules.yaml \
                   --roster examples/teacher-class/roster.yaml \
                   --seed 123456 --output /tmp/legacy.json
# 預期 exit 0；audit import_metadata 為 null
```

## 9. 跑測試

```bash
uv run pytest                                       # 全部測試
uv run pytest tests/integration/test_csv_import.py
uv run pytest tests/integration/test_xlsx_import.py
uv run pytest tests/integration/test_import_errors.py
uv run pytest tests/integration/test_backward_compat_v003.py
```

預期：全部通過（包含階段 1+2a 既有 82 + 階段 2b 新增 ≈ 30）。

---

## 對應 spec.md 章節

| Quickstart 步驟 | 對應 Acceptance / SC |
|---|---|
| 1. CSV 匯入 | US1 #1 + #2、SC-002 |
| 2. 三路徑等價 | SC-001 |
| 3. Excel 單表 | US2 #1、SC-005 |
| 4. Excel 多表 | US2 #3 + #4、SC-005 |
| 5. 編碼錯誤 | US3 #1、SC-002/003 |
| 6. 型別錯誤 | US3 #2、SC-003 |
| 7. preferences 拒絕 | US3、SC-006 |
| 8. 向後相容 | SC-007 |

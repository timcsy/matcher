# CLI Contract: matcher run（擴充）

**Branch**: `003-data-import` | **Date**: 2026-05-22

---

## 修改：`matcher run`

```text
matcher run \
  ( --template <id> | --template-file <path> | --rules <path> ) \
  ( --roster <yaml> | --roster-csv <path> | --roster-xlsx <path> [--sheet <name>] ) \
  --seed <int>
  [--preferences <path>]
  [--mechanism M0]
  [--output <audit.json>]
```

### 規則來源（沿用階段 2a，三組互斥）

未變動：`--template <id>` / `--template-file <path>` / `--rules <path>` 三選一。

### 名單來源（**本階段新增**，三組互斥）

| 組合 | 說明 |
|---|---|
| `--roster <yaml>` | YAML 名單（沿用階段 1） |
| `--roster-csv <path>` | CSV 名單（**新增**） |
| `--roster-xlsx <path>` | Excel .xlsx 名單；多工作表可加 `--sheet <name>`（**新增**） |

任意組合違反互斥（同時提供 ≥ 2 種） → exit 2 + 繁中提示「請擇一」。
未提供任何名單來源 → exit 2 + 提示。

### 退出碼擴充

| Code | 意義 | 對應錯誤類別 | 來源 |
|---|---|---|---|
| 0–17 | 階段 1 既有 | （沿用） | 階段 1 |
| 20–23 | 階段 2a 模板 | （沿用） | 階段 2a |
| 30 | CSV 編碼偵測失敗 | `RosterDecodeError` | **本階段新增** |
| 31 | 表頭缺欄位 / 重複欄位 | `RosterColumnMismatch` | **本階段新增** |
| 32 | 型別轉換失敗 | `RosterTypeError` | **本階段新增** |
| 33 | Excel 工作表歧義 | `RosterSheetAmbiguous` | **本階段新增** |

### 訊息範例

```text
# Code 30
錯誤：無法解碼 CSV 檔案 roster.csv。
細節：已嘗試編碼 utf-8、utf-8-sig、cp950 皆失敗。
建議：請以 Excel 或文字編輯器另存為 UTF-8 編碼後再試。
```

```text
# Code 31（缺欄位）
錯誤：CSV 表頭缺少模板必填欄位。
細節：缺漏 `name`（可用別名：姓名、教師姓名）、`speciality`（可用別名：專業科目、專業）。
建議：在 CSV 中新增上述欄位，或調整模板的 attributes / aliases 宣告。
```

```text
# Code 32
錯誤：第 3 列、欄位 `seniority` 型別轉換失敗。
細節：值「八年」無法解析為整數（int）。
建議：請改為阿拉伯數字（如 8），或調整模板宣告為 str。
```

```text
# Code 33
錯誤：Excel 檔含多張工作表，未指定 --sheet。
細節：可用工作表：「報名表」「說明」「範例」。
建議：以 --sheet "報名表" 指定要匯入的工作表。
```

---

## stdout 摘要擴充

匯入路徑下，stdout 摘要新增一段「資料來源」：

```text
=== 資料來源 ===
類型：csv
編碼：utf-8-sig
資料列數：10
檔案：roster.csv
```

或：

```text
=== 資料來源 ===
類型：xlsx
工作表：報名表
資料列數：9
檔案：study-group-roster.xlsx
```

YAML 路徑不顯示此段（沿用階段 1/2a 行為）。

---

## 不變式（契約測試會驗證）

- **名單來源互斥**：三組同時提供 → exit 2。
- **三路徑等價（SC-001）**：CSV / Excel / YAML 三條路徑配合同模板與同 seed，稽核紀錄在 `qualified_set` / `assignment` / `filter_trace` / `allocation_trace` / `template_snapshot` 五段完全相同。
- **import_metadata 完整性**：CSV/Excel 路徑下，`audit.import_metadata` 含正確的 source_type、encoding (CSV)、sheet_name (xlsx)、row_count、file_basename。YAML 路徑為 `null`。
- **preferences 在 M0 拒絕（SC-006）**：CSV/Excel 匯入後若 preferences 任一筆非空 → exit 17（沿用階段 1）。
- **向後相容（SC-007）**：所有不使用 CSV/Excel 入口的呼叫，行為完全不變；階段 1/2a 既有 82 測試 100% 通過。

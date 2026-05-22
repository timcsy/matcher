# Excel (.xlsx) 格式契約

**Branch**: `003-data-import` | **Date**: 2026-05-22

---

## 檔案格式

- 僅支援 `.xlsx`（OpenXML 格式）
- **不**支援 `.xls`（舊版二進位）、`.xlsm`（含巨集；安全性風險）
- 公式儲存格 → 採**計算結果**（`data_only=True`），不採公式字串

## 工作表選擇

| 情境 | 行為 |
|---|---|
| 單一工作表 | 自動使用，不需 `--sheet` |
| 多工作表 + 未指定 `--sheet` | exit 33 + 列出可用工作表 |
| 多工作表 + 指定不存在的 `--sheet` | exit 33 + 列出實際工作表 |
| 多工作表 + 指定正確的 `--sheet` | 使用指定工作表 |

## 表頭與資料列

規則同 CSV：

- 第一列為表頭
- 表頭兩側空白自動裁切
- 英文不分大小寫；中文嚴格相等
- 欄位順序不重要
- 型別宣告為 `int` → 接受數值儲存格或字串 `"8"`，皆轉為 int 8
- 型別宣告為 `list_str` → 字串儲存格以 `;` 分隔

## 儲存格型別處理

| Excel 儲存格型別 | 模板宣告為 `str` | 模板宣告為 `int` | 模板宣告為 `list_str` |
|---|---|---|---|
| 數值（如 8） | 視為 `"8"` 字串 | 直接取 int(8) | `RosterTypeError`（list_str 不接受數值） |
| 字串（如 "八年"） | `"八年"` | `RosterTypeError`（無法 int） | 以 `;` 切分 |
| 空白／None | `""`（合法） | `RosterTypeError`（缺值） | `[]`（空 list） |
| 公式（含計算結果） | 取計算結果並轉字串 | 取計算結果並轉 int | 取計算結果並切分 |

## 範例（研習分組）

工作表「報名表」：

| 姓名 | 年級 | 志願組別 |
|---|---|---|
| 小明 | 5 | G1;G2;G3 |
| 小華 | 4 | （空） |
| 小美 | 6 | G2 |

CLI：

```bash
matcher run --template study-group --roster-xlsx roster.xlsx --sheet "報名表" --seed 1
```

匯入後等價於 YAML：

```yaml
roles:
  - id: R001
    attributes: {name: "小明", grade: 5}
    preferences: ["G1", "G2", "G3"]
  - id: R002
    attributes: {name: "小華", grade: 4}
    preferences: []
  - id: R003
    attributes: {name: "小美", grade: 6}
    preferences: ["G2"]
```

M0 機制下，因 R001 / R003 的 preferences 非空 → exit 17（沿用階段 1）。

## 不支援的功能

- **合併儲存格**：行為未定義（讀取 openpyxl 提供值，可能為 None）；建議使用者展開後再匯入。
- **隱藏列／欄**：本階段不忽略，全部讀入。
- **資料驗證 / 條件式格式**：忽略。
- **多檔案合併**：YAGNI（spec 排除）。

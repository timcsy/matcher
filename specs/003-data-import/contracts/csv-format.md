# CSV 格式契約

**Branch**: `003-data-import` | **Date**: 2026-05-22

---

## 編碼

支援以下三種（依序嘗試）：

1. **UTF-8**（無 BOM）—— 跨平台首選
2. **UTF-8-SIG**（含 BOM）—— Excel for Windows 另存為 CSV 的預設
3. **CP950**（Big5）—— 老舊系統匯出常見

不在此範圍 → exit 30。

## 分隔符

- 欄位分隔符：`,`（半形逗號，RFC 4180）
- 引號跳脫：雙引號 `""`
- 列分隔符：`\n` 或 `\r\n`（皆接受）

## 表頭

- 第一列必為表頭
- 欄位順序**不重要**（依模板 schema 對齊，不依位置）
- 表頭兩側空白自動裁切
- 英文表頭不分大小寫；中文表頭嚴格相等

## 資料列

- 列數 ≥ 1（不含表頭）；0 列 → `EmptyRoster`
- 模板宣告為 `int` 型別的欄位 → 阿拉伯數字字串
- 模板宣告為 `list_str` 型別的欄位 → 以分號 `;` 分隔（例：`G1; G2; G3`），兩側空白裁切，空字串視為空 list

## 範例（教師-班級配對）

```csv
姓名,專業科目,年資
王老師,國文,8
林老師,數學,6
陳老師,英文,4
```

對齊到模板：

- 「姓名」→ `name`（aliases）
- 「專業科目」→ `speciality`（aliases）
- 「年資」→ `seniority`（aliases）

匯入後等價於：

```yaml
roles:
  - id: ???  # 見下方「id 規則」
    attributes: {name: "王老師", speciality: "國文", seniority: 8}
    preferences: []
```

## id 規則

CSV 不需要也不能含 `id` 欄位；系統會依照**列序自動生成** `R001`、`R002`...

對象（targets）端**不**透過 CSV 匯入；仍以模板宣告或 YAML 提供。

## preferences 欄位

若模板宣告了 `preferences_schema`，CSV 中可有名為 `preferences`（或對應 alias）的欄位：

```csv
姓名,年級,志願組別
小明,5,G1;G2;G3
```

「志願組別」（alias）對齊到 `preferences`；分號分隔的字串展開為 `["G1", "G2", "G3"]`。
M0 機制下若任一筆 preferences 非空 → exit 17（沿用階段 1）。

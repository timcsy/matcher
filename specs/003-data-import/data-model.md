# Data Model: 資料匯入

**Branch**: `003-data-import` | **Date**: 2026-05-22

---

## 新增實體 / 欄位

### `AttributeDecl.aliases`（修改既有實體）

`src/matcher/template.py` 的 `AttributeDecl` dataclass 新增欄位：

| Field | Type | Notes |
|---|---|---|
| `aliases` | `tuple[str, ...]` | 預設空 `()`；列出可接受的 CSV/Excel 表頭別名 |

### `ImportMetadata`（新；稽核紀錄欄位）

序列化形式：

| Field | Type | Notes |
|---|---|---|
| `source_type` | `Literal["csv", "xlsx", "yaml"]` | 必填 |
| `encoding` | `Literal["utf-8", "utf-8-sig", "cp950"] \| None` | CSV 時必填；其他為 null |
| `sheet_name` | `str \| None` | xlsx 時必填；其他為 null |
| `row_count` | `int` | 資料列數（不含表頭） |
| `file_basename` | `str` | 檔案名（不含路徑） |

### 4 個新錯誤類別

```text
RosterDecodeError       exit 30   編碼偵測失敗（3 輪皆失敗）
RosterColumnMismatch    exit 31   表頭缺必填 / 重複欄位
RosterTypeError         exit 32   型別轉換失敗
RosterSheetAmbiguous    exit 33   Excel 多工作表未指定 / 工作表名不存在
```

繼承 `MatcherError`；exit code 30–33 連續、不與既有 10–17（階段 1）、20–23（階段 2）衝突。

---

## 既有實體擴充

### `Template`

無欄位變更；`AttributeDecl` 的 `aliases` 自動透過 attribute schema 帶入。

### `MatcherInput`（修改）

新增欄位：

| Field | Type | Notes |
|---|---|---|
| `import_metadata` | `ImportMetadata \| None` | YAML 路徑為 None；CSV/Excel 路徑為對應 metadata |

### `AuditRecord`（schema 升級 v1.1 → v1.2）

| 新欄位 | Type | Notes |
|---|---|---|
| `import_metadata` | `ImportMetadata \| null` | 沿用「新增可選欄位 + null」模式 |

`schema_version` 從 `"1.1"` 升為 `"1.2"`。

---

## 載入器介面（新）

```text
def detect_csv_encoding(raw_bytes: bytes) -> tuple[str, str]:
    """
    回傳 (encoding, decoded_text)。
    依序嘗試 'utf-8' → 'utf-8-sig' → 'cp950'；皆失敗 → RosterDecodeError。
    """

def load_roster_csv(path: Path, template: Template) -> tuple[Roster, ImportMetadata]:
    """
    1. 讀 bytes → 編碼偵測 → 解碼字串
    2. csv.DictReader 解析
    3. 表頭對齊（依 template.attributes 與 aliases）
    4. 型別轉換（依模板宣告：str / int / list_str）
    5. 組裝 Roster
    """

def load_roster_xlsx(path: Path, template: Template, sheet: str | None = None) -> tuple[Roster, ImportMetadata]:
    """
    1. openpyxl 開啟（read_only=True, data_only=True）
    2. 選擇工作表（單表自動 / 多表須顯式）
    3. 第一列為表頭、後續為資料
    4. 表頭對齊與型別轉換（沿用 csv 路徑相同邏輯）
    5. 組裝 Roster
    """
```

---

## 驗證規則（解析期執行）

| Check | 對應 FR | 觸發錯誤 |
|---|---|---|
| 編碼 3 輪皆失敗 | FR-003 | `RosterDecodeError` |
| 缺必填欄位 | FR-010 | `RosterColumnMismatch`（列出缺漏 + 可接受 aliases） |
| 表頭重複（同 key 出現多次） | FR-011 | `RosterColumnMismatch` |
| 型別轉換失敗（int 無法 parse / list_str 結構錯） | FR-008、FR-013 | `RosterTypeError` |
| Excel ≥ 2 工作表未指定 `--sheet` | FR-005 | `RosterSheetAmbiguous` |
| Excel 指定工作表不存在 | FR-005 | `RosterSheetAmbiguous` |
| 名單為空（只表頭、無資料） | FR-001 + 沿用 | `EmptyRoster`（階段 1） |
| preferences 任一筆非空且 mechanism=M0 | FR-012 | `PreferencesNotSupported`（階段 1） |

---

## 別名對齊演算法（pseudo code）

```text
function resolve_header(csv_header: str, decls: list[AttributeDecl]) -> AttributeDecl | None:
    normalized = csv_header.strip()
    # 第一輪：精確比對 key
    for decl in decls:
        if normalized == decl.key:
            return decl
        # 英文 key 不分大小寫
        if is_ascii(normalized) and is_ascii(decl.key) and normalized.lower() == decl.key.lower():
            return decl
    # 第二輪：比對 aliases（依宣告順序）
    for decl in decls:
        for alias in decl.aliases:
            if normalized == alias:
                return decl
            if is_ascii(normalized) and is_ascii(alias) and normalized.lower() == alias.lower():
                return decl
    return None  # 未匹配 → 忽略此欄
```

---

## 狀態轉移

```text
file path
  → [read bytes (csv) 或 openpyxl (xlsx)]
  → [encoding detect (csv only)]
  → [parse header → align to template]
  → [parse rows → type convert]
  → [build Roster + ImportMetadata]
  → 進入既有 pipeline（無 import 後即與 YAML 路徑無差別）
```

任一步失敗即丟出對應 Exception；錯誤後不繼續流程。

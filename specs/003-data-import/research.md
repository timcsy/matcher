# Research: 資料匯入技術選型

**Branch**: `003-data-import` | **Date**: 2026-05-22

每項決策以「決策 / 理由 / 替代方案」三段式記錄。

---

## R-001 編碼偵測：固定順序 3 輪嘗試

- **Decision**：依序嘗試解碼為 UTF-8 → UTF-8-SIG → CP950；任一輪成功即採用。
  3 輪皆 `UnicodeDecodeError` → 拋 `RosterDecodeError`。
- **Rationale**：
  - 三種覆蓋台灣學校情境 ≥ 99%（Windows Excel 預設、Mac Excel、Notepad++ 等）。
  - 行為**完全確定**——同一檔案在任一機器跑出相同編碼偵測結果，符合原則 2「可重現」。
  - 不引入 chardet（簡潔優先；chardet 採貝氏推論，結果可能因版本變動）。
- **Alternatives considered**：
  - **chardet**：表現好但結果不穩定；對「可重現」場景不友好。
  - **要求使用者明示 `--encoding`**：學校行政不熟悉；額外操作門檻。

---

## R-002 CSV 解析：stdlib `csv` 模組

- **Decision**：使用 `csv.DictReader`（自動以首列為表頭）；分隔符固定 `,`、引號 `"`。
- **Rationale**：
  - 標準函式庫、零依賴。
  - RFC 4180 兼容；處理引號內逗號、跳脫已內建。
- **Alternatives considered**：
  - **pandas**：功能強大但體積龐大、與目前依賴規模不成比例。
  - **手寫解析**：YAGNI，stdlib 已足夠。

---

## R-003 Excel 解析：openpyxl + `read_only` 模式

- **Decision**：使用 `openpyxl.load_workbook(path, read_only=True, data_only=True)`；
  `data_only=True` 取得公式計算結果而非公式字串。
- **Rationale**：
  - 純 Python，跨平台、無需安裝 Excel。
  - `read_only=True` 對大檔記憶體友好（本階段雖然 ≤ 1000 列，仍是好習慣）。
- **Alternatives considered**：
  - **xlrd**：已不維護 .xlsx 支援。
  - **pandas + openpyxl**：把 pandas 拉進來不划算。

---

## R-004 工作表選擇邏輯

- **Decision**：
  - 1 個工作表 → 自動使用，不需要 `--sheet`。
  - ≥ 2 個工作表且未指定 `--sheet` → 拋 `RosterSheetAmbiguous`，列出可用工作表名稱。
  - 指定 `--sheet <name>` 且不存在 → 同樣拋 `RosterSheetAmbiguous`，列出實際工作表。
- **Rationale**：明確拒絕勝過隱式預設；學校 Excel 常見一檔多表（每年級一張），不可猜測。
- **Alternatives considered**：
  - **預設取第一張**：當第一張是「說明」或「範例」時錯誤匯入，無聲失敗。

---

## R-005 別名比對 normalize 規則

- **Decision**：
  - **CSV/Excel 表頭兩側空白自動裁切**（`.strip()`）。
  - **英文（ASCII）alias 比對不區分大小寫**：`name` ≡ `Name` ≡ `NAME`。
  - **中文 alias 嚴格相等**：保留字元正確性（半形/全形不混淆、繁簡不互轉）。
- **Rationale**：
  - 英文大小寫差異是 Excel 常見現象（自動首字母大寫）；忽略大小寫減少摩擦。
  - 中文嚴格比對避免「教師」與「老師」被誤判（兩者語意不同）。
- **Alternatives considered**：
  - **全部嚴格比對**：摩擦過高。
  - **全部模糊比對（含繁簡轉換）**：失控；可能把「年級」（grade）對到「成績」。

---

## R-006 型別轉換規則

- **Decision**：
  - `str`：直接取字串、`.strip()`。空字串視為合法 `""`（不要拒絕）。
  - `int`：嘗試 `int(s.strip())`；失敗 → `RosterTypeError`，訊息含「列號、欄位、值、預期型別」。
  - `list_str`：以 `;`（分號）為分隔符；空字串 → `[]`；每段 `.strip()`；
    結果中過濾掉全空白項。
- **Rationale**：學校行政實務上會大量遇到「八年」（中文數字）型錯誤；明確錯誤比靜默轉 0 更安全。
- **Alternatives considered**：
  - **接受中文數字「八年」**：引入中文數字解析器（YAGNI、簡潔優先）。
  - **list_str 用逗號分隔**：與 CSV 自身的分隔符衝突。

---

## R-007 audit schema v1.1 → v1.2

- **Decision**：升級為 v1.2，**新增可選欄位** `import_metadata`：
  ```json
  {
    "source_type": "csv" | "xlsx" | "yaml",
    "encoding": "utf-8" | "utf-8-sig" | "cp950" | null,
    "sheet_name": "<name>" | null,
    "row_count": <int>,
    "file_basename": "<basename>"
  }
  ```
  YAML 路徑時 `import_metadata` 為 **`null`**（沿用「audit schema 演進新增可選欄位 + null」教訓）。
- **Rationale**：
  - **不**包含完整檔案路徑（含使用者目錄，破壞跨機器可重現）。
  - `file_basename` 提供「資料來自哪個檔案」的線索而不洩露絕對路徑。
  - 欄位皆為「該路徑之資料來源 metadata」，不影響核心媒合邏輯。
- **Alternatives considered**：
  - **記檔案 hash**：精準但對「先 Excel 編輯後另存為 CSV」場景反而誤導。
  - **省略 import_metadata、靜默升 v1.2**：違反 schema 嚴格性。

---

## R-008 三路徑等價的「等價」定義

- **Decision**：CSV/Excel/YAML 三條路徑的稽核紀錄在以下 **5 段完全相同**：
  `qualified_set` / `assignment` / `filter_trace` / `allocation_trace` / `template_snapshot`。
  允許差異的段：`import_metadata`、`roster_snapshot` 中內嵌的細微差異（若有）、`generated_at`（永遠為 null，不會差）。
- **Rationale**：核心媒合邏輯不應依賴「資料從哪裡來」；可重現性的保證在「相同結構化資料」層級。
- **Alternatives considered**：
  - **要求所有欄位完全相同**：技術上很難保證（roster_snapshot 中 list 的順序可能受編碼影響）。

---

## R-009 模組組織：單一 `data_import.py`

- **Decision**：把 CSV 與 Excel 載入器放在同一個 `src/matcher/data_import.py`；不切 `importers/csv.py` + `importers/xlsx.py` 子套件。
- **Rationale**：
  - 兩個載入器各 < 100 行、共用大量輔助函式（編碼偵測、型別轉換、alias 對齊）。
  - 切子套件是過早抽象（簡潔優先；至少有第三個格式才考慮）。
- **Alternatives considered**：
  - **importers/ 子套件**：未來真的支援 ODS / Google Sheets 時再切。

---

## R-010 既有黃金檔的處理

- **Decision**：所有既有黃金檔（baseline、teacher-class-template、study-group-template）一次性重生成，因為：
  1. audit schema 升 v1.2 → 多 `import_metadata: null` 欄位
  2. 兩個內建模板新增 aliases → template_snapshot 內容變
- **Rationale**：邏輯不變、僅資料/格式擴充，黃金檔重生是預期動作，PR diff 仍可審視。
- **Alternatives considered**：
  - **保留舊黃金檔、條件性輸出**：違反 schema 嚴格性，前次 R-009 已駁回此做法。

---

## R-011 openpyxl 新依賴

- **Decision**：加入 `openpyxl >= 3.1` 到 `pyproject.toml` 的 `dependencies`。
- **Rationale**：
  - 純 Python、PyPI 安裝相容、跨平台。
  - `>= 3.1` 涵蓋 Python 3.11+ 兼容版本。
- **Alternatives considered**：
  - **延後到本階段最後決定**：spec 已確認此方向。

---

## 已解決的 NEEDS CLARIFICATION 列表

本 plan 中無 NEEDS CLARIFICATION 標記；spec.md Assumptions 中標為「由 plan 決定」的項目（編碼偵測順序與失敗判定、normalize 規則、import_metadata 結構、模組組織）皆於 R-001 ~ R-009 解決。

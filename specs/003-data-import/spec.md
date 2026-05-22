# Feature Specification: 資料匯入（CSV / Excel）

**Feature Branch**: `003-data-import`
**Created**: 2026-05-22
**Status**: Draft
**Input**: User description: "CSV / Excel 名單匯入：依模板宣告的屬性 schema（含中文 aliases）自動對齊欄位、轉型別、展開 list_str 分隔字串。CSV 採啟發式 3 輪編碼偵測（UTF-8 → UTF-8-SIG → CP950）；Excel 採 openpyxl。新增 --roster-csv / --roster-xlsx 與既有 --roster (YAML) 三組互斥。沿用三條教訓：黃金檔比對驗證 CSV/YAML 同資料出相同稽核、preferences 欄位匯入後在 M0 仍拒絕、若需在稽核加 import_metadata 採新增可選欄位模式。"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — 用 CSV 名單跑通基準場景（Priority: P1）🎯 MVP

學校行政把名單維護在 CSV 檔（從學校系統匯出常見格式），表頭可用中文或英文（依模板宣告的 `aliases`）。執行 `matcher run --template teacher-class --roster-csv <path> --seed N`，系統自動偵測編碼、對齊欄位、轉型別，產出與「同樣資料以 YAML 載入」**完全相同**的稽核紀錄（除了 import metadata 區塊）。

**Why this priority**：CSV 是學校行政的「主要工作格式」——把名單從 Excel 另存為 CSV 是最便利的入口；沒有 CSV 路徑跑通，模板系統的「具體入口」承諾無法兌現。

**Independent Test**：準備一份 CSV（UTF-8 BOM、中文表頭）與一份對應的 YAML 名單，分別跑 `matcher run` 相同 seed，比對 `audit.qualified_set` 與 `audit.assignment` 兩段是否完全一致。

**Acceptance Scenarios**：

1. **Given** UTF-8 編碼、中文表頭（「姓名、專業科目、年資」）的 CSV 名單與 teacher-class 模板（模板宣告 `aliases: ["姓名"]` 等），**When** 執行 `matcher run --template teacher-class --roster-csv <path> --seed 123456`，**Then** 系統正確匯入、跑出與 YAML 版本同 seed 結果一致的稽核紀錄。
2. **Given** UTF-8 BOM 編碼的 CSV（Excel 另存常見格式）與 teacher-class 模板，**When** 執行匯入，**Then** 系統正確處理 BOM 並完成匯入。
3. **Given** CP950（Big5）編碼的 CSV 與 teacher-class 模板，**When** 執行匯入，**Then** 系統在 UTF-8 失敗後自動退到 CP950 並完成匯入。
4. **Given** CSV 表頭含模板未宣告的欄位（例如多餘的「備註」欄），**When** 執行匯入，**Then** 系統忽略未宣告欄位並完成匯入（不報錯——未宣告即不使用）。
5. **Given** CSV 缺少模板必填欄位（例如缺「speciality」），**When** 執行匯入，**Then** 系統回應 `RosterColumnMismatch` 明確錯誤，列出缺漏與所有有效 aliases。

---

### User Story 2 — 用 Excel 名單跑通研習分組場景（Priority: P2）

學校行政維護 Excel（.xlsx）名單，含中文表頭與 list_str 型別欄位（如 preferences 填「G1; G2; G3」分號分隔）。執行 `matcher run --template study-group --roster-xlsx <path> --seed N`，系統正確讀取單一工作表、轉型別、展開分號分隔字串為 list_str。

**Why this priority**：Excel 是學校最常見的編輯工具，無 CSV 編碼問題；對 list_str 欄位的展開能力是 preferences 等多選場景的基礎。

**Independent Test**：準備一份 .xlsx（單一工作表、中文表頭、含 list_str 欄位用分號分隔），跑 study-group + 空 preferences；驗證匯入後的 audit 與對應 YAML 同資料路徑等價。

**Acceptance Scenarios**：

1. **Given** 一份 .xlsx（單一工作表「Sheet1」、中文表頭、preferences 欄填空字串）與 study-group 模板，**When** 執行 `matcher run --template study-group --roster-xlsx <path> --seed 2026`，**Then** 系統正確匯入並跑通。
2. **Given** 一份 .xlsx，preferences 欄填「G1; G2; G3」（分號分隔），**When** 執行匯入（M0 機制），**Then** 系統將分隔字串展開為 list_str → 偵測到非空 preferences → 拒絕（exit 17，沿用既有路徑）。
3. **Given** 一份 .xlsx 含多張工作表，**When** 執行 `matcher run --roster-xlsx <path>` 未指定 `--sheet`，**Then** 系統回應 `RosterSheetAmbiguous` 並列出可用工作表名稱。
4. **Given** 同上 .xlsx，**When** 加上 `--sheet "報名表"`，**Then** 系統正確選用該工作表。

---

### User Story 3 — 匯入錯誤的明確錯誤回應（Priority: P3）

匯入過程的所有錯誤情境（編碼失敗、欄位缺失、型別轉換失敗、工作表歧義）皆產生明確繁中錯誤訊息與專屬 exit code，**不靜默用預設值**。沿用「三段式錯誤訊息」（錯誤 / 細節 / 建議）。

**Why this priority**：學校行政沒有時間調 debug；錯誤訊息要能直接指引動作。

**Independent Test**：構造 4 種異常 CSV/Excel 輸入，執行後驗證 exit code 與訊息關鍵字。

**Acceptance Scenarios**：

1. **Given** 一份不在 UTF-8 / UTF-8-SIG / CP950 三種編碼內的 CSV（例如 UTF-16），**When** 執行匯入，**Then** exit `RosterDecodeError` 對應 code，訊息列出已嘗試的編碼。
2. **Given** CSV 的「年資」欄寫了「八年」而非整數，**When** 執行匯入（模板宣告 `seniority: int`），**Then** exit `RosterTypeError` 對應 code，訊息指出哪列、哪欄、預期型別、實際值。
3. **Given** CSV 缺必填欄位，**When** 執行匯入，**Then** exit `RosterColumnMismatch` 對應 code，訊息列出缺漏欄位的 key 與所有可接受 aliases。
4. **Given** .xlsx 含 ≥ 2 個工作表且未指定 `--sheet`，**When** 執行匯入，**Then** exit `RosterSheetAmbiguous` 對應 code。

---

### Edge Cases

- **空檔案**：CSV 只有表頭、沒有資料列 → `EmptyRoster`（沿用階段 1 錯誤）。
- **表頭重複**：CSV 表頭中同一 key 出現兩次 → `RosterColumnMismatch` 並指出重複欄位。
- **list_str 欄位的別名**：模板宣告 `preferences` 型別為 `list_str`，aliases 含「志願組別」；CSV 表頭用「志願組別」、值用分號分隔 → 系統正確處理。
- **空白與大小寫**：CSV 表頭兩側空白應自動裁切（normalize）；別名比對**不**區分大小寫（針對英文 alias，例如 `name` vs `Name`），但完全保留中文比對的字元正確性。
- **混合 BOM**：CSV 有 BOM 但宣稱 UTF-8——應視同 UTF-8-SIG 路徑成功。
- **既有的 `--roster` 介面**：未指定 `--roster-csv` / `--roster-xlsx` 時，必須維持階段 1/2a 行為（向後相容）。

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**：CLI MUST 在 `matcher run` 命令中新增 `--roster-csv <path>` 與 `--roster-xlsx <path>` 參數，分別用於 CSV 與 Excel 名單匯入。
- **FR-002**：三組名單來源參數 MUST 互斥：`--roster <yaml>` / `--roster-csv <csv>` / `--roster-xlsx <xlsx>`；同時提供 → 明確拒絕（沿用階段 2a 的「請擇一」模式）。
- **FR-003**：CSV 匯入 MUST 採啟發式 3 輪編碼偵測：UTF-8 → UTF-8-SIG → CP950；三輪皆失敗 → `RosterDecodeError`。
- **FR-004**：Excel 匯入 MUST 支援 `.xlsx` 格式；不支援 `.xls`（舊版二進位格式）。
- **FR-005**：Excel 含多張工作表時 MUST 由 `--sheet <name>` 指定；未指定且 ≥ 2 工作表 → `RosterSheetAmbiguous`。
- **FR-006**：匯入時 MUST 依模板宣告的 `attributes` schema 對齊表頭：先比對 `key`，再比對 `aliases`（依宣告順序），匹配後忽略大小寫差異與兩側空白。
- **FR-007**：模板的 `AttributeDecl` MUST 新增選填欄位 `aliases: list[str]`，列出可接受的中文／英文別名。
- **FR-008**：型別轉換 MUST 對應模板宣告：`str` 直接讀字串；`int` 解析為整數（失敗 → `RosterTypeError`）；`list_str` 採分號 `;` 分隔字串展開為 list[str]（空字串 → 空 list）。
- **FR-009**：CSV 表頭含模板**未宣告**的欄位 → MUST 忽略並繼續匯入（不報錯）。
- **FR-010**：CSV 表頭**缺漏必填欄位** → MUST 拒絕並列出缺漏的 key 與所有可接受 aliases。
- **FR-011**：CSV 表頭**重複出現同一 key**（或同一 alias） → MUST 拒絕，指出重複位置。
- **FR-012**：匯入後的 preferences 欄位（list_str）若任一筆非空 → MUST 走階段 1 的 `PreferencesNotSupported` 拒絕路徑（M0 不接受志願）。
- **FR-013**：匯入過程 MUST 在以下 4 種情境輸出明確錯誤，每種對應**獨立的退出碼**：
  - `RosterDecodeError`（編碼偵測失敗）
  - `RosterColumnMismatch`（缺欄位／多重欄位）
  - `RosterTypeError`（型別轉換失敗）
  - `RosterSheetAmbiguous`（Excel 多工作表未指定）
- **FR-014**：稽核紀錄 MUST 新增**選填**欄位 `import_metadata`，當經 CSV/Excel 匯入時包含：`source_type`（csv/xlsx/yaml）、`encoding`（CSV 偵測到的編碼）、`sheet_name`（Excel）、`row_count`；YAML 路徑時為 `null`（沿用「audit schema 演進採新增可選欄位 + null」教訓）。
- **FR-015**：給定**等價內容**的 CSV、Excel 與 YAML 名單 + 同模板 + 同 seed，產出的稽核紀錄中 `qualified_set`、`assignment`、`filter_trace`、`allocation_trace`、`template_snapshot` **完全相同**（差異僅限 `import_metadata` 與 `roster_snapshot` 中的內嵌資料來源細節）。
- **FR-016**：階段 2a 的兩個內建模板（teacher-class、study-group）MUST 補上常用中文 aliases（如 name → 「姓名」、speciality → 「專業科目」、grade → 「年級」等）。
- **FR-017**：所有錯誤訊息、CLI 輸出 MUST 為繁體中文；錯誤訊息 MUST 為三段式（錯誤 / 細節 / 建議）。
- **FR-018**：CSV／Excel 匯入時 MUST 為每位角色的 `preferences` 欄位（若模板宣告為 list_str）做分號分隔展開；空字串視為空 list。
- **FR-019**：階段 1/2a 既有的 `matcher run --roster <yaml>` 行為 MUST 維持不變；既有自動化測試 100% 繼續通過（含階段 1+2a 的 82 個）。

### Key Entities

- **CSV 名單檔**：UTF-8 / UTF-8-SIG / CP950 編碼的純文字檔，首列為表頭（含 key 或 alias），其餘列為角色資料；對象側資料 **不** 透過 CSV 匯入（仍以 YAML 或模板宣告為主）。
- **Excel 名單檔（.xlsx）**：單一工作表為主；多工作表需顯式指定。
- **AttributeDecl.aliases（新欄位）**：每個屬性可宣告的別名列表，用於 CSV/Excel 表頭比對。
- **匯入後對齊結果**：每筆 CSV/Excel 列被轉成一個 Role 物件（含 attributes 與 preferences），與 YAML 載入結果結構完全相同。
- **import_metadata（稽核紀錄新欄位）**：記錄資料來源類型、編碼、工作表名、行數；YAML 路徑時為 null。
- **匯入錯誤類別**：4 個明確類別（DecodeError / ColumnMismatch / TypeError / SheetAmbiguous）。

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**：相同資料以 CSV、Excel、YAML 三種方式匯入跑同 seed，產出的稽核紀錄在 `qualified_set`、`assignment`、`filter_trace`、`allocation_trace`、`template_snapshot` 五段上 100% 相同。
- **SC-002**：UTF-8、UTF-8-SIG、CP950 三種 CSV 編碼皆能成功匯入；非此三者編碼 100% 觸發 `RosterDecodeError`。
- **SC-003**：四種匯入錯誤情境（編碼失敗、欄位缺失、型別失敗、工作表歧義）100% 產生明確繁中錯誤訊息與專屬 exit code；0% 靜默通過。
- **SC-004**：CSV 中文表頭（如「姓名」「專業科目」「年資」）可透過模板 `aliases` 自動對齊到 `name` / `speciality` / `seniority` 等英文 key。
- **SC-005**：Excel 多工作表場景 100% 要求 `--sheet` 顯式指定；單一工作表場景無需指定。
- **SC-006**：list_str 欄位（分號分隔）100% 正確展開為 list；空字串展開為空 list。
- **SC-007**：階段 1/2a 既有 82 個自動化測試在本階段後**100% 繼續通過**（向後相容）。
- **SC-008**：學校行政能直接把 Excel 另存為 CSV、用模板的中文 aliases 跑通基準場景，無需修改 CSV 內容（端對端可用性驗證）。
- **SC-009**：自動化測試覆蓋——三種編碼、四種錯誤情境、CSV/Excel/YAML 三種等價路徑（黃金檔比對）、向後相容、多工作表處理。
- **SC-010**：稽核紀錄 `import_metadata` 欄位在 CSV/Excel 路徑時包含正確的編碼、工作表名、行數；YAML 路徑時為 `null`。

## Assumptions

- **CSV 規格**：採 RFC 4180 標準（逗號分隔、雙引號跳脫）；分隔符固定為 `,`；list_str 內分隔符固定為 `;`。
- **Excel 規格**：只支援 `.xlsx`（OpenXML 格式）；不支援 `.xls`（舊二進位）、`.xlsm`（含巨集）。
- **編碼偵測順序固定**：UTF-8 → UTF-8-SIG → CP950，**不引入第三方偵測套件**（如 chardet），保持「簡潔優先」。
- **大小寫與空白**：別名比對對英文 alias 不區分大小寫；表頭兩側空白自動裁切；中文 alias 嚴格相等比對（保留字元正確性）。
- **list_str 分隔符**：固定為分號 `;`；不接受其他分隔符（避免與 CSV 自身的逗號衝突）。文件與錯誤訊息明示。
- **對象（targets）端資料來源**：仍以 YAML 或模板宣告為主；CSV/Excel 匯入**僅針對 roles 端**（典型場景：teacher-class 中老師資料常匯入、班級設定相對固定）。如需 targets 也匯入，留待未來。
- **import_metadata 欄位**：audit schema 升級為 v1.2（沿用 v1.0 → v1.1 的「新增可選欄位 + null」模式）。
- **新增依賴**：`openpyxl`（純 Python、無需 Excel 安裝）；CSV 與編碼處理皆用 stdlib。
- **不處理**：
  - CSV/Excel **匯出**（屬未來）。
  - Google Sheets、ODS、Numbers 等其他試算表格式。
  - 多檔案合併匯入（單次單檔）。
  - 互動式欄位對齊 UI（屬階段 3 Web UI 範疇）。
  - 模板自身為 CSV/Excel 格式（模板永遠是 YAML）。
  - 對象（targets）端的 CSV/Excel 匯入。

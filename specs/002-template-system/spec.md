# Feature Specification: 模板系統（Template System）

**Feature Branch**: `002-template-system`
**Created**: 2026-05-22
**Status**: Draft
**Input**: User description: "模板系統：定義可命名、可儲存、可載入、可分享的媒合情境模板格式——把屬性 schema、規則、UI 欄位宣告、稽核報告欄位宣告打包為單一檔案；建立 2 個內建模板（教師-班級配對、研習分組）。本階段只做格式與載入器，UI 渲染與報告渲染留給階段 3。沿用階段 1 的兩條教訓：黃金檔比對（模板快照寫入稽核紀錄）與介面預留拒絕分支（模板自始支援 preferences schema，但 M0 機制下拒絕非空 preferences）。"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — 使用內建模板執行媒合（Priority: P1）🎯 MVP

學校行政在 CLI 上選擇一個內建模板（例如「teacher-class」），提供一份對應的名單檔與 seed，即可執行媒合。模板已宣告該情境的屬性 schema 與規則，使用者不需要另外維護規則檔——模板就是「具體入口」。

**Why this priority**：這是模板系統存在的全部理由——讓非技術使用者不必撰寫規則檔即可上手。沒有這條路徑跑通，模板系統等於沒做。

**Independent Test**：在 CLI 上 `matcher run --template teacher-class --roster examples/teacher-class/roster.yaml --seed 123456`，跑通後驗證稽核紀錄含 `template_snapshot` 欄位，且最終配對與階段 1 的同 seed 結果完全一致（向後相容驗證）。

**Acceptance Scenarios**：

1. **Given** 一個內建模板 id「teacher-class」與一份相容的名單檔、一個 seed，**When** 執行 `matcher run --template teacher-class --roster <path> --seed <n>`，**Then** 系統載入模板內含的規則、執行媒合、產出稽核紀錄；稽核紀錄含 `template_snapshot` 欄位記錄完整模板內容。
2. **Given** 另一個內建模板 id「study-group」（研習分組）與一份相容的名單檔，**When** 執行 `matcher run --template study-group ...`，**Then** 系統正確套用該模板的屬性 schema 與規則。
3. **Given** 一個不存在的模板 id，**When** 執行 `matcher run --template no-such --roster ...`，**Then** 系統回應「找不到模板」明確錯誤，並列出所有內建模板 id 供使用者選擇。

---

### User Story 2 — 模板可瀏覽、匯出、匯入（Priority: P2）

學校行政能列出所有可用模板、檢視單一模板的完整內容、把任一模板匯出為單一 YAML 檔以便分享或備份；該檔可作為「外部模板」重新匯入，行為與內建模板一致。

**Why this priority**：分享與備份能力是「模板作為一級概念」的具體展現；學校之間能交換模板才能形成共識做法。

**Independent Test**：`matcher template list` → `matcher template show teacher-class` → `matcher template export teacher-class --output /tmp/tc.yaml` → 用該檔執行 `matcher run --template-file /tmp/tc.yaml ...`，驗證稽核紀錄與直接使用內建模板逐位元組相同。

**Acceptance Scenarios**：

1. **Given** 系統已內建 ≥ 2 個模板，**When** 執行 `matcher template list`，**Then** 系統列出全部模板的 id、名稱、一句話描述（繁中）。
2. **Given** 一個內建模板 id，**When** 執行 `matcher template show <id>`，**Then** 系統列出完整模板內容（含屬性 schema、規則、UI 欄位宣告、報告欄位宣告），所有可讀文字為繁中。
3. **Given** 一個內建模板 id 與輸出路徑，**When** 執行 `matcher template export <id> --output <path>`，**Then** 輸出的 YAML 檔可以被 `--template-file` 重新匯入。
4. **Given** 同一名單與 seed，**When** 一次使用內建模板 id、另一次使用該模板匯出的檔案，**Then** 兩次的稽核紀錄逐位元組相同。

---

### User Story 3 — 預留 preferences schema 並於 M0 拒絕（Priority: P3）

模板可在 schema 中宣告 `preferences` 欄位（例如「研習分組」讓人填 3 個志願）；本階段 M0 機制下，若匯入名單中帶有非空 preferences 值，系統明確拒絕並指引使用者：志願序機制將於階段 4 加入。

**Why this priority**：實踐 experience.md 的「介面預留 + 拒絕分支」教訓——模板格式與名單格式都自始支援 preferences，階段 4 啟用 M1/M2 時不必改格式。

**Independent Test**：使用研習分組模板的範例名單（含 preferences 欄位），在 M0 機制下執行，驗證 exit code 17 與明確錯誤訊息；移除 preferences 後跑通。

**Acceptance Scenarios**：

1. **Given** 「研習分組」模板的範例名單（含每位學生的 preferences 欄位）與 M0 機制，**When** 執行媒合，**Then** 系統回應 exit code 17，訊息含「此機制不接受志願輸入」「階段 4」字樣。
2. **Given** 同一名單但 preferences 欄位皆為空陣列，**When** 執行媒合，**Then** 系統正常以純抽籤完成（preferences 為空時等同未提供）。
3. **Given** 「研習分組」模板的 schema 內含 `preferences` 宣告，**When** 執行 `matcher template show study-group`，**Then** 輸出中明確列出該欄位為「未來機制（M1/M2）使用，本階段不啟用」。

---

### Edge Cases

- **未知 schema_version**：模板檔頂部 `schema_version` 為未支援的值 → 明確錯誤，列出當前支援版本。
- **模板缺必要欄位**：模板缺 `id`、`name`、`description`、`attributes`、`rules` 之一 → 明確錯誤指出缺哪個欄位。
- **id 衝突**：自訂模板與內建模板同 id → 自訂模板優先（以 `--template-file` 載入時）或明確錯誤（若批次預載）。
- **屬性 schema 與名單不一致**：模板宣告「老師需要 speciality 屬性」，但名單缺此屬性 → 沿用階段 1 的 `UnknownAttribute` 錯誤。
- **既有 `--rules + --roster` 介面**：未指定 `--template` / `--template-file` 時，必須維持階段 1 行為（向後相容）。

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**：模板檔格式 MUST 為人類可讀的結構化檔案（與規則檔相同的格式風格），頂層 MUST 含 `schema_version`、`id`、`name`、`description`。
- **FR-002**：系統 MUST 嚴格驗證 `schema_version`；未知版本立即拒絕載入（明確錯誤指出當前支援版本）。
- **FR-003**：模板 MUST 能宣告四層內容——`attributes`（角色與對象的屬性 schema）、`rules`（規則集，沿用階段 1 格式）、`ui_fields`（UI 表單欄位宣告，本階段不渲染但格式須穩定）、`report_fields`（稽核報告欄位宣告，本階段不渲染但格式須穩定）。
- **FR-004**：`attributes` 與 `rules` 為**必填**；`ui_fields` 與 `report_fields` 為**選填**（缺省時即為空）。
- **FR-005**：系統 MUST 提供 ≥ 2 個內建模板：「teacher-class」（教師-班級配對）與「study-group」（研習分組）。「研習分組」MUST 宣告 `preferences` schema 以供未來機制使用。
- **FR-006**：CLI MUST 提供 `matcher template list` 命令，列出所有內建模板的 id、名稱、一句話描述（繁中）。
- **FR-007**：CLI MUST 提供 `matcher template show <id>` 命令，列出指定模板的完整內容（繁中可讀）。
- **FR-008**：CLI MUST 在 `matcher run` 命令中接受 `--template <id>` 參數，行為與既有 `--rules + --roster` 等價但規則來自模板。
- **FR-009**：CLI MUST 提供 `matcher template export <id> --output <path>` 命令，將指定模板匯出為單一檔案。
- **FR-010**：CLI MUST 在 `matcher run` 命令中接受 `--template-file <path>` 參數，從外部檔案載入模板執行媒合。
- **FR-011**：模板 schema MUST 能宣告 `preferences` 欄位（key + type + 說明）；本階段 M0 機制下，若匯入名單帶有非空 preferences 值 → 拒絕（沿用階段 1 的 `PreferencesNotSupported`）。
- **FR-012**：稽核紀錄 MUST 新增 `template_snapshot` 欄位，包含完整模板內容（id、name、version、attributes、rules、ui_fields、report_fields、preferences schema）；該欄位確保「相同模板 + 相同名單 + 相同 seed」100% 可重現。
- **FR-013**：模板載入錯誤 MUST 拋出明確的繁中錯誤類別（至少：模板找不到、schema_version 未知、必填欄位缺失、id 衝突）。
- **FR-014**：既有的 `matcher run --rules <path> --roster <path>` 介面 MUST 維持向後相容；未指定 `--template` 或 `--template-file` 時行為與階段 1 完全一致。
- **FR-015**：所有錯誤訊息、CLI 輸出、模板內附自然語言說明 MUST 為繁體中文（依 constitution）。
- **FR-016**：`--template` 與 `--template-file` 與 `--rules + --roster` 三組參數 MUST 互斥；同時提供時系統明確拒絕並提示「請擇一」。

### Key Entities

- **模板（Template）**：可命名、可儲存、可分享的媒合情境定義；包含 id、名稱、描述、schema_version、屬性 schema、規則集、UI 欄位宣告、稽核報告欄位宣告、preferences schema（可選）。
- **內建模板登錄（Template Registry）**：系統內建模板的集合，可被列舉、查詢、匯出；本階段內建 ≥ 2 個模板。
- **屬性 schema（Attribute Schema）**：宣告角色與對象側必須具備的屬性名稱與型別（例如「老師必有 speciality: 字串」「班級必有 capacity: 整數」）。
- **UI 欄位宣告（UI Field Declaration）**：未來 Web UI 渲染表單時所需的欄位宣告（型別、label、placeholder、validation 等）；本階段格式須穩定，不渲染。
- **稽核報告欄位宣告（Report Field Declaration）**：未來稽核報告渲染時所需的欄位宣告；本階段格式須穩定，不渲染。
- **preferences schema**：模板宣告當事人志願欄位的結構（每人可填幾個志願、是否強制等）；本階段宣告但 M0 機制不執行。
- **模板快照（Template Snapshot）**：每次媒合執行時寫入稽核紀錄的完整模板內容（凍結版本）；確保稽核紀錄獨立於模板檔的後續變更。

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**：≥ 2 個內建模板（teacher-class、study-group）皆能以 `matcher template list` 列出與 `matcher template show <id>` 檢視完整內容。
- **SC-002**：兩個內建模板皆能配合對應範例名單以 `matcher run --template <id>` 跑通，並產出含 `template_snapshot` 的稽核紀錄。
- **SC-003**：任一模板匯出後重新匯入，給定相同（名單 + seed），兩次稽核紀錄逐位元組相同（沿用階段 1 黃金檔比對手法）。
- **SC-004**：稽核紀錄含 `template_snapshot`；給定相同（模板 + 名單 + seed）100% 可重現。
- **SC-005**：未知 `schema_version`、缺必要欄位、模板 id 不存在三種情境 100% 產生明確繁中錯誤，0% 靜默通過。
- **SC-006**：「研習分組」模板宣告了 preferences schema；在 M0 機制下匯入非空 preferences 100% 收到 exit code 17 與「等待階段 4」提示。
- **SC-007**：階段 1 既有的 `matcher run --rules <path> --roster <path>` 介面在本階段後**完全不變**——所有階段 1 既有自動化測試（48 個）100% 繼續通過。
- **SC-008**：`--template`、`--template-file`、`--rules + --roster` 三組參數同時提供時，100% 明確拒絕並提示。
- **SC-009**：自動化測試覆蓋上述路徑——模板載入、CLI 三個子命令（list / show / export）、`--template` 與 `--template-file` 整合測試、preferences 拒絕測試、向後相容測試（依 constitution TDD）。

## Assumptions

- **模板格式**：YAML（與階段 1 規則檔／名單檔風格一致；具體格式由 `/speckit.plan` 決定）。
- **內建模板位置**：存放於套件內（具體路徑由 `/speckit.plan` 決定）；範例名單則放於 repo 的 `examples/`。
- **UI 欄位與報告欄位的宣告格式**：本階段必須定義出**穩定**的格式（即使本階段不渲染），避免階段 3 改動模板格式破壞稽核可重現性；具體欄位類型參考常見表單元素（text、number、select、multiselect、textarea）；具體 schema 在 `/speckit.plan` 細化。
- **「研習分組」schema**：角色為「學生」（id、name、grade、preferences），對象為「分組」（id、name、topic、capacity）；規則例如「分組容量上限」「年級限制」。
- **CLI 子命令分組**：採用 Typer 子應用程式（`matcher template ...`）；保留向後相容（既有 `matcher run` 與 `matcher filter` 不變）。
- **模板 id 命名**：英文 kebab-case（如 `teacher-class`、`study-group`）；模板顯示名稱與描述為繁中。
- **不處理**：
  - 模板繼承 / 組合（單一模板自包含；複雜場景透過自訂模板表達，不引入繼承）。
  - 模板版本遷移（schema_version 不相容直接拒絕，不自動升級）。
  - 多語系（本階段只支援繁中文案）。
  - CSV/Excel 匯入名單（屬下一個 feature 003）。
  - Web UI 渲染（屬階段 3）。
  - 稽核報告 PDF 渲染（屬階段 3）。

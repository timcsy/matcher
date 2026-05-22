# Research: 模板系統技術選型

**Branch**: `002-template-system` | **Date**: 2026-05-22

本文件記錄階段 2 的設計決策。每項以「決策 / 理由 / 替代方案」三段式記錄。

---

## R-001 模板檔格式：YAML（與階段 1 一致）

- **Decision**：模板檔採 YAML，與既有 rules.yaml / roster.yaml 風格一致。
- **Rationale**：
  - 與既有規則檔風格一致，學校行政心智成本最低。
  - 註解支援良好，便於模板作者寫繁中說明。
  - 階段 1 已有 PyYAML 依賴；不引入新工具。
- **Alternatives considered**：
  - **JSON**：序列化嚴格，但不支援註解，模板的「自然語言說明」較難凸顯。
  - **TOML**：層級結構不適合表達 AST 樹狀規則。

---

## R-002 模板檔頂層結構

- **Decision**：頂層欄位固定為 `schema_version` / `id` / `name` / `description` / `attributes` / `rules` / `ui_fields` / `report_fields` / `preferences_schema`。
  - 必填：`schema_version`、`id`、`name`、`description`、`attributes`、`rules`
  - 選填：`ui_fields`、`report_fields`、`preferences_schema`
- **Rationale**：
  - 對應 spec.md FR-001/003/004；強制必填的最小集合。
  - `attributes` 與 `rules` 是規則執行的最小依賴；`ui_fields`/`report_fields` 在階段 3 才被消費；`preferences_schema` 在階段 4 才被消費。
- **Alternatives considered**：
  - **將 schema_version 嵌入 id**（例如 `teacher-class@1.0`）：破壞 id 純淨性、不利程式化判斷。
  - **將 attributes/rules 列為選填**：失去最小可執行保證，模板可能載入卻無法運作。

---

## R-003 內建模板存放位置

- **Decision**：以套件資源形式存於 `src/matcher/templates/builtin/*.yaml`，透過 `importlib.resources.files("matcher.templates.builtin")` 列舉與讀取。
- **Rationale**：
  - 隨套件一起安裝（pip install / uv pip install），不需額外設定路徑。
  - 對 wheel/zip 安裝相容，跨平台一致。
- **Alternatives considered**：
  - **硬編碼絕對路徑**：開發機可動，正式安裝後找不到檔案。
  - **環境變數 / 設定檔指定目錄**：本階段內建只有 2 個，外部模板用 `--template-file` 即足夠，不必引入「使用者目錄」概念。

---

## R-004 schema_version 策略

- **Decision**：本階段固定支援 `schema_version: "1.0"`；未來變更格式時透過增加版本字串。載入器嚴格拒絕未知版本（明確錯誤 + 列出當前支援版本清單）。
- **Rationale**：
  - 階段 2 教訓（experience.md「介面預留」）：寧可預留版本欄位避免未來向後相容地獄。
  - 嚴格拒絕勝過自動升級——後者會靜默改變稽核紀錄，破壞可重現性。
- **Alternatives considered**：
  - **自動升級**：簡便但會讓相同檔案在不同程式版本下產生不同稽核 → 直接違反原則 2。

---

## R-005 UI 欄位宣告格式

- **Decision**：採類似 JSON Schema 子集的扁平宣告，每筆含 `key` / `label` / `type` / `required` / `options?` / `placeholder?` / `help?`。
  - 支援的 `type`：`text` / `number` / `select` / `multiselect` / `textarea`。
- **Rationale**：
  - 涵蓋學校行政常見表單需求；不引入巢狀結構（學生輸入學號、選班級類型）。
  - 限制 type 為閉集合，避免階段 3 渲染器要支援無限類型。
- **Alternatives considered**：
  - **完整 JSON Schema**：表達力強但對非技術使用者過度複雜；本階段用不上。
  - **不定義 UI 格式，留給階段 3**：違反 spec FR-003「本階段不渲染但格式須穩定」，會迫使階段 3 改模板格式破壞稽核可重現性。

---

## R-006 報告欄位宣告格式

- **Decision**：採「欄位識別字 + label + 來源路徑」三元組，每筆含 `key` / `label` / `source`。
  - `source` 為點分式路徑，指向稽核紀錄中的欄位，例如 `assignment.{role_id}` 或 `roster_snapshot.roles[].name`。
- **Rationale**：
  - 階段 3 渲染器只需依此映射即可組稽核報告，不需動態程式邏輯。
  - 與「規則必須可解釋」（原則 1）一致：可閱讀的宣告，而非任意函式。
- **Alternatives considered**：
  - **嵌入式公式 / JavaScript expression**：表達力強但破壞可解釋性、引入安全風險。

---

## R-007 模板載入錯誤類別

- **Decision**：新增 4 個錯誤類別，繼承 `MatcherError`：
  - `TemplateNotFound`（exit 20）：模板 id 不存在
  - `UnknownSchemaVersion`（exit 21）：schema_version 不在支援清單
  - `TemplateMissingField`（exit 22）：必填欄位缺失
  - `TemplateConflict`（exit 23）：多個來源出現同 id（內建 vs 外部）
- **Rationale**：
  - 與階段 1 風格一致（明確類別 + 不同退出碼 + 三段式繁中訊息）。
  - exit code 20–23 連續、避免與階段 1 的 10–17 衝突。
- **Alternatives considered**：
  - **重用 `UnknownAttribute` 等既有錯誤**：模板層級的錯誤本質不同（找不到 id ≠ 屬性引用錯誤），混用會增加除錯成本。

---

## R-008 CLI 結構：Typer 子應用

- **Decision**：將 `matcher template` 作為 Typer 子應用群組，內含 `list` / `show` / `export` 三個子命令。`matcher run` 既有命令新增 `--template` / `--template-file` 互斥於 `--rules + --roster`。
- **Rationale**：
  - Typer 子應用語法乾淨：`app.add_typer(template_app, name="template")`。
  - 與 git/kubectl 等工具的 `<noun> <verb>` 語法一致，學校行政熟悉。
- **Alternatives considered**：
  - **平級命令** `matcher template-list / template-show`：命名繁瑣、無法分群顯示 `--help`。
  - **重用 `matcher run --list-templates`**：混雜 run 子命令的語意，違反「單一職責」。

---

## R-009 audit schema 演進策略

- **Decision**：audit-schema 升級為 1.1，**新增** `template_snapshot` 欄位（型別：物件 | null）；其他欄位不變。
  - 階段 1 黃金檔 `teacher-class-baseline.audit.json` 需要重新生成以包含 `template_snapshot: null`（無模板路徑）。
- **Rationale**：
  - 「新增可選欄位」是 audit schema 最低衝擊的演進方式。
  - `null` 明確表示「本次未使用模板」，比省略欄位更可機讀。
- **Alternatives considered**：
  - **保持 schema 1.0，只在使用模板時加欄位**：違反 schema 嚴格性；同一檔案結構在不同情境下不同。
  - **新增 schema_version 2.0**：本階段未動其他欄位，重大版號過頭。

---

## R-010 向後相容測試策略

- **Decision**：階段 1 既有 48 個測試**全數保留**；只更新一個黃金檔（`teacher-class-baseline.audit.json`）以反映新增的 `template_snapshot: null` 欄位。此更新會在 plan 階段的研究階段紀錄並於 implement 階段一次完成。
- **Rationale**：
  - 黃金檔更新是必要的、由 schema 演進造成、非邏輯變更——可被 PR diff 清楚審視。
  - SC-007「48 測試 100% 通過」的真正承諾是「**邏輯**完全不變」，而非「**輸出 bytes** 完全不變」。schema 升級造成的單一欄位差異不算破壞。
- **Alternatives considered**：
  - **保持階段 1 黃金檔 bytes 不變、條件性輸出 template_snapshot**：違反 R-009 的 schema 嚴格性。

---

## R-011 模板 id 與顯示名稱

- **Decision**：模板 `id` 為英文 kebab-case；`name` 與 `description` 為繁中。內建模板 id 固定為 `teacher-class`、`study-group`。
- **Rationale**：
  - id 為程式介面（CLI 參數、檔名、log），英文穩定；name/description 為人類介面，用繁中。
  - 與 git branch 短名稱（`002-template-system`）風格一致。
- **Alternatives considered**：
  - **全繁中 id**：在 CLI 上需處理 shell 跳脫、IM 引號等，徒增複雜度。

---

## R-012 模板快照（template_snapshot）寫入時點

- **Decision**：稽核紀錄中的 `template_snapshot` 包含**載入後的完整 Template 物件序列化**（含 id、schema_version、name、description、attributes、rules、ui_fields、report_fields、preferences_schema），於 `build_audit_record` 寫入。
- **Rationale**：
  - 「模板檔可能在事後被改動」——快照凍結了當下版本，確保稽核紀錄獨立。
  - 序列化形式採 `sort_keys=True`、`ensure_ascii=False`，沿用階段 1 的可重現性保證。
- **Alternatives considered**：
  - **只記 template id + schema_version**：模板被改動後重播無從還原；違反 SC-004。

---

## 已解決的 NEEDS CLARIFICATION 列表

本 plan Technical Context 中無 NEEDS CLARIFICATION 標記；spec.md Assumptions 中標為「由 plan 決定」的項目（YAML 格式、內建模板位置、UI/report 欄位宣告、CLI 子命令結構、kebab-case 命名）皆於 R-001 ~ R-011 解決。

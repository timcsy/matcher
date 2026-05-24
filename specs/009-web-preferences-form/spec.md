# Feature Specification: Web UI 動態填志願表單

**Feature Branch**: `009-web-preferences-form`
**Created**: 2026-05-24
**Status**: Draft
**Input**: User description: "Web UI 動態填志願表單：上傳名單後若模板含 preferences_schema 且選 M1/M2，自動進入填志願步驟（單張長表格、每位角色 max_choices 個下拉、候選來自模板 default_targets）；表單可跳過（escape hatch）。填寫後跑 pipeline 與『同樣志願以 CSV 上傳』audit bytewise 相等。核心 0 改動；技術詞零容忍沿用教訓 6。"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — 行政在 UI 上替學生填志願（Priority: P1）🎯 MVP

學校行政在 `/match/new` 選 study-group 模板、上傳「無志願欄」CSV/Excel 名單、選擇 M1 或 M2 機制、點執行 → 系統偵測到模板含 `preferences_schema` 且使用者上傳的名單**所有角色 preferences 皆為空**，因此跳到「填志願」步驟。畫面顯示一張長表格：每列一位學生（id + 姓名），每列右側 `max_choices` 個志願下拉，選項為模板 `default_targets`（如「程式組」「自然組」「人文組」）。行政填完按「確認執行」→ 系統把表單志願組裝為 roster preferences 跑既有 pipeline、跳到結果頁。結果 audit 與「同樣志願以 CSV 上傳」跑出的 audit 五段逐位元組相同。

**Why this priority**：vision 階段 4d 唯一交付項——讓「30 分鐘行政實測」徹底擺脫 CSV preferences 欄的教學負擔。完成後 M1/M2 才算對非工程師「真正可用」。

**Independent Test**：上傳 study-group 內含 9 學生但無志願欄的 CSV + 選 M1 → 自動跳填志願頁 → 填完 → 結果頁正常出現「處理順序」「志願排名」段。

**Acceptance Scenarios**：

1. **Given** 模板 `study-group` 含 `preferences_schema(max_choices=3)` + 名單 9 學生全空 preferences + mechanism=M1，**When** 提交 `/match/new`，**Then** 系統跳到「填志願」中介頁面、表格顯示 9 列、每列 3 個下拉（選項為「程式組」「自然組」「人文組」+ 空白）。
2. **Given** 填志願頁、行政為每位學生選滿 3 志願（不重複），**When** 點「確認執行」，**Then** 系統執行媒合、跳到結果頁、`audit.mechanism == "M1"` 且 `processing_order` 非 null。
3. **Given** 填志願頁完成後的 record，**When** 比對與 CLI（`--roster-csv` 含同樣 preferences 欄）跑出的 audit，**Then** qualified_set / assignment / filter_trace / allocation_trace / template_snapshot 五段逐位元組相同。
4. **Given** 填志願頁，**When** 同列重複選同一對象，**Then** 表單拒絕送出、UI 顯示「同列不可重複選同對象」。

---

### User Story 2 — 跳過填志願表單（escape hatch）（Priority: P2）

某行政「我已在 CSV 中填好 preferences 欄、不想再填一次」。系統需提供清楚的退路。

**Why this priority**：避免逼迫已熟悉 CSV preferences 欄的使用者多走一步；同時保留 008 的既有路徑完全可用。

**Independent Test**：上傳含 preferences 欄的 study-group CSV（如既有 roster-m1.csv）+ 選 M1 → **不**跳填志願頁、直接跑、結果與 008 相同。

**Acceptance Scenarios**：

1. **Given** 上傳的 CSV 中**至少一位**角色 preferences 非空 + mechanism=M1，**When** 提交，**Then** 系統**不**跳填志願頁、直接執行（沿用 008 路徑）。
2. **Given** 上傳全空 prefs + mechanism=M1 + 跳到填志願頁，**When** 使用者點「跳過此步驟」按鈕，**Then** 系統以「全空 preferences」執行 → 沿用既有 `MechanismRequiresPreferences` 拒絕路徑（M1 / M2）+ 顯示失敗結果頁。
3. **Given** 上傳全空 prefs + mechanism=M0，**When** 提交，**Then** **不**跳填志願頁、直接 M0 跑（M0 不需 preferences）。

---

### User Story 3 — 填志願 UI 的可解釋性與透明度（Priority: P3）

填志願時，行政（或未來代填的學生）需要看懂候選對象。冷冰冰的「G1 / G2 / G3」代碼會讓人猶豫。每個下拉選項應顯示對象的中文顯示名（如「程式組」），且可看到候選對象的關鍵屬性。

**Why this priority**：服務原則 1「屬性與規則必須可解釋」+ 原則 5「對使用者透明」。降低填寫錯誤率與「我選錯了」的爭議。

**Independent Test**：填志願頁上方顯示「候選對象清單」段，列出每個對象的 id + 名稱 + 關鍵屬性；下拉選項文字含中文名（如「程式組（G1）」），不僅是 id。

**Acceptance Scenarios**：

1. **Given** 填志願頁，**When** 開啟頁面，**Then** 頂部「候選對象」段列出 3 組（程式組、自然組、人文組）+ 各組的 capacity（如「容量 3 人」），不暴露 `default_targets` / `attributes` 等英文 token。
2. **Given** 填志願頁的任一下拉，**When** 展開選項，**Then** 選項文字為「程式組」「自然組」「人文組」+ 空白選項「（未選）」；不僅是「G1」「G2」「G3」。
3. **Given** 填志願頁 HTML，**When** 跑 FORBIDDEN_TECHNICAL_TOKENS 正則，**Then** 0 匹配（沿用 008 清單 + 新增 `default_targets` / `max_choices`）。

---

### Edge Cases

- **模板無 `preferences_schema`**（如 teacher-class）+ 選 M1/M2：規格設定為直接 reject 在 pipeline（既有行為，不引入新路徑）；填志願頁完全不會被觸發
- **模板無 `default_targets`**：填志願頁應顯示明確提示「此模板未宣告 default_targets，無法在 UI 上填志願——請在 CSV 中填 preferences 欄」+ 提供「回到上一步」按鈕
- **`max_choices == 1`**：表格每列只 1 個下拉，仍正常運作
- **角色數很多**（如 50 人）：單張長表格須能完整 render；POST body 在 FastAPI 預設 limit 內（純文字 50×3 ≈ 數 KB）
- **重複選同對象**：HTML `<select>` 不阻擋；須在 POST 後端驗證、回相同頁面 + 錯誤提示
- **使用者填了一半離開**：草稿不儲存（明確排除）；UI 顯示「離開不會儲存」提示
- **mechanism=M0 + 模板含 schema**：仍不跳填志願頁；M0 不需 preferences

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**：`/match/run` 偵測到「上傳名單所有角色 preferences 皆為空」**且**「模板含 `preferences_schema`」**且** mechanism ∈ {M1, M2} → 跳到填志願中介頁面（不直接執行）。
- **FR-002**：填志願頁顯示一張長表格——每列一位角色（含 id + 顯示名）、每列 `max_choices` 個志願下拉（標籤「您的第 1 志願」「您的第 2 志願」…）。
- **FR-003**：每個志願下拉選項來自模板 `default_targets`——選項文字為對象的顯示名（如「程式組」），不僅是 id。第一選項為「（未選）」（空白值）。
- **FR-004**：填志願頁頂部 MUST 顯示「候選對象」段，列出每組對象的顯示名 + 容量（如「程式組（容量 3 人）」）。
- **FR-005**：填志願頁 MUST 提供「跳過此步驟，以全空志願執行」按鈕——點擊後沿用既有 `MechanismRequiresPreferences` 拒絕路徑（M1/M2 必然失敗、回失敗結果頁）。
- **FR-006**：填志願頁 POST 端點 MUST 驗證：(a) 同列志願不可重複（同一對象不可填兩次）、(b) 至少一位角色有 ≥ 1 志願（否則沿用 FR-005 路徑）；驗證失敗回填志願頁 + 友善繁中錯誤訊息。
- **FR-007**：填志願頁 POST 驗證通過後，系統將表單志願組裝為 `Role.preferences` 列表並走既有 pipeline；輸出的 audit MUST 與「同樣志願以 CSV 上傳跑出的 audit」逐位元組相同（qualified_set / assignment / filter_trace / allocation_trace / template_snapshot 五段）。
- **FR-008**：「填志願頁」MUST 不顯示於以下情境：(a) 模板無 `preferences_schema`、(b) 上傳名單中**有任何角色** preferences 非空（使用者已自帶志願）、(c) mechanism == "M0"。
- **FR-009**：模板含 `preferences_schema` 但**無** `default_targets`、且使用者上傳的名單也無 targets 旁檔資料 → 填志願頁顯示明確繁中錯誤「此模板未宣告 default_targets，無法在 UI 上填志願——請在 CSV preferences 欄填寫」+ 「回到上一步」按鈕。
- **FR-010**：所有新增 UI 文案 MUST 通過 FORBIDDEN_TECHNICAL_TOKENS 正則驗證（教訓 6）——不可暴露 `default_targets` / `preferences_schema` / `max_choices` / `preference_rank` / `preferred_order` 等英文 token。
- **FR-011**：本 feature MUST 不動核心模組（`src/matcher/{rules,filter,allocator,pipeline,audit,errors,data_import,template_loader,rng,roster}`）——所有變更限於 `src/matcher/web/`。
- **FR-012**：填志願頁的草稿 MUST NOT 自動儲存；頁面 MUST 顯示「離開不會儲存」提示。
- **FR-013**：階段 1+2a+2b+3a+3b+4a+4b+4c 既有 234 個自動化測試 MUST 100% 繼續通過。
- **FR-014**：所有錯誤訊息、UI 文案 MUST 為繁中（沿用 constitution）。

### Key Entities

- **填志願頁中介狀態**：使用者第一次 POST `/match/run` 時偵測到應跳填志願，將「已驗證的 template_id、mechanism、seed、roster 暫存資料（含原始 bytes 或解析後 roles）」傳至填志願頁。實作層面可採取 (a) 把資料嵌入頁面 hidden input、(b) 暫存於 session、(c) 第二次 POST 時要求重傳檔——本 spec 不指定，留 plan 階段決定。
- **志願下拉選項清單**：模板 `default_targets` 的 (id, display_name) 配對，加一個「（未選）」空白選項。
- **表單驗證錯誤**：含「同列重複」「對象 id 不在 default_targets 中」兩種；皆回填志願頁 + 紅字提示。

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**：上傳 study-group + 9 學生全空 prefs CSV + 選 M1 → 自動跳填志願頁；填完後 audit 與「同樣志願以 CSV 上傳」跑出的 audit 五段 100% bytewise 相同。
- **SC-002**：上傳含 prefs 欄的 CSV（如 roster-m1.csv）+ 選 M1 → 不跳填志願頁、直接執行（既有 008 行為向後相容 100%）。
- **SC-003**：填志願頁 HTML 通過 FORBIDDEN_TECHNICAL_TOKENS 正則 100% 驗證；新增 token：`default_targets`、`preferences_schema`、`max_choices`。
- **SC-004**：M0 + 模板含 schema 100% 不跳填志願頁；M1/M2 + 模板無 schema 100% 沿用既有 reject 路徑（不引入新分支）。
- **SC-005**：「跳過此步驟」按鈕 → 沿用 `MechanismRequiresPreferences` 失敗結果頁；錯誤訊息含「M1/M2 需要至少一位角色提供志願」。
- **SC-006**：填志願表單 POST 驗證「同列不可重複」「至少一人有志願」100% 守住——違反者 0% 進入 pipeline 執行。
- **SC-007**：50 學生 × `max_choices=3` = 150 個下拉的填志願頁能正常 render + POST + 跑通；不撞表單 size limit。
- **SC-008**：階段 1-4c 既有 234 個自動化測試 100% 繼續通過。
- **SC-009**：核心模組（`src/matcher/{rules,filter,allocator,...}`）0 改動。
- **SC-010**：本 feature 新增 ≥ 10 個自動化測試（HTTP 整合 + 表單驗證 + Web/CSV 等價 + escape hatch + 各 edge case）。

## Assumptions

- **無新依賴**：本 feature 僅在 `src/matcher/web/` 內加 routes / 樣板；HTML form + jinja2 即可。
- **暫存策略由 plan 決定**：spec 不指定 hidden input vs session；但傾向 hidden input（無新依賴、無 session 管理複雜度）。
- **僅支援模板 `default_targets`**：自訂 targets 旁檔 + UI 填志願視為低頻組合，列為錯誤路徑（FR-009）；未來如需可再開 feature。
- **草稿不儲存**：填一半離開資料就丟；列入 UI 警告。
- **mechanism 偵測與跳轉時機**：在第一次 `/match/run` POST 後判斷；非新增端點，是既有端點的分支。
- **填志願頁版面**：單張長表格（每列一角色、欄為志願 1..N）；桌面優先；不刻意做 mobile 優化（行政場景為主）。
- **不處理**：
  - 「分發個別連結讓學生自己填志願」（→ 階段 4e 或更後）
  - 草稿儲存與恢復（→ 未來）
  - 對象屬性的多欄顯示（如最低年級、主題）—— FR-004 僅顯示顯示名 + 容量
  - 動態增減志願數（max_choices 固定來自模板）
  - 表單欄位的客製排序（沿用 roster 列序）
  - PDF 匯出（→ 階段 3c / 未來 feature）

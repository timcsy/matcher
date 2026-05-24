# Feature Specification: Web UI 機制選擇 + 結果頁志願展示

**Feature Branch**: `008-web-mechanism-prefs`
**Created**: 2026-05-24
**Status**: Draft
**Input**: User description: "Web UI 機制選擇 + 結果頁志願展示：新建媒合表單新增『機制』下拉（M0/M1/M2，預設 M0）；結果頁顯示機制名稱、處理順序、志願排名欄；個別查詢頁顯示『您被分到第幾志願』或『由公平抽籤分到』。填志願仍以 CSV 上傳為主，UI 動態表單留作未來。不動核心模組；技術詞零容忍沿用教訓 6。"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — 行政在 Web 上選機制跑 M1 / M2（Priority: P1）🎯 MVP

學校行政打開「新建媒合」表單，看到模板選單、CSV/Excel 上傳、隨機種子，以及**新增的「分配機制」下拉**（M0 純抽籤 / M1 RSD / M2 Boston，預設 M0）。對於含志願的場景（如研習分組），選 M1 或 M2、上傳含 preferences 欄位的 CSV → 結果頁顯示機制名稱、處理順序、每位被媒合者的志願排名（第 N 志願 / fallback）。Web 跑出的 audit 與 CLI 同樣 mechanism+seed 跑出的 audit 五段逐位元組相同。

**Why this priority**：本 user story 直接讓 vision 階段 4 的三機制承諾在 Web 上實現。目前 M1/M2 只能透過 CLI 跑，行政實際工作流（Web 為主）無法體驗志願序機制。

**Independent Test**：在 Web 上選 study-group + roster-m1.csv + seed 2026 + M2 → 結果頁顯示分配表（含「志願排名」欄）+ 處理順序段；下載 audit 與 CLI 同樣輸入跑出的 audit 五段相同。

**Acceptance Scenarios**：

1. **Given** Web `/match/new` 表單，**When** 使用者展開「分配機制」下拉，**Then** 看到三個選項：「M0 純抽籤」「M1 RSD（隨機輪流挑）」「M2 Boston（層級填滿）」；預設 M0。
2. **Given** 選 M1 + 上傳 roster-m1.csv + seed 2026，**When** 點執行，**Then** 結果頁顯示「分配階段（M1 RSD 隨機輪流挑）」+ 處理順序段 + 分配表含「志願排名」欄（1-based 或「抽籤」）。
3. **Given** Web 跑出的 record，**When** 下載 audit JSON，**Then** 與 CLI 同模板、同 roster-m1.csv、同 seed、同 mechanism 跑出的 audit 在 qualified_set / assignment / filter_trace / allocation_trace / template_snapshot 五段逐位元組相同。

---

### User Story 2 — 被媒合者個別查詢頁顯示志願滿足度（Priority: P2）

個別查詢頁（`/match/{rid}/role/{role_id}`）在 M1/M2 路徑下新增「您被分到第幾志願」段：若被分配的對象在自己的志願清單中 → 顯示「您被分到第 N 志願：<對象顯示名>」；若是 fallback 抽中且原本有填志願 → 「您原本的志願已被分配給其他人，由公平抽籤分到 <對象顯示名>」；若原本沒填志願 → 「您未在志願清單中，由公平抽籤分到 <對象顯示名>」。M0 路徑不顯示此段。

**Why this priority**：vision 階段 4c 成功標準明文要求「個別查詢頁顯示『您被分到第幾志願』」；對應原則 5「對使用者透明」在 M1/M2 機制下的延伸。

**Independent Test**：以 M1 跑一次 → 取得任一被媒合者 URL → 個別查詢頁應出現「您被分到第 N 志願」相關文案；用 M0 同樣的測試流程 → 不出現此段。

**Acceptance Scenarios**：

1. **Given** M1/M2 路徑的成功 record + 一位獲第 1 志願分配的角色，**When** 開個別查詢頁，**Then** 顯示「您被分到第 1 志願：<對象顯示名>」。
2. **Given** 同 record + 一位 fallback 抽中（有填志願但志願都滿）的角色，**When** 開頁，**Then** 顯示「您原本的志願已被分配給其他人，由公平抽籤分到 <對象顯示名>」。
3. **Given** 同 record + 一位 fallback 抽中（沒填志願）的角色，**When** 開頁，**Then** 顯示「您未在志願清單中，由公平抽籤分到 <對象顯示名>」。
4. **Given** M0 路徑的 record，**When** 開個別查詢頁，**Then** **不**出現「您被分到第幾志願」段。

---

### User Story 3 — Web 路徑的 M1/M2 拒絕與錯誤回應（Priority: P3）

使用者在 Web 選 M1 / M2 但上傳全空 preferences 的 CSV → 系統明確拒絕並顯示友善訊息（沿用 admin 結果頁失敗模式 + 既有 MechanismRequiresPreferences）。

**Why this priority**：邊界處理；無此處理會讓使用者看到 500 或不明錯誤。

**Independent Test**：選 M1 + 上傳 examples/study-group/roster.yaml（全空 prefs）→ 結果頁顯示失敗、訊息含「M1 需要至少一位角色提供志願」。

**Acceptance Scenarios**：

1. **Given** Web 選 M1 + roster 全空 prefs，**When** 執行，**Then** 結果頁顯示失敗、錯誤類別為 `MechanismRequiresPreferences`、訊息含「M1 需要至少一位角色提供志願」與「改用 mechanism=M0」建議。
2. **Given** Web 選 M2 + roster 全空 prefs，**When** 執行，**Then** 訊息為「M2 需要至少一位角色提供志願」（動態填寫）。
3. **Given** Web 選 M0 + roster 任一非空 prefs，**When** 執行，**Then** 結果頁顯示失敗、訊息為 `PreferencesNotSupported`（沿用既有）。

---

### Edge Cases

- **mechanism 下拉的非法值**：HTML form 限制為 3 選項；POST 端點仍須驗證並對非法值給明確錯誤。
- **「志願排名」欄在 M0 路徑**：不顯示該欄（conditional render），避免「-」滿欄混亂。
- **個別查詢頁的「第幾志願」段**：M0 路徑完全不出現；M1/M2 + 未分配的角色不出現此段（既有 3b 失敗模式處理）。
- **技術詞零容忍**：「您被分到第 N 志願」不可暴露 `preference_rank` 等英文 token（沿用教訓 6）。
- **處理順序段**：M0 路徑下 audit 中 `processing_order` 為 null → 不顯示；M1/M2 下顯示為「S03 → S01 → ...」。

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**：`/match/new` 表單 MUST 新增「分配機制」下拉欄位，3 個選項分別為「M0 純抽籤」「M1 RSD（隨機輪流挑）」「M2 Boston（層級填滿）」；預設 M0。
- **FR-002**：「分配機制」下拉旁 MUST 附簡短說明文字（≤ 50 字），引導使用者「無志願選 M0；有志願選 M1 或 M2」。
- **FR-003**：`/match/run` 端點 MUST 接受 `mechanism` 表單參數；規範化大寫；不在 {M0, M1, M2} 中時回應 400 + 明確訊息。
- **FR-004**：結果頁（admin 視圖、`match_result.html`）MUST 顯示機制名稱（標題段：「分配階段（M0 純抽籤 / M1 RSD 隨機輪流挑 / M2 Boston 層級填滿）」）。
- **FR-005**：結果頁在 M1 / M2 路徑下 MUST 顯示「處理順序」段，列出 audit 中 `processing_order` 序列（含對應角色顯示名）。
- **FR-006**：結果頁分配表 MUST 新增「志願排名」欄；M1/M2 路徑下顯示「第 N 志願」或「抽籤」（依 preference_rank 與 fallback_random_index 推導）；M0 路徑下**不顯示**此欄。
- **FR-007**：個別查詢頁（`individual_view.html`）MUST 在 M1 / M2 路徑下新增「您被分到第幾志願」段，依 audit 推導出三種顯示：
  - (a) `preference_rank` 非 null（被分到志願）→ 「您被分到第 N 志願：<對象顯示名>」
  - (b) `fallback_random_index` 非 null + `preferred_order` 非空 → 「您原本的志願已被分配給其他人，由公平抽籤分到 <對象顯示名>」
  - (c) `fallback_random_index` 非 null + `preferred_order` 為空 → 「您未在志願清單中，由公平抽籤分到 <對象顯示名>」
  - M0 路徑或未分配者**不顯示**此段
- **FR-008**：所有新增文案 MUST 通過 FORBIDDEN_TECHNICAL_TOKENS / FORBIDDEN_PATTERNS 正則驗證（教訓 6）——不可暴露 `preference_rank` / `fallback_random_index` / `preferred_order` 等英文 token。
- **FR-009**：Web 路徑與 CLI 同模板 + 同 roster + 同 seed + 同 mechanism MUST 跑出的 audit 在 5 個核心欄位（qualified_set / assignment / filter_trace / allocation_trace / template_snapshot）逐位元組相同（沿用 SC-003 from 3a，延伸至 M1/M2）。
- **FR-010**：M1 / M2 + 全空 prefs 上傳 → Web 失敗結果頁顯示 `MechanismRequiresPreferences` 友善訊息（沿用既有 3a 結果頁失敗模式）。
- **FR-011**：本 feature MUST 不動核心模組（`src/matcher/{rules,filter,allocator,pipeline,audit,errors,data_import,template_loader,rng,roster}`）——所有變更限於 `src/matcher/web/`。
- **FR-012**：不引入 Web 表單填志願介面（保留 CSV/Excel 上傳為唯一填志願入口；UI 動態志願表單留作未來）。
- **FR-013**：階段 1+2a+2b+3a+3b+4a+4b 既有 210 個自動化測試 MUST 100% 繼續通過。
- **FR-014**：所有錯誤訊息、CLI 輸出、UI 文案 MUST 為繁中（沿用 constitution）。

### Key Entities

- **分配機制下拉**：HTML `<select>` 元素，3 個固定選項；預設 M0。
- **志願排名欄**：結果頁分配表的可選欄；M1/M2 路徑顯示、M0 不顯示。
- **個別查詢頁的「您被分到第幾志願」段**：依 audit 推導的三種顯示。
- **代名詞替換**：沿用既有 `humanize.py` 規則，本 feature 無新代名詞。

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**：Web 上選 M1 / M2 + roster-m1.csv + seed 2026 跑通；下載 audit 與 CLI 同 mechanism + 同 seed 跑出的 audit 5 個核心欄位 100% bytewise 相同。
- **SC-002**：結果頁在 M1 / M2 路徑下顯示「處理順序」段、「志願排名」欄；M0 路徑下不顯示這兩者。
- **SC-003**：個別查詢頁在 M1 / M2 路徑下對 3 種情境（第 N 志願 / fallback + 有 prefs / fallback + 空 prefs）各顯示對應文案；M0 路徑或未分配者不顯示此段。
- **SC-004**：個別查詢頁與結果頁的新增文案 100% 通過技術詞零容忍正則驗證（沿用 SC-002 from 3b）。
- **SC-005**：M1 / M2 + 全空 prefs 的 Web 上傳 100% 顯示失敗結果頁 + `MechanismRequiresPreferences` 訊息。
- **SC-006**：階段 1+2a+2b+3a+3b+4a+4b 既有 210 個自動化測試 100% 繼續通過。
- **SC-007**：核心模組（`src/matcher/{rules,filter,allocator,...}`）0 改動。
- **SC-008**：本 feature 新增 ≥ 8 個自動化測試（HTTP 整合 + 樣板渲染 + Web/CLI 等價 + 拒絕路徑 + 技術詞驗證）。
- **SC-009**：「分配機制」下拉的旁註說明文字 ≤ 50 字、清晰易懂。

## Assumptions

- **無新依賴**：Web 層僅加 form / template 與 routes 變動。
- **mechanism 預設 M0**：與既有 Web 行為向後相容；不修改既有測試斷言。
- **填志願仍以 CSV 為主**：UI 動態填志願表單屬未來；本 feature 不做。
- **個別查詢頁 fallback 文案邏輯**：依 audit 中 `fallback_random_index` 與 `preferred_order` 長度推導，**不**新增 audit 欄位。
- **「處理順序」段在 admin 視圖**：列出 role_id + 對應角色顯示名（依 roster_snapshot 取 name）；長 list 可用簡單橫向排列「S03 → S01 → S05 → ...」。
- **不處理**：
  - UI 動態填志願表單（→ 未來）
  - 同層超額抽籤的視覺化（audit JSON 已含 tie_break_random_index，UI 不視覺化）
  - 多模板對應不同機制（每模板皆可用三機制）
  - mechanism 推薦邏輯（依模板 preferences_schema 自動建議）
  - 個別查詢頁的「處理順序」段（admin 視圖已含；個別頁不重複）
  - PDF 匯出（→ 階段 3c / feature 009）

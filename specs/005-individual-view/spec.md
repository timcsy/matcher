# Feature Specification: 個別查詢視圖（Individual View）

**Feature Branch**: `005-individual-view`
**Created**: 2026-05-23
**Status**: Draft
**Input**: User description: "個別查詢視圖：被媒合者（老師、班級代表、學生）透過個別 URL 查詢自己在某次媒合中的狀態——基本資訊、最終分配、依模板規則為何有/沒資格；用語面向一般教師。實踐 vision 階段 3b 與原則 5「對使用者透明」。"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — 老師查詢「我被分到哪個班」與「為什麼」（Priority: P1）🎯 MVP

學校行政在媒合完成後，把每位老師的「個別查詢連結」發給對方。老師點連結進入專屬頁面，看到：自己的姓名與屬性、是否被分到班級（哪個班）、依模板規則的判定說明（例：哪幾條規則為什麼通過、哪幾條沒通過、在哪一輪被抽中）。文案用一般教師熟悉的語言，不出現「資格集合」「過濾」「random_index」等技術詞。

**Why this priority**：本 user story 直接兌現原則 5「對使用者透明」的最強形式。沒有個別視圖，當事人面對結果只能信任行政——爭議發生時無法獨立檢視。3a 的「下載 audit JSON」對行政足夠，但對一般老師形同無物。

**Independent Test**：找一位**未參與開發**的中小學老師（不需技術背景），給予一個個別查詢 URL，請其在 5 分鐘內回答兩個問題——「我被分到哪個班？」「為什麼分到（或沒分到）這個班？」；能正確回答即通過。

**Acceptance Scenarios**：

1. **Given** 媒合成功的記錄、老師 T01 的個別查詢 URL，**When** 老師打開該 URL，**Then** 頁面顯示：「您的姓名 / 專業 / 年資」、「您被分到：三年甲班」、「判定說明：依以下規則判斷您能否分到各班…」（含每條規則的繁中說明 + 通過/不通過）。
2. **Given** 同一媒合中老師 T08 被分到的對象在資格集合內但因抽籤未中（容量耗盡前剩餘候選），**When** 打開該 URL，**Then** 頁面顯示「您未被分配」+ 簡短說明（如「容量已滿、抽籤未中」）+ 該老師對所有班級的判定（哪些有資格、哪些沒有）。
3. **Given** 一份個別查詢 URL，**When** 一般教師閱讀整個頁面，**Then** 頁面文字**完全不含**「filter_trace」「allocation_trace」「random_index」「資格集合」「分配機制」等技術詞——統一替換為一般用語（「您是否有資格」「電腦抽籤過程」等）。

---

### User Story 2 — 行政視圖增加「個別查詢連結列表」（Priority: P2）

媒合結果頁（admin 視圖、`/match/{record_id}`）新增可摺疊區段，列出所有被媒合者的個別查詢 URL，方便行政一次取得全部連結（複製、貼到 email、群組廣播）。

**Why this priority**：是 US1 的配套——若行政無法輕鬆取得每位連結，US1 不可能在真實流程中被使用。但本身不直接面向當事人，priority 次於 US1。

**Independent Test**：admin 跑完一次教師-班級媒合 → 結果頁可看到「個別查詢連結」區段 → 點開 → 看到 10 位老師的 10 個 URL 與姓名。

**Acceptance Scenarios**：

1. **Given** 媒合成功的結果頁，**When** admin 點「個別查詢連結」可摺疊區段，**Then** 顯示一個表格：每位被媒合者一列，含姓名、角色 id、個別查詢連結（可複製）。
2. **Given** 失敗的媒合結果頁，**When** admin 檢視，**Then** 不顯示「個別查詢連結」區段（失敗紀錄無 audit、無從產生個別視圖）。

---

### User Story 3 — 不存在 / 失敗 / 不在名單的明確錯誤（Priority: P3）

各種「找不到」情境皆有明確繁中錯誤頁，沿用既有 4XX 錯誤頁風格。

**Why this priority**：邊界處理；無此處理會洩漏技術錯誤（500）給當事人。

**Independent Test**：構造三種錯誤情境（record 不存在 / role_id 不在 record 中 / status=failed 的 record），驗證 404 + 訊息對一般人友善。

**Acceptance Scenarios**：

1. **Given** 不存在的 record_id，**When** 打開 `/match/<bad_id>/role/T01`，**Then** 404 + 訊息「找不到該次媒合的紀錄」+ 建議「請確認連結是否正確、或聯絡發送連結的行政人員」。
2. **Given** 存在的 record_id 但 role_id 不在該 record 的名單中，**When** 打開，**Then** 404 + 訊息「您不在這次媒合的名單中」+ 同樣建議。
3. **Given** status=failed 的 record_id，**When** 打開 `/match/<id>/role/T01`，**Then** 404 + 訊息「該次媒合執行失敗，無個別查詢資料」。

---

### Edge Cases

- **匿名追蹤**：無 auth 假設下，任何取得 URL 的人皆可查看；URL 結構為 `record_id + role_id`，與 record_id 同樣靠隱蔽性（v1 信任 LAN）。
- **被媒合者「未分配」**：頁面正常顯示，原因說明聚焦於「為什麼資格集合內未被抽中」或「無資格 target」。
- **規則描述含技術 token**：例如模板規則描述寫「依 role.speciality 比對 target.required_subjects」→ 顯示前做代名詞替換（`role.X` → 「您的 X」、`target.X` → 「該對象的 X」）。
- **規則 ID 與 description 衝突**：若描述為空（不應發生但保險），顯示「規則 R001」+ 通過/不通過。
- **個別查詢頁完全靜態化**：只讀 audit 內容，不引入即時計算 → 與下載的 audit JSON 完全一致。

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**：系統 MUST 提供 `GET /match/{record_id}/role/{role_id}` 端點，回應該角色在該次媒合中的個別查詢頁。
- **FR-002**：個別查詢頁 MUST 顯示該角色的：(a) 基本資訊（依 roster_snapshot 的 attributes 全部欄位），(b) 最終分配結果（被分到的對象顯示名稱與 id；或「未分配」），(c) 媒合過程說明（依 filter_trace 過濾出該角色的所有判定 + allocation_trace 中該角色的抽籤步驟）。
- **FR-003**：個別查詢頁的文字 MUST**完全不含**下列技術詞或其原樣字串：`filter_trace`、`allocation_trace`、`qualified_set`、`role.<X>`、`target.<X>`、`random_index`、`exit_code`；改為一般教師熟悉的中文用語。
- **FR-004**：規則的自然語言說明渲染時 MUST 做代名詞替換：`role.<attribute>` → 「您的 <attribute 對應的繁中欄位顯示名>」、`target.<attribute>` → 「該對象的 <繁中欄位顯示名>」；attribute 對應的顯示名來自模板 attributes 宣告中的 description 或 ui_fields 的 label（若有）。
- **FR-005**：媒合結果頁（admin 視圖）MUST 新增「個別查詢連結」可摺疊區段，列出所有被媒合者的姓名 / role_id / 個別查詢 URL（成功媒合時顯示；失敗媒合時不顯示）。
- **FR-006**：對下列情境 MUST 回應 404 + 明確繁中訊息：record_id 不存在、role_id 不在 record 中、status=failed。
- **FR-007**：個別查詢頁的內容 MUST 完全由既有 audit 與模板資料推導，不引入即時重算；同一 record + role_id 多次訪問結果完全一致。
- **FR-008**：本 feature MUST 不引入任何認證機制（沿用階段 3a 的「信任 LAN」假設）。
- **FR-009**：本 feature MUST 不動既有核心模組（`src/matcher/{rules,filter,allocator,pipeline,audit,data_import,template_loader}`）；新增的全部位於 Web 層。
- **FR-010**：本 feature MUST 不改既有 audit schema（v1.2 不變）；不改 match-record schema（1.0 不變）。
- **FR-011**：階段 1+2a+2b+3a 既有 142 個自動化測試 MUST 100% 繼續通過。
- **FR-012**：個別查詢頁 MUST 提供「返回行政首頁」與「下載我的稽核紀錄段落」兩個操作；後者輸出該角色相關的 filter_trace 與 assignment 子集（JSON）。

### Key Entities

- **個別查詢頁（Individual View Page）**：呈現某角色在某次媒合中的「我的視圖」；資料完全來自既有 audit。
- **個別查詢 URL**：`/match/{record_id}/role/{role_id}`；行政可由 admin 視圖一次取得全部連結。
- **代名詞替換規則**：把模板規則中的 `role.X` / `target.X` 替換為一般教師熟悉的中文用語。
- **個別 audit 子集**：FR-012 中可下載的、只含該角色相關 filter_trace 條目與該角色 assignment 對應的 JSON。

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**：一位**未參與開發、不需技術背景**的中小學老師，在拿到個別查詢 URL 後 5 分鐘內能獨立回答兩個問題：「我被分到哪個班？」「為什麼分到/沒分到？」（人工驗證）
- **SC-002**：個別查詢頁的 HTML response **0%** 包含 FR-003 列出的技術詞或原樣 `role.X` / `target.X` 字串（自動化測試以正規表達式驗證）
- **SC-003**：對 3 種錯誤情境（不存在 record / 不在名單 / failed 紀錄）皆回應 404 + 明確繁中訊息，0% 顯示 500 或技術錯誤頁
- **SC-004**：admin 結果頁含「個別查詢連結」區段；列表中的 URL 數 = 該次媒合的角色數
- **SC-005**：同一 record + role_id 訪問兩次的 HTML response **逐位元組相同**（無時間戳、無隨機元素混入）
- **SC-006**：個別 audit 子集下載端點對該角色的 filter_trace 條目數 = audit.filter_trace 中 role_id 等於該 role 的條目數（完整且不多不少）
- **SC-007**：階段 1+2a+2b+3a 既有 142 個自動化測試 100% 繼續通過
- **SC-008**：新增 ≥ 8 個整合測試覆蓋：成功配對的視圖、未分配的視圖、技術詞零容忍、代名詞替換、admin 連結列表、3 種 404 情境

## Assumptions

- **無 auth**：沿用 vision「v1 信任 LAN」假設；URL 結構為 `record_id + role_id`，靠隱蔽性。未來部署到公網時須先加 auth。
- **代名詞顯示名來源**：模板 `attributes.roles[].description` 與 `attributes.targets[].description` 為主；若無則用 attribute key 原樣（fallback）。
- **「為什麼沒分到」的解釋深度**：本階段提供「規則層級」的解釋（哪些規則通過/沒通過、抽籤是否輪到）；不提供「如果某規則改變則會發生什麼」之類的反事實分析。
- **「下載我的稽核紀錄段落」**（FR-012）：JSON 格式，含 `role_id`、`role_attributes`、`assignment`、`filter_trace_subset`（只屬該 role 的條目）。
- **被媒合者的「對象」識別**：個別視圖中顯示對象的 attributes.name；若無則顯示 target_id。
- **不處理**：
  - 認證 / 個別 token（→ 未來公網部署時加）
  - PDF 匯出（→ feature 006）
  - 申訴 / 異議 / 編輯介面（vision 範圍邊界已排除「動態調整」）
  - 統計儀表板（聚合視圖；超出本階段範圍）
  - 通知系統（email / SMS）
  - 多語系（繁中為唯一語系）
  - 反事實分析（「如果這條規則放寬會怎樣」）
  - 即時更新（媒合紀錄為一次定案、靜態檢視）

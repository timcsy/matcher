# Feature Specification: M1 RSD 分配機制（隨機輪流挑）

**Feature Branch**: `006-m1-rsd-mechanism`
**Created**: 2026-05-23
**Status**: Draft
**Input**: User description: "M1 RSD（隨機輪流挑）分配機制：啟用核心引擎『志願非空』分支；mechanism dispatch 從固定 M0 擴為 M0/M1；CLI --mechanism M0|M1；audit schema v1.2→v1.3 新增處理順序紀錄；mechanism=M1 + 空 preferences 明確拒絕；既有 M0 路徑完全不變、所有黃金檔重生為 v1.3（assignment 不變）。本 feature 為階段 4a；4b（M2 Boston）與 4c（Web UI 填志願 + 機制選擇器）拆為後續。"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — 用 M1 跑通研習分組志願序媒合（Priority: P1）🎯 MVP

學校行政準備研習分組名單（含每位學生的志願組別清單）；以 CLI 執行 `matcher run --template study-group --roster-csv <csv> --seed N --mechanism M1`，系統先隨機決定處理順序（由 seed 推導），再依該順序讓每位學生挑「目前還有名額的最高志願」。結果頁顯示分配 + 處理順序 + 每人挑了第幾志願。稽核紀錄完整記錄處理順序與每人選擇，使同 seed 重跑能 bytewise 重現。

**Why this priority**：階段 1 預留的 preferences 介面與階段 2a 預留的 preferences_schema 終於在本 user story「兌現」；沒有 M1，整條「志願序機制」的承諾無法兌現。本 feature 直接驗證 vision 階段 4 的第一條成功標準。

**Independent Test**：以「研習分組」內建模板 + 含 preferences 欄位的範例 CSV + seed 2026 + `--mechanism M1` 執行；驗證：(a) 每位學生被分到的組別在其志願清單中（除非所有志願組別皆已滿）；(b) 兩次同輸入產出的稽核紀錄 bytewise 相同；(c) 稽核中 `processing_order` 為長度 = 角色數的順序串。

**Acceptance Scenarios**：

1. **Given** study-group 模板 + 9 位學生的 CSV（每人 1-3 個志願）+ seed 2026 + mechanism=M1，**When** 執行 `matcher run`，**Then** 系統依「隨機處理順序」逐位分配；每位學生最終獲得「其志願清單中第一個還有名額的組別」；稽核紀錄含 `mechanism: "M1"`、`processing_order` 序列、每人 `preference_satisfied_rank`。
2. **Given** 與情境 1 相同的輸入，**When** 再次執行，**Then** 稽核紀錄與第一次逐位元組相同（含處理順序、每人選擇）。
3. **Given** 同 roster + seed 但 mechanism=M0，**When** 執行，**Then** M0 路徑運作（忽略 preferences 走純抽籤，行為與階段 1 完全一致）——這驗證向後相容。

---

### User Story 2 — mechanism=M1 + 空 preferences 明確拒絕（Priority: P2）

若使用者選擇 mechanism=M1，但匯入的 roster 中**所有角色的 preferences 皆為空**，系統明確拒絕並提示「M1 需要至少一位角色提供志願；若無志願請改用 mechanism=M0」。避免「我以為跑了 M1 結果其實是 M0」的混淆。

**Why this priority**：教訓 2「介面預留 + 拒絕分支」的對偶——現在 M1 啟用了，但**反向**保留拒絕：使用者顯式選 M1 但資料不滿足 → 顯式拒絕，不退化。

**Independent Test**：以空 preferences 的 CSV + `--mechanism M1` → exit 非 0 + 訊息含「M1 需要至少一位角色提供志願」。

**Acceptance Scenarios**：

1. **Given** roster 中所有角色 preferences 為空 + mechanism=M1，**When** 執行，**Then** 系統拒絕並回應「M1 需要至少一位角色提供志願；若無志願請改用 mechanism=M0」訊息 + 對應 exit code。
2. **Given** roster 中部分（≥ 1 位）角色 preferences 非空 + mechanism=M1，**When** 執行，**Then** 系統正常執行；preferences 為空的角色按「處理到他時所有資格集合內仍有名額的對象任意抽一個」處理（不退化整批為 M0）。
3. **Given** roster 中所有角色 preferences 非空 + mechanism=M0，**When** 執行，**Then** 系統沿用既有階段 1 拒絕邏輯（PreferencesNotSupported）——M0 不接受 preferences。

---

### User Story 3 — 既有 M0 路徑完全向後相容（Priority: P3）

階段 1+2a+2b+3a+3b 既有 169 個自動化測試 100% 繼續通過；M0 路徑的 audit 結構（除 schema_version 升至 v1.3 + 新增 null 欄位外）邏輯不變；既有 5 個黃金檔重生（含 baseline、teacher-class-template、study-group-template、teacher-class-csv、study-group-xlsx），assignment / qualified_set / filter_trace / allocation_trace 等核心欄位皆不變。

**Why this priority**：「向後相容」是教訓 5（library + CLI + Web 三入口分層）與教訓 3（audit schema 演進「新增可選欄位 + null」）的關鍵保證；違反此 SC 表示分層或 schema 演進策略失敗。

**Independent Test**：跑既有 169 個測試 → 100% 通過；以 `git diff` 檢視重生後的 5 個黃金檔 → 變動僅限「schema_version 升 v1.3」與「新增 M1 相關欄位皆為 null」。

**Acceptance Scenarios**：

1. **Given** 既有的所有 M0 CLI / Web / 黃金檔測試，**When** 跑全量回歸，**Then** 169 個測試 100% 通過。
2. **Given** 既有 teacher-class-baseline.audit.json 黃金檔，**When** 以階段 1 的指令重生，**Then** diff 只顯示：`schema_version: "1.2" → "1.3"` + 新增 `processing_order: null`（或本 feature 新增的其他 null 欄位）；其餘逐位元組不變。

---

### Edge Cases

- **單一角色 preferences 為空、其餘非空 + mechanism=M1**：被處理到該角色時，採「資格集合內任意還有名額者抽一」；不退化整批為 M0。
- **某角色所有志願皆已被分配滿**：該角色未被分配（assignment[role] = null）；audit 記錄「processing time 所有志願已滿」原因。
- **preferences 含資格集合外的對象 id**：以「靜默忽略不在資格集合內的志願」處理，不拋錯（avoid 過度嚴格）。
- **preferences 含重複的對象 id**：取第一個出現，後續重複忽略（規範化 dedup）。
- **mechanism 既不是 M0 也不是 M1**：CLI / pipeline 拒絕，列出支援機制清單。
- **既有 audit schema v1.2 的黃金檔**：本 feature 完成後**不再有效**——必須重生為 v1.3。
- **M1 處理順序的隨機性**：由 seed 推導；同 seed → 同順序；audit 中 `processing_order` 為人類可讀的序列（角色 id 陣列）。

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**：系統 MUST 支援 `mechanism` 參數取值為 `"M0"` 或 `"M1"`；既有預設值維持 `"M0"`。
- **FR-002**：當 `mechanism="M1"` 且 roster 中**至少一位**角色的 preferences 非空時，系統 MUST 走 M1（RSD）演算法。
- **FR-003**：當 `mechanism="M1"` 且 roster 中**所有**角色的 preferences 皆為空時，系統 MUST 拒絕並回應明確訊息「M1 需要至少一位角色提供志願；若無志願請改用 mechanism=M0」。
- **FR-004**：M1 演算法 MUST 滿足以下行為——
  - (a) 以 seed 推導「處理順序」（角色 id 的隨機排列，採顯式 Fisher–Yates，沿用既有 SeededRandom 介面）
  - (b) 依處理順序逐位處理角色：取該角色「資格集合內 ∩ 該角色 preferences 中仍有名額者」中**最高志願**並分配
  - (c) 若該角色所有志願皆已被分配滿（preferences 內所有 target 容量耗盡），但資格集合內仍有其他 target 有名額：從「資格集合內所有仍有名額者」中**任意抽一個**（同樣由 seed 推導）
  - (d) 若該角色 preferences 為空但資格集合內仍有有名額者：等同 (c) 從中任意抽一個
  - (e) 若該角色所有 target（無論是否在 preferences 內）皆已耗盡容量：該角色未被分配
- **FR-005**：系統 MUST 在 `mechanism="M0"` 時維持階段 1 既有行為——preferences 非空時拒絕（PreferencesNotSupported）、preferences 空時走 M0 純抽籤。
- **FR-006**：audit schema MUST 從 v1.2 升級為 v1.3，新增三個欄位（皆可為 null）——
  - `processing_order`：M1 時為角色 id 陣列；M0 時為 null
  - 每筆 `allocation_trace` 項目可新增 `preference_rank`（M1 時為「分到的對象在 preferences 中的排名」整數或 null（從志願外抽中）；M0 時為 null）
  - 既有其他欄位（mechanism、seed、qualified_set、assignment、filter_trace、template_snapshot、import_metadata）皆不變
- **FR-007**：稽核紀錄 MUST 在 M1 路徑下完整記錄處理順序與每位角色的選擇結果，使同 seed 重跑可逐位元組重現。
- **FR-008**：CLI `matcher run` MUST 新增 `--mechanism <M0|M1>` 選項；不指定時預設 `M0`；非支援的機制值 → 明確錯誤訊息列出支援清單。
- **FR-009**：preferences 中**不在資格集合內**的 target id MUST 被靜默忽略（不拋錯）；preferences 中**重複**的 target id MUST 取第一個並忽略後續（規範化 dedup）。
- **FR-010**：既有 5 個黃金檔（baseline、teacher-class-template、study-group-template、teacher-class-csv、study-group-xlsx）MUST 重生為 schema v1.3；diff 應僅顯示 schema_version 升版 + 新增 null 欄位；assignment / qualified_set / filter_trace / allocation_trace 等核心欄位邏輯不變。
- **FR-011**：階段 1+2a+2b+3a+3b 既有 169 個自動化測試 MUST 100% 繼續通過（含 Web 路徑、CLI 路徑、黃金檔比對）。
- **FR-012**：study-group 內建模板的範例 roster MUST 新增一份含 preferences 的版本（CSV），供 M1 演示與測試。
- **FR-013**：所有錯誤訊息、CLI 輸出、稽核紀錄中可閱讀文字 MUST 為繁中（沿用 constitution）。
- **FR-014**：Web UI 端點本階段不修改——既有 Web 流程繼續以 M0 跑（因 Web 尚無填志願介面，屬 feature 008）；CLI 是 M1 的唯一入口。

### Key Entities

- **mechanism 參數**：列舉 `"M0" | "M1"`；現有所有 audit 與 record 結構皆從 mechanism 推導行為。
- **M1 處理順序（processing_order）**：角色 id 的隨機排列；由 seed 推導；audit 中可重播。
- **per-role choice**：每位角色在處理時的選擇——最高未滿志願 / 從非志願但仍有名額者抽一 / 完全無對象。
- **preference_rank**：M1 路徑下，每位被分配角色的選擇在其 preferences 中的排名（1-based；不在 preferences 中為 null）。
- **audit schema v1.3**：v1.2 + processing_order 欄位 + allocation_trace 條目可選 preference_rank。

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**：給定相同（規則 + 名單含 preferences + seed + mechanism=M1），兩次執行的稽核紀錄逐位元組相同（沿用既有黃金檔模式）
- **SC-002**：以 study-group 模板 + 9 位學生的範例 CSV（每人 1-3 個志願）+ `--mechanism M1` 跑通；audit 中每位被分配角色的 `preference_rank` 為其偏好清單中的合法排名（或 null 表示從非偏好但仍有名額者抽中）
- **SC-003**：當 mechanism=M1 + roster 所有角色 preferences 皆空 → 100% 拒絕並回應明確訊息；0% 靜默退化為 M0
- **SC-004**：當 mechanism=M0 + roster 任一角色 preferences 非空 → 沿用階段 1 PreferencesNotSupported 拒絕（向後相容）
- **SC-005**：階段 1+2a+2b+3a+3b 既有 169 個自動化測試在本 feature 完成後 100% 繼續通過
- **SC-006**：既有 5 個黃金檔重生後 diff 僅顯示 schema_version 升版 + 新增 null 欄位；assignment / qualified_set / filter_trace / allocation_trace 邏輯不變
- **SC-007**：M1 演算法的「處理順序」由 seed 推導；同 seed → 同順序（與「黃金檔比對」教訓一致）
- **SC-008**：preferences 含資格集合外的 target id → 100% 被靜默忽略；含重複 id → 100% dedup
- **SC-009**：本 feature 新增 ≥ 12 個自動化測試（unit + integration），涵蓋 M1 演算法、mechanism dispatch、拒絕邏輯、向後相容
- **SC-010**：CLI 對非支援的 `--mechanism` 值 100% 回應明確錯誤訊息列出支援清單

## Assumptions

- **M1 演算法為 Random Serial Dictatorship 標準形式**：「先隨機洗牌處理順序、後逐位選最高未滿志願」；無「策略性反向誘導」（strategyproof 性質為 RSD 內建）。
- **seed 推導兩種隨機性的順序**：先處理順序（Fisher–Yates over roles），再每位角色處理時若無志願但有資格 target → 隨機抽（這個抽動作消耗 seed state）；兩種隨機性共用同一 SeededRandom 物件以維持「同 seed 同結果」。
- **M0 行為完全不變**：preferences 非空 + M0 仍走 PreferencesNotSupported；preferences 空 + M0 走純抽籤。
- **`mechanism` 值的傳遞鏈**：CLI `--mechanism` → `MatcherInput.mechanism` → `pipeline.run_match` dispatch → `allocate_m0` 或 `allocate_m1`。
- **audit schema v1.3 是非破壞性升版**：新增可選欄位（皆 null 在 M0 路徑），既有欄位語意與型別不變。
- **黃金檔重生策略**：與階段 2a/2b/3a 重生相同模式；commit 中 diff 明確顯示「schema_version 升版 + 新增 null 欄位」。
- **Web UI 不變**：本 feature CLI-only；Web 仍跑 M0；UI 填志願介面為 feature 008。
- **不處理**：
  - M2 Boston 機制（→ feature 007）
  - Web UI 機制選擇下拉、表單填志願（→ feature 008）
  - 「全策略性 / 全 truthful / DA」之類學術變體演算法
  - 動態調整既有結果（vision 範圍邊界已排除）
  - preferences 表達能力擴充（仍為 `list[target_id]`；不引入「禁絕對象」「同等偏好」）
  - 多種 RSD 變體（如「分批 RSD」「兩階段 RSD」）

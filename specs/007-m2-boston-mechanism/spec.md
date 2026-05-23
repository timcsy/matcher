# Feature Specification: M2 Boston 分配機制（層級填滿）

**Feature Branch**: `007-m2-boston-mechanism`
**Created**: 2026-05-24
**Status**: Draft
**Input**: User description: "M2 Boston（層級填滿）分配機制：先全塞第 1 志願（超額抽籤），剩餘退到第 2 志願，以此類推。沿用 4a 的 mechanism dispatch；M2 + 全空 prefs 走拒絕；audit schema 保持 v1.3 但 allocation_trace 條目新增 tie_break_random_index 欄位（M0/M1 為 null）；錯誤類別由 M1RequiresPreferences 重新命名為 MechanismRequiresPreferences；CLI --mechanism 擴為 M0|M1|M2；複用 study-group/roster-m1.csv 跑 M2 範例；既有 188 測試 100% 通過、6 個既有黃金檔不變。Web UI 不動（屬 4c）。"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — M2 跑通研習分組志願序媒合（Priority: P1）🎯 MVP

學校行政以 CLI `matcher run --template study-group --roster-csv ... --seed N --mechanism M2`。系統依層級逐次處理志願：先把所有人的第 1 志願全塞到對應組別（同組別人數超過容量時用 seed 推導的抽籤決定誰中、誰落到下一層）；落到下一層的繼續以「第 2 志願」嘗試，以此類推；所有層級完成後仍未分配的角色 → 從合格 ∩ 仍有名額者抽一（fallback，與 M1 對齊）。結果頁與 audit 顯示「每位被分到第幾志願」+ 「同層超額抽籤的細節」。

**Why this priority**：vision 階段 4 路線圖明文要求支援 M2；本 user story 直接兌現「分配機制三選一」承諾。沒有 M2，使用者只能在「公平抽籤（M0）」與「逐位隨機輪流挑（M1）」二選一；M2 對應「想最大化整體偏好滿足」的另一公平定義。

**Independent Test**：以 study-group + 含 preferences 的 CSV + seed 2026 + `--mechanism M2` 跑通；驗證：(a) 兩次同輸入產出的稽核紀錄 bytewise 相同；(b) audit 中每位被分配角色的 `preference_rank` 為其被分到的層級（1-based）；(c) 同層超額抽籤的角色其 `tie_break_random_index` 為非 null 整數。

**Acceptance Scenarios**：

1. **Given** study-group 模板 + 9 位學生的含 preferences CSV（與 4a 同檔）+ seed 2026 + mechanism=M2，**When** 執行 `matcher run`，**Then** 系統依層級填滿；audit 含 `mechanism: "M2"`、`processing_order` 序列、每筆 trace 含 `preference_rank` 與 `tie_break_random_index` 兩欄位。
2. **Given** 與情境 1 相同的輸入，**When** 再次執行，**Then** 稽核紀錄 bytewise 相同。
3. **Given** 同 roster + seed 但 mechanism=M1，**When** 執行，**Then** M1 路徑運作（沿用既有 4a 黃金檔；本 feature 不影響）。

---

### User Story 2 — 機制需要志願的拒絕邏輯（Priority: P2）

若使用者選 mechanism=M1 或 M2，但 roster 中**所有**角色的 preferences 皆為空 → 系統明確拒絕並提示「該機制需要至少一位角色提供志願；若無志願請改用 mechanism=M0」。錯誤類別由 `M1RequiresPreferences` 重新命名為通用的 `MechanismRequiresPreferences`（exit 40 不變）。

**Why this priority**：4a 已建立的拒絕模式對 M2 完全適用；本 feature 把「M1 專屬」的命名通用化，為未來機制（M3、M4…）鋪路。

**Independent Test**：以空 preferences 的 roster + `--mechanism M1` 或 `--mechanism M2` 皆得到相同錯誤碼與訊息。

**Acceptance Scenarios**：

1. **Given** roster 全空 preferences + mechanism=M2，**When** 執行，**Then** exit 40 + 訊息含「M2 需要至少一位角色提供志願」與「請改用 mechanism=M0」。
2. **Given** roster 全空 preferences + mechanism=M1，**When** 執行，**Then** 與情境 1 相同行為（沿用 4a；訊息含「M1 需要...」）。
3. **Given** roster 部分非空 preferences + mechanism=M2，**When** 執行，**Then** 系統正常執行；preferences 為空的角色按既有 fallback 處理。

---

### User Story 3 — 既有 M0 / M1 路徑完全向後相容（Priority: P3）

階段 1–4a 既有 188 個自動化測試 100% 繼續通過；既有 6 個黃金檔（5 個 M0 + 1 個 M1）**邏輯不變**；allocation_trace 既有欄位 `preferred_order` / `preference_rank` / `fallback_random_index` 在 M0/M1 路徑下值不變；新增 `tie_break_random_index` 欄位在 M0/M1 路徑下為 null。

**Why this priority**：教訓 5 + 教訓 7 的硬要求——核心職責擴充必須不破壞既有路徑。

**Independent Test**：跑全量回歸測試 → 100% 通過；既有 6 個黃金檔 diff 僅顯示「新增 tie_break_random_index: null」。

**Acceptance Scenarios**：

1. **Given** 既有 M0/M1 CLI 測試，**When** 跑全量回歸，**Then** 188 個測試 100% 通過。
2. **Given** 既有 6 個黃金檔（teacher-class-baseline / -template / -csv、study-group-template / -xlsx / -m1），**When** 重生，**Then** diff 僅顯示「每筆 allocation_trace 條目新增 `tie_break_random_index: null` 欄位」；其他欄位逐位元組不變。

---

### Edge Cases

- **同層超額抽籤的隨機性**：由 seed 推導；同 seed → 同抽籤結果；audit 中 `tie_break_random_index` 為「在該層該 target 競爭者洗牌後的索引」。
- **角色所有志願皆被擠掉**：系統 fallback 至「合格 ∩ 仍有名額」抽籤（與 M1 fallback 一致）；audit 中 `preference_rank = null`、`fallback_random_index` 非 null。
- **角色 preferences 為空但 mechanism=M2**：與 M1 相同——進 fallback 抽籤。
- **preferences 含資格集合外 id**：靜默忽略（沿用 4a 規範化）。
- **preferences 含重複 id**：取第一個（沿用 4a 規範化）。
- **錯誤類別重新命名**：既有任何斷言「M1RequiresPreferences」的測試需更新為「MechanismRequiresPreferences」（這也是教訓 3「新增可選欄位 + null」對「重命名」的不適用——重命名是破壞性，但本 feature 將把舊名作為 alias 維持向後相容）。

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**：系統 MUST 支援 `mechanism` 參數取值為 `"M0"` / `"M1"` / `"M2"`；既有預設值維持 `"M0"`。
- **FR-002**：當 `mechanism="M2"` 且 roster 中**至少一位**角色的 preferences 非空時，系統 MUST 走 M2（Boston 層級填滿）演算法。
- **FR-003**：當 `mechanism="M1"` 或 `"M2"` 且 roster 中**所有**角色的 preferences 皆為空時，系統 MUST 拒絕並回應明確訊息「<機制> 需要至少一位角色提供志願；若無志願請改用 mechanism=M0」。錯誤類別為 `MechanismRequiresPreferences`（exit 40）。
- **FR-004**：M2 演算法 MUST 滿足以下行為——
  - (a) 依層級 L = 1, 2, ... 逐次處理：對每個 target，收集「該 target 為其第 L 志願的尚未分配角色」
  - (b) 同 target 競爭者 ≤ 剩餘容量 → 全部分配；超額 → 用 SeededRandom + Fisher-Yates 對競爭者洗牌、取前 N 名（N = 剩餘容量）
  - (c) 同層的多個 target 競爭處理順序固定（依 target_id 字母序），確保 seed 推導決定性
  - (d) 所有層級處理完仍未分配的角色 → 從「合格 ∩ 仍有名額」中抽一（fallback，與 M1 一致；使用同一 SeededRandom）
  - (e) preferences 規範化（去重 + 忽略資格外）沿用 4a 邏輯
- **FR-005**：既有錯誤類別 `M1RequiresPreferences` MUST 重新命名為 `MechanismRequiresPreferences`；exit code 40 不變；舊名稱可選地保留為 alias（向後相容）。
- **FR-006**：audit schema 保持 v1.3；`allocation_trace` 每筆條目 MUST 新增可選欄位 `tie_break_random_index`：
  - M2 + 同層超額抽籤時的角色：為 Fisher-Yates 洗牌後該角色的位置索引（int）
  - M2 + 非超額情境（≤ 容量）：null
  - M0 / M1 路徑：永遠 null
- **FR-007**：M2 路徑稽核紀錄 MUST 完整記錄處理過程，使同 seed 兩次跑出的 audit bytewise 相同。
- **FR-008**：CLI `matcher run --mechanism` MUST 接受值 `M0` / `M1` / `M2`（不分大小寫）；不支援值 → exit 2 + 明確錯誤訊息列出支援清單。
- **FR-009**：M2 路徑的 `processing_order` 欄位 MUST 為「角色在 audit.allocation_trace 中出現的順序」——即各層級 + 同層 fallback 完成後的最終排序。語意與 M1 對齊（皆為「分配發生的時序」）。
- **FR-010**：既有 188 個自動化測試 MUST 100% 繼續通過；6 個既有黃金檔重生後 diff 應僅顯示「每筆 allocation_trace 條目新增 `tie_break_random_index: null` 欄位」。
- **FR-011**：本 feature MUST 不修改既有 M0 / M1 演算法邏輯；不修改 audit schema 版本（仍為 v1.3）。
- **FR-012**：所有錯誤訊息、CLI 輸出、稽核紀錄中可閱讀文字 MUST 為繁中（沿用 constitution）。
- **FR-013**：Web UI 本 feature 不修改（既有 Web 仍只跑 M0；UI 機制選擇器與填志願表單屬 feature 008 / 階段 4c）。
- **FR-014**：本 feature MUST 不引入新依賴；演算法皆用既有 `SeededRandom` + 顯式 `fisher_yates_shuffle`。

### Key Entities

- **M2 Boston 演算法**：依層級逐次處理志願；同層超額用 Fisher-Yates 洗牌取前 N 名。
- **層級（level）**：1-based；對應「第幾志願」。
- **同層競爭者（level competitors）**：在某層中以同一 target 為志願的尚未分配角色集合。
- **超額抽籤（super-quota tie-break）**：競爭者 > 剩餘容量時的 Fisher-Yates 洗牌；對應 audit 中的 `tie_break_random_index`。
- **MechanismRequiresPreferences**：通用化錯誤類別（取代 `M1RequiresPreferences`；exit 40）。
- **audit `tie_break_random_index`**：新增可選欄位；只有 M2 + 超額情境為非 null。

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**：給定相同（規則 + 名單含 preferences + seed + mechanism=M2），兩次執行的稽核紀錄 bytewise 相同
- **SC-002**：以 study-group + roster-m1.csv（複用）+ seed 2026 + `--mechanism M2` 跑通；audit 中每位被分配角色的 `preference_rank` 為其分到的層級或 null（fallback 抽籤）
- **SC-003**：M2 + roster 全空 prefs → 100% 拒絕並回應「M2 需要...」訊息（exit 40）；M1 同樣的拒絕邏輯沿用且訊息更新為「M1 需要...」
- **SC-004**：階段 1+2a+2b+3a+3b+4a 既有 188 個自動化測試在本 feature 完成後 100% 繼續通過
- **SC-005**：既有 6 個黃金檔重生後 diff 僅顯示「每筆 allocation_trace 條目新增 `tie_break_random_index: null` 欄位」；assignment / qualified_set / filter_trace / processing_order / preference_rank 等核心欄位邏輯不變
- **SC-006**：CLI 對 `--mechanism M0` / `M1` / `M2`（不分大小寫）皆能正確 dispatch；對非支援值（如 `M3`、`X`）100% 回應 exit 2 + 訊息含支援清單
- **SC-007**：M2 演算法的「同層超額抽籤」由 seed 推導；audit 中 `tie_break_random_index` 為驗算依據
- **SC-008**：M1 與 M2 在相同 seed 與相同 roster 下的 audit `preference_rank` 分布**可能不同**（M2 偏好集中於低層）；這是正常行為而非 bug
- **SC-009**：本 feature 新增 ≥ 10 個自動化測試（unit M2 演算法 + integration CLI + 拒絕邏輯 + 向後相容）
- **SC-010**：錯誤類別重新命名（`M1RequiresPreferences` → `MechanismRequiresPreferences`）後，既有測試斷言 100% 仍可運作（透過 alias 或測試更新）

## Assumptions

- **M2 演算法為 Boston Mechanism / Immediate Acceptance 標準形式**：「先全塞第 1 志願，超額抽籤；剩餘退到第 2 志願…」；無 strategyproof 性質（與 M1 對比）。
- **同層超額抽籤的 Fisher-Yates 採固定順序**：依「target_id 字母序」逐次處理同層的各 target；每個 target 內部用 SeededRandom 洗牌競爭者，取前 N 名。
- **fallback 規則與 M1 對齊**：所有層級處理完仍未分配的角色 → 從「合格 ∩ 仍有名額」抽一；使用同一 SeededRandom；audit 中對應條目 `preference_rank = null`、`fallback_random_index` 非 null。
- **錯誤類別重新命名向後相容**：保留 `M1RequiresPreferences = MechanismRequiresPreferences` alias，避免破壞既有 Python import；或直接更新測試（由 plan 決定）。
- **不處理**：
  - Deferred Acceptance (DA / Gale-Shapley)（屬未來）
  - Top Trading Cycles (TTC)
  - 雙邊志願（vision 範圍邊界已排除）
  - Web UI 機制選擇下拉與填志願表單（→ feature 008 / 階段 4c）
  - 模板 schema 變動（沿用 4a 的 preferences_schema）
  - audit schema 升版（保持 v1.3，僅新增可選欄位 tie_break_random_index）

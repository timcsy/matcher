# Feature Specification: 配對失敗可解釋（資格集合為空）

**Feature Branch**: `015-explain-empty-set`
**Created**: 2026-05-26
**Status**: Draft
**Input**: 真實使用者測試時，UI 填名單跑配對得到「資格集合為空：所有組合皆未通過」，但畫面沒說是哪條規則刷掉、該怎麼修；且失敗後填的內容沒保留。同時發現內建 teacher-class 範本 R003「說明寫中文、實際要英文代碼」會誤導使用者。

## Background / 動機

matcher 的核心價值是「**可解釋**」（principles 原則 1、5）。但目前最容易遇到的失敗——「資格集合為空」（`QualifiedSetEmpty`，exit 10）——卻完全不可解釋：

- `filter_qualified` 其實已逐組算出 filter_trace（每個 (角色,對象) 過了哪些規則、被哪條刷掉），但在資格集合為空時直接 raise，**把 trace 丟掉**。
- 失敗頁只顯示「所有組合皆未通過」，不告訴使用者**哪條規則是元兇、各刷掉多少組**。
- UI 填名單失敗後，填的內容沒保留，使用者無從檢視/修正。

加上內建 teacher-class 範本 R003 的「規則說明」寫「雙語、stem、藝術」，但 `in` 算子實際接受的是英文代碼 `bilingual`/`stem`/`arts`——使用者照說明填中文必然全被刷掉，是一個誘導踩雷。

一個標榜「可解釋」的工具，最常見的失敗卻無法解釋自己，違反其核心原則。本 feature 補上。

## User Scenarios & Testing

### User Story 1 - 空資格集合要說清楚原因（Priority: P1）

身為配對執行者，當我跑出「沒有任何人符合資格」時，畫面要告訴我**是哪條規則刷掉了最多/全部組合**，讓我知道該檢查哪裡，而不是只看到「全部都沒過」。

**Why this priority**：這是本 feature 的核心，直接兌現「可解釋」原則。

**Independent Test**：用 teacher-class 跑一組「班級特色填中文」的名單 → 失敗頁顯示「R003（班級特色…）刷掉了全部 N 組」之類的診斷，並點出 R003 的描述。

**Acceptance Scenarios**：

1. **Given** 一組所有組合都不通過的名單，**When** 執行配對，**Then** 失敗頁列出每條規則「刷掉幾組」的統計，並標出「元兇規則」（淘汰最多者）
2. **Given** 失敗頁，**When** 閱讀，**Then** 不出現技術 token（沿用技術詞零容忍），規則以人類可讀描述呈現
3. **Given** CLI 路徑同樣輸入，**When** `matcher run`，**Then** 退出碼仍為 10，但 stderr / 輸出含可讀的「哪條規則刷掉最多」診斷

---

### User Story 2 - 失敗後保留我填的內容（Priority: P2）

身為 UI 填名單的使用者，配對失敗後，我能看到（或一鍵回到）剛剛填的名單，不必從零重打。

**Why this priority**：減少挫折，但非「可解釋」核心；列 P2。

**Independent Test**：UI 填名單 → 故意觸發空集合 → 失敗頁提供「回去修改（保留剛填內容）」的路徑。

**Acceptance Scenarios**：

1. **Given** UI 填名單觸發空集合失敗，**When** 看失敗頁，**Then** 有「回去修改」可回到填名單頁且內容還在

---

### User Story 3 - 修掉 teacher-class R003 的中英文不一致（Priority: P2）

身為使用內建範本的使用者，teacher-class 的「班級特色」規則說明與實際接受值要一致，照說明填就會過。

**Why this priority**：是內建範本的內容 bug，會誤導；但屬範本資料修正，非引擎能力，列 P2。

**Independent Test**：照 R003 說明填班級特色 → 該規則通過（不再因中英文不一致而全刷）。

**Acceptance Scenarios**：

1. **Given** teacher-class，**When** 檢視 R003，**Then** 說明與接受值一致（照說明填得過）
2. **Given** 既有 examples / golden，**When** 重生，**Then** 仍可成功配對（值對齊後 assignment 合理）

---

### Edge Cases

- **部分角色有資格、部分沒有**：這不是「空集合」（不 raise），維持現狀（個別頁已能解釋）。本 feature 只處理「**全空**」。
- **規則彼此矛盾導致全空**：診斷應仍指出「淘汰最多的規則」，即使多條都刷很多。
- **失敗 record 的 audit**：目前為 None；本 feature 要讓它帶上診斷資料（filter_trace 或統計），但要保持 audit schema 對「成功紀錄」的相容。
- **CLI 無 UI**：US2「保留輸入」不適用 CLI；US1 診斷適用兩者。

## Requirements

### Functional Requirements

- **FR-001**：資格集合為空時，系統 MUST 保留並輸出 filter 診斷資料（每條規則被多少 (角色,對象) 組合「卡住」的統計）
- **FR-002**：失敗頁 MUST 顯示「元兇規則」（淘汰最多組合者）與各規則淘汰數，規則以人類可讀描述呈現
- **FR-003**：診斷頁面 MUST 不含技術 token（沿用既有零容忍清單）
- **FR-004**：CLI 在 exit 10 時 MUST 輸出可讀診斷（保留退出碼 10 不變）
- **FR-005**：UI 填名單觸發空集合失敗 MUST 提供「回去修改、保留內容」路徑
- **FR-006**：內建 teacher-class 範本 R003 的說明與接受值 MUST 一致（使用者照說明填得過）
- **FR-007**：既有「成功配對」的 audit schema MUST 不被破壞（診斷資料只在失敗路徑出現，或以相容方式新增）
- **FR-008**：核心變動 MUST 限於「可解釋性」職責（filter / errors / pipeline / audit）；不擴及無關模組（教訓 7）

### Key Entities

- **QualifiedSetEmpty 例外**：擴充攜帶 filter_trace（或規則淘汰統計），讓上層可解釋
- **規則淘汰統計**：`{rule_id: 卡住組合數}` + 元兇規則 id
- **失敗 MatchRecord**：error 區塊或新增診斷欄位帶上統計（供失敗頁渲染）

## Success Criteria

### Measurable Outcomes

- **SC-001**：teacher-class「班級特色填中文」→ 失敗頁明確指出 R003 是元兇 + 其人類可讀描述
- **SC-002**：失敗頁與 CLI 輸出皆不含技術 token
- **SC-003**：UI 失敗後可回到填名單頁且內容保留
- **SC-004**：照修正後的 teacher-class R003 說明填 → 配對成功
- **SC-005**：全測試（現有 385 + 新增）綠；成功配對 audit 不變（既有 golden 僅因 R003 值修正而重生，trace/assignment 結構不變）

## Assumptions

- 只處理「全空」情境；「部分有資格」維持現狀
- 診斷「元兇」定義為「卡住最多組合的規則」（淘汰計數最大者）；並列最大時可都標示
- R003 修正方向：把接受值改為與說明一致的中文（`雙語`/`stem`/`藝術`），或把說明改為英文——由 plan 決定哪個衝擊小（傾向改值為中文，較貼近使用者直覺）
- 失敗診斷不需逐組全列（資料可能很大）；以「每規則淘汰數 + 元兇」摘要為主，必要時可展開

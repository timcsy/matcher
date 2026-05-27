# Feature Specification: 內部識別碼 role → participant 全面更名

**Feature Branch**: `018-rename-role-participant`
**Created**: 2026-05-27
**Status**: Draft
**Input**: 把 role 全面更名為 participant，與 UI 用詞「參與者」一致（完整改：識別碼 + audit schema + 範本 DSL + URL）

## 背景與動機

UI 用詞已從「角色」改為「參與者」（feature 017）。但程式內部、audit 稽核紀錄、範本規則語法、公開 URL 仍用 `role`。此 feature 把這條「subject 側」概念的英文識別碼全面對齊為 `participant`，消除「畫面說參與者、底層說 role」的認知斷層。

這是**資料模型／schema 演進**（audit schema 升版 + 範本 DSL 變更），依教訓 9 獨立成 feature，讓相容性與 golden 重生等隱藏複雜度先浮現。對外語意維持「參與者 ↔ 對象」（participant ↔ target）。

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 程式碼與稽核紀錄一致用 participant（Priority: P1）

開發者與稽核紀錄的消費者看到的「subject 側」一律是 `participant`：Python 識別碼、audit JSON 鍵、PDF/個別查詢資料皆然，不再 role/participant 混用。

**Why this priority**: 這是本 feature 的核心價值——術語一致。其餘故事都依附於此。

**Independent Test**: 跑全套件綠 + grep `src/matcher`（排除歷史 specs）無殘留 `role`（識別碼層級）+ 重生的 golden audit 含 `participants`/`participant_id` 而無 `roles`/`role_id`。

**Acceptance Scenarios**:

1. **Given** 一份既有 CSV 名單與內建範本，**When** 以相同 seed 跑配對，**Then** 產出的 audit 用 `roster_snapshot.participants`、`allocation_trace[].participant_id`，且 `audit_schema_version` 為 `1.5`。
2. **Given** 同一份輸入與 seed 跑兩次，**When** 比對兩份 audit，**Then** 逐位元組相同（可重現性，原則 2 在新 schema 下仍成立）。

---

### User Story 2 - 範本規則用 participant. 前綴（Priority: P2）

範本作者在規則中以 `participant.<屬性>` 引用 subject 側欄位（取代 `role.<屬性>`）；內建範本、授權指南、表單建立器、AI prompt 範例皆同步。

**Why this priority**: DSL 是範本作者面對的語法，必須與新術語一致；但它依附於 P1 的 parser/schema 更名。

**Independent Test**: 用含 `participant.speciality` 規則的範本跑配對成功；含舊 `role.` 前綴的範本被視為未知前綴而明確報錯（乾淨切斷）。

**Acceptance Scenarios**:

1. **Given** 內建 teacher-class 範本（已改為 `participant.` 規則），**When** 跑配對，**Then** 篩選與分配結果正確、audit 的 `rules_snapshot` 顯示 `participant.` 規則。
2. **Given** 一份舊範本含 `role.speciality`，**When** 載入並跑配對，**Then** 系統回明確錯誤（未定義前綴 `role.`，必須為 `participant.` 或 `target.`），不靜默誤判。

---

### User Story 3 - 公開 URL 用 participant（Priority: P3）

行政預覽個別結果的 URL 由 `/match/{id}/role/{role_id}` 改為 `/match/{id}/participant/{participant_id}`；簽章 token 連結 `/r/{token}` 不受影響（token 內承載的是資料、不在路徑字面）。

**Why this priority**: URL 字面是最表層的一致性；功能上 token 路徑才是當事人主要入口，不受此影響。

**Independent Test**: 以擁有者身分 GET 新 URL 回 200；token 連結 `/r/{token}` 與其 audit/pdf 子路徑照常運作。

**Acceptance Scenarios**:

1. **Given** 一筆成功配對，**When** 擁有者開 `/match/{id}/participant/{pid}`，**Then** 顯示該參與者的個別查詢頁。

---

### Edge Cases

- **舊 audit/紀錄（v1.4，含 `roles`/`role_id`）**：採乾淨切斷——不保證可讀；沿用先前「升級清空舊資料」決議。viewer 不需向後相容 v1.4。
- **舊自訂範本含 `role.` 規則**：載入時對 `role.` 前綴回明確「未知前綴」錯誤（與既有未知前綴錯誤同路徑），不靜默通過。
- **舊 `/match/{id}/role/{role_id}` URL**：不保留重導向（乾淨切斷）；外部若有人存舊連結會 404，可接受。
- **CSV/Excel 匯入**：匯入欄位對齊靠模板屬性 schema（中文/英文別名），與 `role` 字樣無關，行為不變。

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: 系統 MUST 將 Python 內部識別碼 `Role`→`Participant`、`roles`→`participants`、`role_id`→`participant_id`、`role_attrs`/`role_field` 等對應更名，涵蓋核心與 web 層。
- **FR-002**: audit schema MUST 將 subject 側鍵更名（`roster_snapshot.roles`→`participants`、`allocation_trace[].role_id`→`participant_id`、`rules_snapshot` 內 `role.` 引用等），並升 `audit_schema_version` 由 `1.4` 至 `1.5`。
- **FR-003**: 範本規則 DSL MUST 以 `participant.` 取代 `role.` 作為 subject 側欄位前綴；parser 對 `role.` 前綴 MUST 回明確未知前綴錯誤（不向後相容）。
- **FR-004**: 兩個內建範本（teacher-class、study-group）、授權指南 `docs/template-authoring-guide.md`、表單建立器（template_form）、AI prompt 範例 MUST 同步改用 `participant.`。
- **FR-005**: 公開 URL MUST 由 `/match/{record_id}/role/{role_id}` 改為 `/match/{record_id}/participant/{participant_id}`（含 audit.json、report.pdf 子路徑）；`/r/{token}` 系列維持不變。
- **FR-006**: 全部 7 個 golden audit MUST 以新 schema 重生；同 seed 同輸入 bytewise 可重現 MUST 維持。
- **FR-007**: 全套件（含既有測試與本 feature 新增/調整測試）MUST 綠。
- **FR-008**: 對外顯示文字 MUST 維持「參與者 ↔ 對象」（本 feature 不改 UI 中文用字，017 已完成）。

### Key Entities

- **Participant（原 Role）**：被配對／分配出去的個體（老師、學生、幹部）。屬性 schema、preferences、id。對外英文識別碼 `participant`，中文「參與者」。
- **Target（對象，不變）**：被分配進去的標的（班級、組別、職位），有容量。
- **Audit record（v1.5）**：稽核紀錄；subject 側鍵改名，schema 版本升 1.5。
- **Rule expression DSL**：`participant.<attr>` / `target.<attr>` 兩種前綴。

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `grep -rn '\brole' src/matcher`（排除 specs/ 歷史、字串中合理殘留）無 subject 側識別碼殘留；audit 與 DSL 不再出現 `role`。
- **SC-002**: 全部 7 個 golden 以 v1.5 重生後，全套件綠（含可重現性 bytewise 測試）。
- **SC-003**: 同一份輸入 + 同 seed 跑兩次，audit 逐位元組相同（原則 2）。
- **SC-004**: 含 `role.` 前綴的範本載入 → 明確錯誤訊息（非靜默或 500）。
- **SC-005**: core 變動範圍可被一句話說明＝「subject 側更名」，無夾帶其他能力變更（教訓 7）。

## Assumptions

- 沿用既有決議「升級清空舊資料」：無需為舊 v1.4 audit / 舊 `role.` 範本 / 舊 URL 做向後相容讀取或重導向。
- 本 feature 接續在 017 分支（含「角色→參與者」UI 用字）之上，否則用字會不一致。
- `specs/**` 歷史規格不在更名範圍（point-in-time 紀錄）。
- 對象側 `target`（對象）維持不變；本 feature 只動 subject 側。
- 環境以 uv 管理（沿用）。

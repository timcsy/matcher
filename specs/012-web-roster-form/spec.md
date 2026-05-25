# Feature Specification: Web UI 直接填名單（與必要時填對象）

**Feature Branch**: `012-web-roster-form`
**Created**: 2026-05-25
**Status**: Draft
**Input**: User description: "Web UI 直接填名單：/match/new 加「直接填名單」入口；依範本動態渲染角色欄位+加減行；範本無 default_targets 時 UI 也能填對象（同頁兩段）；M0 直接跑、M1/M2 沿用 4d hidden inputs 路徑銜接填志願頁；audit 與 CSV 上傳路徑 bytewise 等價；核心 0 改動；UI 完全沿用既有 Alpine+Tailwind pattern。"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — 行政在 UI 上填寫小型名單跑配對（Priority: P1）🎯 MVP

學校行政想跑一次 7 位老師的「教師-班級配對」，不想做 CSV。在 `/match/new` 看到三選一：「📂 上傳名單檔 / ✏️ 直接填名單 / 📌 從過去紀錄」。選「直接填名單」+ teacher-class 範本 → 跳填寫頁：依範本自動渲染表單，每位老師一列含**姓名 / 老師專業科目 / 年資（年）**三欄；可加減行；填完選機制（純抽籤）→ 點「執行配對」→ 跳結果頁。

**Why this priority**：直接面對 vision 核心想法「**讓學校行政能在 30 分鐘內完成一次有公信力的配對**」——CSV 是行政未必擅長的工具，UI 填寫降到「跟 Google 表單一樣」的門檻。

**Independent Test**：選 teacher-class 範本 + 填 7 位老師（姓名/專業/年資）+ M0 → 跑通到結果頁，分配表正常顯示。

**Acceptance Scenarios**：

1. **Given** `/match/new` 頁面，**When** 載入，**Then** 顯示三個並列選項：「📂 上傳名單檔」「✏️ 直接填名單」「📌 從過去紀錄」（後者為連結到 `/matches`）。
2. **Given** 選範本 teacher-class + 點「✏️ 直接填名單」，**When** 跳填寫頁，**Then** 表單依範本「角色資料欄位」動態渲染——每列含 3 欄輸入（姓名 / 老師專業科目 / 年資（年））+ 移除按鈕；下方有「＋新增一位」按鈕。
3. **Given** 填寫頁，**When** 點「＋新增一位」5 次，**Then** 7 列空白角色出現（初始 2 列 + 5 次新增）。
4. **Given** 填了 7 位完整資料 + 選 M0，**When** 點「執行配對」，**Then** 系統跑 pipeline → 跳結果頁、`audit.mechanism == "M0"` + assignment 含 7 位。
5. **Given** UI 填的同樣 7 位老師，**When** 與「同樣資料以 CSV 上傳」對比，**Then** audit 五段（qualified_set / assignment / filter_trace / allocation_trace / template_snapshot）逐位元組相同。

---

### User Story 2 — 自訂範本無 `default_targets` 時，UI 也能填對象（Priority: P2）

行政建了自訂範本（feature 011），範本本身沒有預設對象（因為對象每年都不同）。選此範本 + ✏️ 直接填名單 → 填寫頁同時顯示「角色清單」+「對象清單」兩段；都填完才能跑配對。

**Why this priority**：feature 011 拿掉了「建範本時填預設對象」UI（合理——對象每年不同），但配對時要從哪來？此 user story 補上：UI 跑配對時填對象。

**Independent Test**：選某自訂範本（無 default_targets）+ UI 填 5 位角色 + 填 3 個對象 → 跑通 M0 → 結果頁。

**Acceptance Scenarios**：

1. **Given** 範本無 `default_targets`，**When** 進填寫頁，**Then** 同頁顯示兩段「① 角色清單」+「② 對象清單」，對象段依範本「對象資料欄位」動態渲染欄位（含 `代號 / 容量 / 各對象屬性`）。
2. **Given** 範本有 `default_targets`（如內建 teacher-class），**When** 進填寫頁，**Then** 只顯示「角色清單」段；對象段隱藏（隱含使用範本的 default_targets）。
3. **Given** 對象段填了 3 個（含代號 / 容量 / 屬性），**When** 跑配對，**Then** 跑通 + audit.roster_snapshot.targets 含此 3 個對象。

---

### User Story 3 — 接續填志願（M1/M2 + 範本有 preferences_schema）（Priority: P3）

範本宣告 `preferences_schema` 時，UI 填名單後若選 M1/M2 → 跳到 feature 009 的「填志願頁」（沿用既有 4d 機制）。

**Why this priority**：與 feature 009/4d 對齊。使用者選 M1/M2 但 UI 填名單沒填志願，要有自然延續。

**Independent Test**：自訂範本含 `preferences_schema` + UI 填 5 位 + 選 M1 → 跳填志願頁（feature 009）→ 填志願 → 跑通。

**Acceptance Scenarios**：

1. **Given** 範本含 `preferences_schema` + UI 填好角色（無 prefs 欄位）+ 選 M1，**When** 點「執行配對」，**Then** 系統跳到 `/match/preferences` 填志願頁（feature 009 既有），且名單已預載（hidden inputs 攜帶）。
2. **Given** 範本無 `preferences_schema` + 選 M1/M2，**When** 點執行，**Then** 沿用既有 `MechanismRequiresPreferences` 拒絕路徑。

---

### Edge Cases

- **使用者填一半離開**：草稿不儲存（同 4d 決策；UI 顯示提示「離開不會儲存」）
- **角色重複 id**：若使用者填了重複 id → 後端拒絕（PreferencesNotSupported 之外另一種 error）or 自動產生 id（沿用 CSV path 行為，無 id 欄則自動 R001/R002...）
- **必填欄位空白**：HTML5 `required` 屬性 + 後端二次驗證
- **規模 ≥ 20**：UI 仍可運作；POST body 在 FastAPI 預設 limit 內；若超 50 顯示提示「建議改用 CSV 上傳」
- **list_str 類型欄位**：UI 用「多筆文字以分號分隔」單行 input（簡化）；或用 multiple input（複雜）；MVP 採前者
- **範本既有 default_targets 但使用者想覆蓋**：MVP 不支援；想覆蓋請改範本或上傳 sidecar
- **填到一半切換範本**：先警告「會清掉目前填的資料」

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**：`/match/new` MUST 顯示三選一：「📂 上傳名單檔」「✏️ 直接填名單」「📌 從過去紀錄」並列。
- **FR-002**：選「✏️ 直接填名單」MUST 跳至填寫頁（同 URL 或 `/match/new/fill?template_id=X`）；表單依範本「角色資料欄位」動態渲染對應數量的輸入欄位。
- **FR-003**：填寫頁 MUST 支援動態加減角色行（沿用 feature 011 Alpine pattern）。
- **FR-004**：範本**有** `default_targets` 時，填寫頁 MUST **不**顯示對象段。
- **FR-005**：範本**沒有** `default_targets` 時，填寫頁 MUST 顯示「對象清單」段，依範本「對象資料欄位」渲染動態行。
- **FR-006**：使用者送出後，系統 MUST 將表單資料組裝為 `Roster` dataclass（含 roles 與 targets）並走既有 pipeline，產出與「同樣資料以 CSV 上傳」**bytewise 等價的 audit**。
- **FR-007**：UI 填名單 + 選 M0 → 直接跑 pipeline → 跳結果頁。
- **FR-008**：UI 填名單 + 選 M1/M2 + 範本有 `preferences_schema` → MUST 跳轉到 `/match/preferences`（feature 009 既有頁），透過 hidden inputs 攜帶名單（沿用 4d 機制）。
- **FR-009**：UI 填名單 + 選 M1/M2 + 範本無 `preferences_schema` → MUST 沿用既有 `MechanismRequiresPreferences` 拒絕路徑。
- **FR-010**：本 feature MUST 不動核心模組（`src/matcher/{rules,filter,allocator,pipeline,audit,errors,data_import,template_loader,rng,roster}`）；所有變更限於 `src/matcher/web/`。
- **FR-011**：所有 UI 文案 MUST 通過技術詞零容忍正則（沿用 4c/4d/4e 清單）。
- **FR-012**：階段 1-4e 既有 322 個自動化測試 MUST 100% 繼續通過。
- **FR-013**：本 feature **無**新依賴（Alpine + Tailwind + Python 既有皆已具備）。
- **FR-014**：UI 上 `list_str` 類型欄位以「多筆文字以分號分隔」單行 input 呈現（MVP）；UI 提示說明「以分號分隔，如：國文;數學」。

### Key Entities

- **`/match/new` 三選一 radio**：unified 入口；Alpine state `mode = "upload" | "fill" | "from-record"`；對應顯示不同區塊。
- **UI-filled Roster 表單**：表單欄位以 `role_<i>_<key>` / `target_<j>_<key>` 命名（與 feature 009 的 `pref_<id>_<rank>` 同 pattern）；後端用 `request.form()` + 動態欄位蒐集。
- **動態欄位渲染來源**：選定範本的 `attributes.roles` / `attributes.targets`（含 `key`、`type`、`description`、`required`）。
- **過渡狀態（M1/M2）**：填完名單後若需填志願，hidden inputs 攜帶 `template_id` + `mechanism` + `seed` + `roster_bytes_b64`（將 UI 填寫的資料轉成 CSV bytes + base64 編碼）→ POST 到 `/match/preferences`（feature 009）。

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**：使用者在 `/match/new` 選「直接填名單」+ teacher-class 範本 → 填寫頁顯示「姓名 / 老師專業科目 / 年資（年）」三欄；填 7 位後跑通 → 結果頁。
- **SC-002**：UI 填名單產出的 audit 與「相同資料以 CSV 上傳」5 段 100% bytewise 等價。
- **SC-003**：自訂範本（無 default_targets）→ UI 顯示「對象清單」段並能填；填完跑通。
- **SC-004**：範本有 `preferences_schema` + 選 M1/M2 → 跳 `/match/preferences` 並預載名單（feature 009 既有頁）；填志願後跑通。
- **SC-005**：範本無 `preferences_schema` + 選 M1/M2 → 沿用既有拒絕路徑。
- **SC-006**：核心模組 0 改動（git diff src/matcher/{rules,filter,allocator,pipeline,audit,errors,data_import,template_loader,rng,roster} 為空）。
- **SC-007**：階段 1-4e 既有 322 個自動化測試 100% 繼續通過。
- **SC-008**：本 feature 新增 ≥ 10 個自動化測試（UI 渲染、加減行、M0 流程、M1 銜接、Web/CSV bytewise 等價、對象填寫、規模測試、技術詞驗證）。
- **SC-009**：UI 文案 100% 通過技術詞零容忍正則。
- **SC-010**：填寫頁能處理 20+ 角色不卡頓；表單 POST body 不撞 FastAPI 預設 limit。

## Assumptions

- **無新依賴**：Alpine + Tailwind + python-multipart + jinja2 皆已具備。
- **填寫頁路徑**：MVP 用 `/match/new` 同頁切換（Alpine state）；不開新 URL。
- **對象段預設隱藏邏輯**：依範本 `default_targets` 是否存在自動判定；不提供「override 預設對象」選項（簡化 MVP）。
- **M1/M2 銜接機制**：沿用 feature 009 的 `/match/preferences` 路徑；本 feature 在 UI 提交時將表單轉為 CSV bytes（in-memory）+ base64 → 走 4d 既有 hidden inputs 路徑（避免重複實作）。
- **規模限制**：建議 ≤ 50 筆；UI 不阻擋但顯示提示「建議改用 CSV 上傳」。
- **list_str 簡化**：UI 以「分號分隔單行 input」處理（與 feature 011 同方式）。
- **id 自動生成**：使用者不填 role.id 時，後端自動生成 R001、R002...（沿用 CSV path 行為）。
- **草稿不儲存**：填一半離開即丟（與 4d/009 一致）。
- **不處理**：
  - 從 CSV 預載再 UI 編輯（混合輸入）
  - 草稿儲存 / 半填繼續
  - 名單持久化
  - 對象覆蓋（範本 default_targets 已決定就用，不允許 UI override）
  - 多範本同時填寫（一次只一範本）
  - PDF 匯出新格式（沿用既有）

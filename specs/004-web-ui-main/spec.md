# Feature Specification: Web UI 主流程

**Feature Branch**: `004-web-ui-main`
**Created**: 2026-05-22
**Status**: Draft
**Input**: User description: "Web UI 主流程：學校行政在瀏覽器選模板、上傳名單、設定 seed、執行媒合、查看結果並下載稽核紀錄。本 feature 為階段 3a，僅做主流程；個別查詢（3b）與 PDF 匯出（3c）拆為後續 feature。重用 src/matcher/ 既有 library；無 auth、媒合紀錄持久化於 data/matches/*.json。"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — 行政完成一次完整媒合（Priority: P1）🎯 MVP

學校行政打開瀏覽器，從首頁進入「新建媒合」流程：選擇一個內建模板（例如「教師-班級配對」）、上傳已準備好的 CSV/Excel 名單檔、輸入一個整數種子、按下「執行媒合」。瀏覽器在數秒內顯示分配結果（哪位老師 → 哪個班級）與資格集合摘要；頁面下方有「下載稽核紀錄」按鈕可取回完整 audit JSON。

**Why this priority**：本 user story 直接對應 vision「核心想法」：「讓學校行政能在 30 分鐘內完成一次有公信力、爭議發生時能拿出紀錄的角色屬性媒合」。沒有此路徑跑通，整個專案至此累積的引擎與模板無法被非技術使用者所用。

**Independent Test**：找一位**未參與開發**的學校行政，給予 5 分鐘介面導覽後請其獨立完成「上傳一份 CSV、跑出結果、下載 audit」的全流程；若能在 30 分鐘內完成且 audit 內容與 CLI 等價，視為通過。

**Acceptance Scenarios**：

1. **Given** 瀏覽器位於首頁、CSV 名單已備妥（含 id、姓名、專業科目、年資欄位），**When** 使用者點「新建媒合」→ 選「教師-班級配對」模板 → 上傳 CSV → 輸入 seed 123456 → 點「執行媒合」，**Then** 5 秒內顯示「結果頁」含分配表（角色 → 對象）、資格集合大小、所用 seed、稽核下載連結。
2. **Given** 結果頁已顯示，**When** 使用者點「下載稽核紀錄」，**Then** 瀏覽器下載一份 audit JSON；以同樣輸入透過 CLI 跑出的 audit 與此檔在五個核心欄位（qualified_set、assignment、filter_trace、allocation_trace、template_snapshot）逐位元組相同。
3. **Given** 名單檔含模板未宣告的欄位（如「備註」），**When** 上傳，**Then** 系統忽略未知欄位並完成媒合（不報錯——與 CLI 行為一致）。
4. **Given** 名單檔缺必填欄位（如缺「專業科目」），**When** 上傳，**Then** 結果頁顯示明確繁中錯誤訊息含「缺欄位 `speciality`（可用別名：專業科目、專業）」與「請補上後重新上傳」按鈕。

---

### User Story 2 — 模板瀏覽與選擇（Priority: P2）

使用者能從「模板列表」頁瀏覽所有內建模板（含名稱、一句話描述）；點任一模板進入「模板詳情」頁，看到完整的屬性 schema、規則的自然語言說明、UI 欄位宣告、是否含 preferences schema。從詳情頁可直接「使用此模板新建媒合」進入主流程。

**Why this priority**：原則 1「屬性與規則必須可解釋」在 UI 層的具體實現；行政在執行媒合前能完整檢視「這個模板會用什麼規則篩、會怎麼配對」。

**Independent Test**：在模板列表頁應看到 teacher-class、study-group 兩個內建模板；點 teacher-class 進入詳情頁，應能讀到 R001/R002/R003 三條規則的繁中說明、姓名/專業科目/年資三個屬性宣告（含中文 aliases）。

**Acceptance Scenarios**：

1. **Given** 系統有內建模板，**When** 使用者訪問「模板列表」頁，**Then** 列表顯示所有可用模板的 id、名稱、一句話描述（繁中）。
2. **Given** 模板詳情頁，**When** 使用者瀏覽，**Then** 頁面顯示：基本資訊、屬性 schema（roles 與 targets 兩段，含中文別名）、規則清單（id + 自然語言說明）、UI 欄位宣告（若有）、preferences schema（若有，標註「未來機制使用、本階段不啟用」）。
3. **Given** 詳情頁的「使用此模板新建媒合」按鈕，**When** 點擊，**Then** 進入「新建媒合」流程且模板已預選。

---

### User Story 3 — 媒合紀錄瀏覽與重新查看（Priority: P3）

每次成功的媒合會被持久化儲存；使用者可從「過去媒合」頁瀏覽最近的媒合紀錄（時間、模板名、seed、狀態），點任一筆可重新檢視該次媒合的結果頁（含下載 audit）。

**Why this priority**：原則 4「結果可稽核」在 UI 層的延伸——爭議發生時，行政能立即找到過去某次媒合並再次提供稽核紀錄。

**Independent Test**：執行 ≥ 3 次媒合後，「過去媒合」頁應顯示 ≥ 3 筆紀錄；點最舊的一筆能還原當時的結果頁與 audit。

**Acceptance Scenarios**：

1. **Given** 系統已執行過 ≥ 1 次媒合，**When** 使用者訪問「過去媒合」頁，**Then** 列表顯示最近 50 筆媒合（依時間遞減），含時間、模板名、seed、狀態（成功 / 失敗 + 錯誤類型）。
2. **Given** 過去媒合列表，**When** 點某筆成功紀錄，**Then** 重新顯示該次的結果頁，與當時 audit 內容完全一致。
3. **Given** 過去媒合列表，**When** 點某筆失敗紀錄，**Then** 顯示當時的錯誤訊息與輸入摘要，協助使用者理解失敗原因。

---

### Edge Cases

- **上傳檔過大**：限制 ≤ 5 MB；超過 → 明確繁中錯誤。
- **檔案格式錯誤**：MIME 不在 csv/xlsx 白名單 → 明確繁中錯誤。
- **同時多人操作**：v1 假設單機 / LAN 信任環境，無 race condition 處理；媒合紀錄檔名含時間戳 + UUID 避免覆寫。
- **seed 非整數**：表單前端驗證 + 後端拒絕。
- **媒合紀錄目錄不存在**：第一次執行時自動建立 `data/matches/`。
- **CLI 與 Web 並行**：CLI 跑的媒合**不會**進入 Web 的「過去媒合」列表（兩條獨立通道；Web 列表只反映 Web 入口的紀錄）。
- **既有 CLI 介面**：本 feature 不改 CLI；`matcher run` / `matcher template` / `matcher filter` 行為完全不變。

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**：系統 MUST 提供瀏覽器可訪問的 Web 介面，繁中。
- **FR-002**：首頁 MUST 提供至少三個入口：「新建媒合」、「模板列表」、「過去媒合」。
- **FR-003**：「新建媒合」流程 MUST 包含四步驟：(a) 選模板、(b) 上傳名單檔（CSV/Excel）、(c) 輸入 seed、(d) 執行並顯示結果。可採向導（wizard）或單頁均可，依 UI 設計決定。
- **FR-004**：系統 MUST 重用既有 `src/matcher/` library（`load_roster_csv` / `load_roster_xlsx` / `run_match`），不重寫媒合邏輯。
- **FR-005**：模板列表頁 MUST 列出所有內建模板的 id、名稱、一句話描述；點任一模板進入詳情頁。
- **FR-006**：模板詳情頁 MUST 顯示模板的完整內容（attributes / rules / ui_fields / report_fields / preferences_schema），所有可閱讀文字為繁中。
- **FR-007**：結果頁 MUST 顯示：模板基本資訊、所用 seed、資格集合大小、最終配對表（含角色顯示名稱與對象顯示名稱）、稽核紀錄下載連結。
- **FR-008**：「下載稽核紀錄」MUST 提供與 CLI 路徑等價的 audit JSON 檔（核心五段逐位元組相同）。
- **FR-009**：所有匯入錯誤（編碼、欄位缺失、型別、工作表歧義）MUST 在結果頁以明確繁中錯誤訊息呈現，沿用既有 4 個錯誤類別。
- **FR-010**：preferences 在 M0 機制下的拒絕邏輯（沿用階段 1）MUST 在 Web 介面上產生對應錯誤訊息，並提示「志願序機制將於階段 4 啟用」。
- **FR-011**：系統 MUST 將每次媒合（成功或失敗）持久化儲存於 `data/matches/<timestamp>-<uuid>.json`；檔案內容含 audit（成功時）或錯誤詳情（失敗時）+ metadata（執行時間、模板 id、seed、輸入檔案名）。
- **FR-012**：「過去媒合」頁 MUST 顯示最近 ≥ 50 筆媒合（時間遞減），含時間、模板名、seed、狀態。
- **FR-013**：點過去媒合的單筆紀錄 MUST 還原當時的結果頁；下載的 audit 內容與當時逐位元組相同。
- **FR-014**：「機制」選擇 UI 元素 MUST 存在但只有 M0 為可選；M1/M2 顯示為 disabled 並附「將於階段 4 啟用」說明。
- **FR-015**：preferences 欄位在「新建媒合」流程中**不顯示為可填寫欄位**（避免引誘使用者填）；若上傳的名單檔含非空 preferences 仍走 PreferencesNotSupported 拒絕路徑。
- **FR-016**：上傳檔大小 MUST 限制在 ≤ 5 MB；MUST 限制 MIME 為 `text/csv` 與 `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`；超出 → 明確錯誤。
- **FR-017**：本 feature MUST 不引入任何認證 / 授權機制（v1 假設單機 / LAN 信任）。
- **FR-018**：本 feature MUST 不改既有 CLI 介面；既有 116 個自動化測試 100% 繼續通過。
- **FR-019**：Web UI 主要面向「學校行政」與「一般教師」；MUST 避免技術術語（如「seed」可顯示為「隨機種子」並附簡短說明）；MUST 提供至少一個「範例資料」連結讓使用者下載既有 examples/* 作為起點。
- **FR-020**：每個 HTTP 端點 MUST 在錯誤時返回繁中錯誤訊息與適當的狀態碼（400 使用者輸入錯誤 / 500 系統內部錯誤）。

### Key Entities

- **媒合執行紀錄（Match Record）**：每次「新建媒合」的完整紀錄；含 id（時間戳+UUID）、模板 id、seed、輸入檔案 basename、執行時間、結果狀態（成功 / 失敗）、audit（成功時）或錯誤詳情（失敗時）。
- **媒合紀錄儲存（Match Store）**：持久化於 `data/matches/*.json` 的紀錄集合；本 feature 提供「列表最近 N 筆」與「依 id 取單筆」兩個操作。
- **HTTP 端點**：列表 / 詳情 / 上傳 / 執行 / 下載 等對應 user story 的介面，本 feature 一律無 auth。

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**：「未參與開發的學校行政」在 5 分鐘介面導覽後，能在 **30 分鐘內**獨立完成「上傳 CSV → 跑出結果 → 下載 audit」全流程（vision 核心想法的具體驗證）。
- **SC-002**：結果頁顯示與「按下執行」之間的時間 ≤ **5 秒**（教師-班級基準場景，10 老師 5 班）。
- **SC-003**：Web 路徑下載的 audit JSON 與 CLI 同樣輸入跑出的 audit 在 5 個核心欄位（qualified_set、assignment、filter_trace、allocation_trace、template_snapshot）**100% 逐位元組相同**。
- **SC-004**：模板列表頁列出 ≥ 2 個內建模板；詳情頁展示完整內容。
- **SC-005**：「過去媒合」頁能顯示最近 ≥ 50 筆紀錄；點任一筆能重現該次結果。
- **SC-006**：4 種匯入錯誤情境（編碼、欄位、型別、工作表）皆在 UI 上顯示明確繁中錯誤訊息（0% 靜默通過）。
- **SC-007**：在 M0 機制下上傳含非空 preferences 的名單 → UI 100% 顯示「不接受志願輸入 / 階段 4 啟用」訊息。
- **SC-008**：階段 1+2a+2b 既有 116 個自動化測試 100% 繼續通過；本 feature 額外新增 ≥ 15 個 HTTP 端點層級的整合測試。
- **SC-009**：UI 任一頁面**完全**不出現英文技術術語（除了 CLI 命令範例段落）；所有按鈕、提示、錯誤訊息為繁中。
- **SC-010**：上傳檔 > 5 MB 或 MIME 不符 100% 被拒；無系統內部錯誤暴露給使用者。

## Assumptions

- **網頁框架方向**：採 server-rendered HTML（非單頁式 SPA）；具體技術選型由 `/speckit.plan` 決定（傾向 FastAPI + HTMX + Jinja2，沿用 Python 生態避免 Node toolchain；簡潔優先）。
- **儲存**：媒合紀錄為純檔案系統 JSON（`data/matches/<timestamp>-<uuid>.json`）；不引入 SQLite / PostgreSQL（簡潔優先）。
- **部署**：本 feature 假設單機執行（`matcher serve` 命令啟動本地 server）；K8s 部署為階段 5。
- **無 auth**：v1 假設使用者在 LAN 內信任環境；登入、權限、多使用者皆不處理。
- **上傳檔保留**：暫存於記憶體或 OS 暫存區，**不**長期保留；audit 中的 roster_snapshot 已含完整結構化資料，無需保留原始上傳檔。
- **靜態資源**：CSS / JS 採極簡風格、極少量；無需打包工具。
- **瀏覽器相容**：目標為近 2 年內主流瀏覽器（Chrome / Firefox / Edge / Safari）；不支援 IE。
- **真實使用者測試（SC-001）**：本 feature 完成後須與真實學校行政實測一次；不在自動化測試中強行模擬。
- **不處理**：
  - 個別查詢視圖（被媒合者「為什麼我被/沒被抽到」）→ feature 005
  - PDF 報告匯出 → feature 006
  - 動態調整既有媒合結果（vision 範圍邊界已排除）
  - 模板編輯介面（v1 只接受內建 + 上傳模板檔）
  - M1/M2 機制選擇（階段 4）
  - 多人協作、即時通知
  - i18n（本階段繁中為唯一語系）

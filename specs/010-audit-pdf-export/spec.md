# Feature Specification: 稽核報告 PDF 匯出

**Feature Branch**: `010-audit-pdf-export`
**Created**: 2026-05-24
**Status**: Draft
**Input**: User description: "稽核報告 PDF 匯出：admin 結果頁與個別查詢頁皆可下載 PDF；用 WeasyPrint 渲染既有 jinja2 樣板；嵌入 Noto Sans CJK TC 字體；弱可重現性（內容相同；audit JSON 仍是 bytewise 權威）；CLI 提供 matcher report 指令。核心 0 改動；技術詞零容忍延伸至 PDF 文案。"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — 行政下載 admin 結果 PDF 存檔（Priority: P1）🎯 MVP

學校行政在 Web 上跑完一次媒合後，於結果頁點「下載 PDF 報告」按鈕，下載一份 A4 列印格式的稽核報告。報告含：標題（媒合報告 + 模板名）、紀錄編號、時間、模板名稱、機制、隨機種子、處理順序段（M1/M2）、完整分配表（含志願排名欄）、簡明的稽核摘要說明。報告字體為嵌入式 Noto Sans CJK TC，中文顯示正常；可用 Adobe Reader / 系統預覽開啟。

**Why this priority**：原則 4「結果可稽核」明文「學校行政可匯出為稽核報告」——本 user story 把該語句落地為實體可印製的紙本。家長/教評委員/上級檢視場景強需「白紙黑字」的存檔形式。

**Independent Test**：跑一次媒合 → 結果頁點下載 → 取得 PDF 檔 → Adobe Reader 開啟 → 內容齊全、中文正常顯示。

**Acceptance Scenarios**：

1. **Given** 一次成功 M2 媒合的 record，**When** 行政點結果頁「下載 PDF 報告」，**Then** 取得 `<record_id>.report.pdf`（HTTP 200、Content-Type 為 PDF、Content-Disposition 為 attachment）、檔大小 ≤ 500 KB（不含 9 學生分配表的標準場景）。
2. **Given** 取得的 PDF，**When** 用 PDF 閱讀器打開，**Then** 第一頁含標題「媒合報告」+ 模板名稱、紀錄編號、時間、機制顯示名（如「M2 Boston 層級填滿」）、隨機種子、處理順序段（M1/M2 路徑）、分配表（含「志願排名」欄）。
3. **Given** 取得的 PDF 內含中文字元（「程式組」「您的第 1 志願」），**When** 用 PDF 閱讀器搜尋繁中關鍵字，**Then** 能成功搜尋到對應文字（字體嵌入正確）。
4. **Given** 失敗的 record（如 M1 + 全空 prefs 拒絕），**When** 點下載 PDF，**Then** 取得失敗版報告（標題「媒合報告（失敗）」+ 錯誤類別 + 訊息），HTTP 200。

---

### User Story 2 — 當事人下載個別 PDF 簽收（Priority: P2）

被媒合者（學生家長代收 / 教師本人）在個別查詢頁點「下載我的報告 PDF」，取得一份**只含自己資料**的 PDF：基本資訊、被分到哪個對象、第幾志願（M1/M2）、判定過程簡述。可印出簽收。

**Why this priority**：原則 5「對使用者透明」延伸到實體簽收場景；目前 individual JSON 下載對非技術背景使用者不友善。

**Independent Test**：跑一次 M1 媒合 → 開任一學生的個別查詢 URL → 點「下載我的報告」→ PDF 含該學生資料，不含其他學生 trace。

**Acceptance Scenarios**：

1. **Given** 一次成功 M1 record + 一位被分到第 1 志願的學生 role_id=S01，**When** 從個別查詢頁下載 PDF，**Then** PDF 含：標題「您的媒合結果」+ 學生姓名、被分到「程式組」、被分到第 1 志願、不含其他學生的姓名與分配資料。
2. **Given** PDF 文字內容，**When** 跑技術詞正則驗證（沿用 008 FORBIDDEN_TECHNICAL_TOKENS + 新增 `preference_rank` / `random_index` 等），**Then** 0 命中。
3. **Given** 失敗 record 的個別頁，**When** 嘗試下載個別 PDF，**Then** HTTP 404 + 友善訊息（沿用既有 individual_error.html 邏輯）。

---

### User Story 3 — CLI `matcher report` 指令（Priority: P3）

行政或自動化腳本可從 CLI 直接從 audit JSON 生 PDF，不必啟動 Web。

**Why this priority**：教訓 5「三入口共用核心」——library/CLI/Web 三入口應對等。Web 已能下載 PDF；CLI 應能對等。亦支援批次處理 / 排程匯出場景。

**Independent Test**：CLI 跑 `matcher report --audit cli-audit.json --output report.pdf` → 取得 PDF；其內容與 Web 下載的 PDF 內容相同（不要求 bytewise 同，但所有顯示欄位相同）。

**Acceptance Scenarios**：

1. **Given** 一份 audit JSON 檔，**When** 跑 `matcher report --audit <file> --output <pdf>`，**Then** 產出 PDF 含 admin 結果頁的所有欄位（如 US1）。
2. **Given** 同 audit JSON + 指定 `--role-id S01`，**When** 跑指令，**Then** 產出個別版 PDF（如 US2）。
3. **Given** 無效或缺欄位的 audit JSON，**When** 跑指令，**Then** exit code ≠ 0 + 明確繁中錯誤訊息（如「audit 缺欄位 `assignment`」）。

---

### Edge Cases

- **WeasyPrint 系統依賴缺失**（macOS / Linux 未裝 Pango）：應用啟動時即偵測並提示；render PDF 端點失敗時回 500 + 明確繁中錯誤「PDF 渲染失敗：缺少系統依賴 Pango/Cairo——請見 README 安裝指引」
- **PDF 大小極限**：50 學生 × 3 志願規模 → 預期 ~150 KB；100+ 學生若超 1 MB 可加分頁
- **字體找不到**：嵌入字體檔路徑錯誤 → 啟動時即偵測；render 失敗回 500 + 「字體檔遺失」訊息
- **失敗 record + 個別 PDF**：404（如 spec）
- **PDF 中文搜尋**：嵌入 Noto Sans CJK TC subset 應支援搜尋；用 ASCII-only 子集字體會讓中文變為 outline glyph、無法搜尋——須驗證
- **同 record 多次下載**：弱可重現性——時間戳 / `/CreationDate` metadata 可能不同；內容欄位（標題、分配表、姓名等）必相同
- **CLI audit 檔來自不同 schema 版本**：v1.0 / v1.1 / v1.2 / v1.3 皆應能渲染；舊版本路徑（無 `processing_order` 等）顯示為「（未紀錄）」或隱藏該欄

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**：結果頁（admin `match_result.html`）MUST 新增「下載 PDF 報告」按鈕；點擊呼叫 `GET /match/{rid}/report.pdf` 回 PDF（Content-Type: application/pdf、Content-Disposition: attachment）。
- **FR-002**：個別查詢頁（`individual_view.html`）MUST 新增「下載我的報告 PDF」按鈕；點擊呼叫 `GET /match/{rid}/role/{role_id}/report.pdf`。
- **FR-003**：admin PDF 內容 MUST 包含：標題、模板名、紀錄編號、時間、機制顯示名、隨機種子、（M1/M2 時）處理順序、分配表（含志願排名欄 M1/M2 時）。
- **FR-004**：individual PDF 內容 MUST 包含：標題「您的媒合結果」、學生姓名、分配對象、（M1/M2 時）第幾志願或「由公平抽籤分到」、判定過程簡述；MUST NOT 包含其他角色的資料。
- **FR-005**：PDF MUST 使用嵌入式中文字體（Noto Sans CJK TC，OFL 授權子集），保證任意機器渲染後中文顯示正常且**可搜尋**（非 outline glyph）。
- **FR-006**：失敗 record 的 admin PDF MUST 顯示「失敗版」（含錯誤類別 + 訊息）；失敗 record 的個別 PDF MUST 回 HTTP 404。
- **FR-007**：所有 PDF 文字 MUST 通過技術詞零容忍正則驗證——不可暴露 `preference_rank` / `random_index` / `processing_order` / `default_targets` / `preferences_schema` / `max_choices` / `filter_trace` / `allocation_trace` / `qualified_set` / `role\.\w+` / `target\.\w+` 等英文 token / pattern。
- **FR-008**：CLI MUST 新增 `matcher report --audit <file> [--role-id <id>] --output <pdf>` 指令；`--role-id` 缺省 → admin 版；有值 → individual 版。
- **FR-009**：CLI report 指令 MUST 在 audit JSON 無效或缺核心欄位時 exit code ≠ 0 + 明確繁中錯誤訊息。
- **FR-010**：同 record 兩次下載 PDF 的**內容欄位**（標題、表格內容、文字段）MUST 100% 相同；位元組可不同（時間戳 / metadata）。
- **FR-011**：本 feature MUST 不動核心模組（`src/matcher/{rules,filter,allocator,pipeline,audit,errors,data_import,template_loader,rng,roster}`）——所有變更限於 `src/matcher/web/` + CLI 新指令所在檔（如 `src/matcher/cli.py`，僅新增不修改既有命令；若必要 cli.py 修改視為「新入口」延伸，不視為「核心」改動）。
- **FR-012**：應用啟動時 MUST 偵測 WeasyPrint 系統依賴 + 字體檔可用性；若任一失敗，**仍可啟動 Web/CLI 既有功能**（PDF 端點 graceful degrade 為 503 / CLI report 指令拋友善錯誤）；不阻斷其他流程。
- **FR-013**：階段 1-4d 既有 256 個自動化測試 MUST 100% 繼續通過。
- **FR-014**：所有錯誤訊息、UI 文案、PDF 文案 MUST 為繁中（沿用 constitution）。

### Key Entities

- **PDF 報告檔**：A4 列印格式；admin 版含完整分配表；individual 版只含當事人；字體嵌入 Noto Sans CJK TC。
- **CLI report 指令參數**：`--audit <file>`（必填）、`--role-id <id>`（選填）、`--output <pdf>`（必填）。
- **PDF render 純函式**：以 audit dict + 可選 role_id 為輸入、PDF bytes 為輸出（library 化）。
- **Noto Sans CJK TC 字體子集**：放 `src/matcher/web/static/fonts/`，OFL 授權、~10MB；嵌入 PDF。

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**：行政在結果頁可下載 admin PDF；檔大小 ≤ 500 KB（9 學生標準場景）；Adobe Reader / 系統預覽可開啟；中文顯示正常且可搜尋。
- **SC-002**：當事人在個別查詢頁可下載 individual PDF；內容只含自己；MUST NOT 包含其他角色姓名（自動化測試守住）。
- **SC-003**：CLI `matcher report` 指令可從 audit JSON 產出 admin 或 individual PDF；exit code 0；產出 PDF 與 Web 下載的內容欄位 100% 相同。
- **SC-004**：所有 PDF 文字 100% 通過 FORBIDDEN_TECHNICAL_TOKENS 正則驗證（沿用 008+009 清單）。
- **SC-005**：同 record 兩次下載 PDF 的內容欄位 100% 相同（位元組可不同）。
- **SC-006**：50 學生 × 3 志願 標準場景的 admin PDF 渲染 ≤ 2 秒；檔大小 ≤ 1 MB。
- **SC-007**：階段 1-4d 既有 256 個自動化測試 100% 繼續通過。
- **SC-008**：核心模組（`src/matcher/{rules,filter,allocator,pipeline,audit,errors,data_import,template_loader,rng,roster}`）0 改動。
- **SC-009**：本 feature 新增 ≥ 10 個自動化測試（HTTP 整合 + PDF 內容斷言 + CLI 指令 + 技術詞驗證 + 失敗路徑 + 字體可搜尋驗證）。
- **SC-010**：WeasyPrint / 字體檔缺失時，PDF 端點 graceful degrade 為 503 + 明確繁中訊息；不阻斷既有 Web/CLI 功能（既有 256 測試仍綠）。

## Assumptions

- **新依賴**：`weasyprint >= 60.0`（Python 套件）+ Noto Sans CJK TC 字體檔（嵌入專案，~10MB OFL 授權）。
- **系統依賴**（README 補說明）：
  - macOS：`brew install pango`
  - Linux (Debian/Ubuntu)：`apt install libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b`
- **弱可重現性**：原則 2「分配過程必須可驗證且可重現」由 audit JSON 守住（bytewise 可重現）；PDF 只是人類友善呈現，**不**要求位元組同——時間戳、`/CreationDate` 等 metadata 可變。內容欄位 MUST 同。
- **核心 0 改動**：本 feature 屬「新呈現視圖」（PDF）+ 「新入口」（CLI report 子指令）——皆為周邊整合（教訓 7）；CLI 新增子指令但不改既有 `run` / `template` 等。
- **PDF 樣板**：新增 `src/matcher/web/templates/pdf/match_report.html`（A4 列印版，不重用 `match_result.html` 避免螢幕 / 印刷視覺混淆）；個別版用 `pdf/individual_report.html`。
- **字體嵌入策略**：使用 WeasyPrint 預設的 fontconfig 解析 + `@font-face` 在樣板 CSS 中引用本機字體檔；不依賴系統字體（避免「在某機器中文變問號」）。
- **不處理**：
  - PDF 客製化排版 / Logo 上傳（→ 未來）
  - 多語版 PDF（→ 未來）
  - 動 audit / record schema（FR-011）
  - PDF 簽章 / 浮水印 / 加密（→ 未來，如有法律存檔需求再做）
  - 批次匯出（行政在 UI 一次下載多份 PDF；CLI 已可 shell 迴圈）
  - audit schema 升版本——本 feature 完全讀取既有 v1.3 audit
  - PDF reproducibility 位元組級（弱要求）
  - 圖表 / 視覺化（如分配長條圖；先做純文字表格）

# Feature Specification: 模板創作工具 UI（簡單 / 進階 / 編輯 / 版本歷史）

**Feature Branch**: `011-template-author-ui`
**Created**: 2026-05-25
**Status**: Draft
**Input**: User description: "模板創作工具 UI：簡單模式（表單導引）+ 進階模式（YAML 編輯器 + AI prompt），編輯內建模板需 fork，自訂模板支援版本歷史（每 save = 新版本），媒合紀錄頁可「以此版本再執行」。持久化到 data/templates/<id>/v<N>.yaml；TemplateRegistry 加掃描自訂目錄。算核心職責擴充（教訓 7 第 3 種合法情境）。"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — 簡單模式建立新模板（Priority: P1）🎯 MVP

學校行政（非工程師）在 `/templates` 頁點「新增模板」→ 進到 `/templates/new`。預設「簡單模式」頁籤：

1. 從「**場景樣板**」下拉選一個起點（如「空白」「社團報名」），系統預填常見欄位
2. 填基本資訊（id、name、description）
3. 在「角色屬性表格」動態加減行（key/type/required/中文 description/aliases）
4. 同樣填「對象屬性表格」
5. 加多張「**規則卡片**」，每張選類型（5 種預設規則類型之一），系統依使用者填入的欄位自動生成 description
6. 填「預設對象表格」（id/capacity/各屬性）
7. （可選）勾選「啟用志願」+ 填 max_choices
8. 點「**驗證**」→ 顯示 success 或繁中錯誤訊息
9. 點「**儲存**」→ 寫入 `data/templates/<id>/v1.yaml`；下次重新整理 `/templates` 與 `/match/new` 即出現此模板

**Why this priority**：vision 階段 4e/4f 核心交付——讓非工程師能在 UI 上產出可用模板。完成後「30 分鐘行政實測」可涵蓋「自製場景」的真實情境。

**Independent Test**：在新空白瀏覽器 session 中，從零建立一個「社團報名」模板（3 屬性、2 規則、3 default_targets），儲存後到 `/match/new` 下拉應出現此模板；用它跑一次媒合成功。

**Acceptance Scenarios**：

1. **Given** `/templates/new` 簡單模式 + 場景樣板選「社團報名」，**When** 頁面載入，**Then** 預填 3 個常見角色屬性（name/grade/interest）+ 3 個對象屬性 + 2 個範例規則。
2. **Given** 簡單模式 + 規則卡片選「角色 X 必須 ≥ Y」，**When** 填入 `role.grade ≥ 4`，**Then** 系統自動寫入 description「角色年級必須 ≥ 4」（可後續編輯）。
3. **Given** 表單填完 + 驗證通過，**When** 點儲存，**Then** 系統建立 `data/templates/club/v1.yaml`、跳到 `/templates/club` 顯示新模板，且 `/match/new` 下拉立即出現「社團報名（club）」。
4. **Given** id 與既有模板（內建或自訂）衝突，**When** 點儲存，**Then** 顯示繁中錯誤「模板 id 已存在；請改名或選擇 fork 現有模板」。

---

### User Story 2 — 進階模式建立模板（YAML 編輯器 + AI prompt）（Priority: P2）

熟悉 YAML 的使用者（或想用 AI 助手的）切到「進階模式」頁籤：

1. 上半填空格（場景描述 / 角色 / 對象 / 規則 / 志願與否），點「**複製完整 Prompt**」→ JS 複製內含整份 `docs/template-authoring-guide.md` + 填空後的 prompt 到剪貼簿
2. 把 prompt 貼給 Claude/ChatGPT，AI 回 YAML
3. 把 AI 回的 YAML 貼回頁面下半的大文字框
4. 點「驗證」→ 同上
5. 點「儲存」→ 同上

**Why this priority**：覆蓋「需要複雜規則 (and/or/not 巢狀)」「想用 AI 加速」的進階使用者。簡單模式不支援 and/or/not，這是「complex 場景出口」。

**Independent Test**：複製進階模式生的 prompt 給 ChatGPT、貼回 YAML、驗證成功、儲存。

**Acceptance Scenarios**：

1. **Given** 進階模式頁籤，**When** 點「複製完整 Prompt」，**Then** 剪貼簿內容含 `docs/template-authoring-guide.md` 整份文字 + 使用者填入的場景描述。
2. **Given** YAML 文字框貼入合法模板 YAML，**When** 點驗證，**Then** 顯示 ✅ 含「模板 id、名稱、屬性數、規則數」摘要。
3. **Given** YAML 文字框貼入有語法錯的 YAML（如 ge 用了非整數），**When** 點驗證，**Then** 顯示繁中錯誤訊息（如「規則 R001 的 ge 算子 value 必須為整數」）+ 不允許儲存。

---

### User Story 3 — 編輯既有模板 + 版本歷史（Priority: P3）

行政在 `/templates/<id>` 看到「**編輯**」按鈕（若該模板為自訂）。點擊 → 進 `/templates/<id>/edit`，**載入最新版本**內容到簡單/進階模式的表單/編輯器中 → 改 → 儲存 → 系統寫入 `v<N+1>.yaml`（N 為現有最大版本號）。

`/templates/<id>` 頁面顯示「版本歷史」表格：列出所有版本（v1、v2、v3...）、儲存時間、可點「查看此版本」展開該版的內容。

**內建模板限制**：`/templates/teacher-class`、`/templates/study-group` **無**「編輯」按鈕；改為「**Fork 為自訂模板**」按鈕——點擊後跳 `/templates/new` 並預填內建模板內容（含 ` -fork` 後綴的新 id 提示）。

**Why this priority**：實際使用後必然出現「我寫錯了規則想改」的需求；無編輯就要全部重來。版本歷史讓「改錯回不去」的恐懼消失（也是 audit 可追溯精神的延伸）。

**Independent Test**：建立 `myschool` v1 → 編輯 → 儲存為 v2 → `/templates/myschool` 顯示版本表格含 v1 / v2；點 v1 能看舊內容。

**Acceptance Scenarios**：

1. **Given** 自訂模板 `myschool` 已存在 v1，**When** 訪問 `/templates/myschool`，**Then** 頁面含「編輯」按鈕 + 版本歷史段（含 v1 + 儲存時間）。
2. **Given** 點「編輯」後改了 name 並儲存，**When** 重新整理 `/templates/myschool`，**Then** 版本歷史段含 v1 + v2；目前 active = v2。
3. **Given** 訪問 `/templates/teacher-class`（內建），**When** 載入，**Then** 頁面**無**「編輯」按鈕；有「Fork 為自訂模板」按鈕。
4. **Given** 點「Fork 為自訂模板」，**When** 跳到 `/templates/new`，**Then** 表單預填 teacher-class 的所有內容；id 預填為 `teacher-class-fork`（使用者可改）。

---

### User Story 4 — 從媒合紀錄「以此版本再執行」（Priority: P4）

行政在 `/match/<rid>`（任何過去媒合的結果頁）底部新增「**以此模板版本再執行**」按鈕。點擊：

1. 系統從 `record.audit.template_snapshot` 還原該模板 YAML
2. 跳到 `/match/new`，下拉預選此模板；模板若已不存在（被刪除）或版本不同（已更新），自動把 audit 的 snapshot 寫入一個臨時 `<id>-snapshot-<rid>` 版本，預選此臨時版本

**Why this priority**：原則 2「分配過程必須可驗證且可重現」的延伸——同 audit + 同 seed + 同模板 → 結果應可重現。**現在已是 audit-snapshot 的免費延伸**（audit 早就完整含 template_snapshot，只差 UI button）。

**Independent Test**：跑 M1 媒合 v1 → 編輯模板為 v2 → 在舊 record 頁點「以此版本再執行」→ 用 v1 跑新一次媒合（seed 可改）→ 結果與 v1 的歷史版本一致。

**Acceptance Scenarios**：

1. **Given** 過去成功媒合的 record，**When** 訪問結果頁，**Then** 頁面底部新增「以此模板版本再執行」按鈕（含模板 id + 顯示「v<N>」或「（snapshot）」標籤）。
2. **Given** 點此按鈕，**When** 跳到 `/match/new`，**Then** 模板下拉預選正確模板版本 + 顯示「已預載 audit 中的模板版本」提示。

---

### Edge Cases

- **內建模板與自訂模板 id 衝突**：自訂模板 id 與內建模板（teacher-class / study-group）相同時，儲存即拒絕；不允許「覆蓋內建」
- **同 id 已有 v1...vN，使用者編輯儲存**：自動寫 v(N+1)；不允許「指定版本號覆蓋」
- **YAML 語法錯誤（包括非法 expr 算子）**：驗證階段擋下；不允許儲存
- **儲存後重啟 server**：自訂模板需被 TemplateRegistry 載入；測試需含 server 重啟模擬
- **`data/templates/` 不存在**：第一次儲存時自動建立
- **進階模式貼入 YAML 但 id 與簡單模式表單中的 id 不一致**：以 YAML 內 id 為準（簡單模式表單在進階模式被忽略）
- **使用者把 v1 整個內容刪光只剩 `id:` 一行**：驗證階段擋下（缺必填欄位）
- **fork 內建模板後又改 id 為內建模板 id**：儲存拒絕（同上 id 衝突邏輯）
- **版本歷史過多**（如 v50）：UI 折疊顯示最新 5 個 + 「展開更多」（保護 UX）

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**：`/templates/new` 提供「簡單模式」與「進階模式」兩個頁籤，預設簡單模式
- **FR-002**：簡單模式提供：場景樣板下拉、基本資訊區、角色/對象屬性表格（動態增刪行）、規則卡片（含 5 種預設規則類型：ge/le/eq/in/role_in_target_field）、預設對象表格、可選 preferences_schema
- **FR-003**：簡單模式的規則卡片 MUST 依使用者選的類型 + 填入的欄位**自動生成 description**（如「角色年級必須 ≥ 4」）；使用者可後續編輯描述
- **FR-004**：簡單模式 **不支援** and/or/not 巢狀規則（若需要請進階模式）
- **FR-005**：進階模式提供：填空欄位（場景/角色/對象/規則/志願）+「複製完整 Prompt」按鈕（JS clipboard 操作）+ YAML 大文字框
- **FR-006**：「複製完整 Prompt」MUST 複製內含整份 `docs/template-authoring-guide.md` 文字 + 填空生成的場景描述
- **FR-007**：兩模式皆提供「驗證」「下載 YAML」「複製 YAML」「儲存」4 個按鈕
- **FR-008**：「驗證」呼叫後端 `POST /templates/validate`，回 JSON 含 `ok: true/false` + 錯誤訊息（繁中）
- **FR-009**：「儲存」呼叫後端 `POST /templates/save`，寫入 `data/templates/<id>/v<N>.yaml`（N 自動為現有最大版本 +1）；驗證失敗不寫入
- **FR-010**：`TemplateRegistry` MUST 在啟動 + 每次取模板列表時掃描 `data/templates/` 目錄；自訂模板與內建模板並列；同 id 衝突（自訂 vs 內建）→ 自訂模板**儲存時拒絕**（不可覆蓋內建）
- **FR-011**：自訂模板的「目前版本」MUST 為 `data/templates/<id>/` 內版本號最大的 `v<N>.yaml`
- **FR-012**：`/templates/<id>` 頁面對自訂模板 MUST 顯示「編輯」按鈕；對內建模板 MUST 顯示「Fork 為自訂模板」按鈕；兩按鈕互斥
- **FR-013**：`/templates/<id>` 頁面對自訂模板 MUST 顯示「版本歷史」段（列出 v1...vN + 儲存時間 + 「查看此版本」連結展開內容）
- **FR-014**：`/templates/<id>/edit` 預載**最新版本**內容到對應模式（簡單 / 進階自動判斷：若內容含 and/or/not 強制進階）
- **FR-015**：`POST /templates/<id>/save`（編輯路徑）MUST 寫 `v<N+1>.yaml`；版本號自動遞增；不可覆蓋現有版本
- **FR-016**：「Fork 為自訂模板」MUST 跳 `/templates/new` 並預填內建模板內容；id 預填為 `<原id>-fork`（使用者可改）
- **FR-017**：媒合紀錄頁 `/match/<rid>` MUST 新增「以此模板版本再執行」按鈕；點擊後跳 `/match/new?template_id=<id>`（若該模板及版本仍存在）或 `/match/new?template_snapshot=<rid>`（若不存在，從 audit 還原為臨時模板）
- **FR-018**：所有 UI 文案 MUST 為繁中；「自動生成 description」MUST 通過技術詞零容忍正則
- **FR-019**：階段 1-3c+4a-4d 既有 281 個自動化測試 MUST 100% 繼續通過
- **FR-020**：本 feature 動 `src/matcher/template_loader.py`（TemplateRegistry 掃描 custom dir）—— 算核心職責擴充（教訓 7 第 3 種合法情境：「模板管理本來就是核心職責」），PR 描述明示

### Key Entities

- **自訂模板檔案**：路徑 `data/templates/<id>/v<N>.yaml`；單一檔案即一個版本快照；存活週期：永久（除非使用者刪除）
- **模板版本號**：整數 ≥ 1；同 id 內單調遞增；「目前版本」=該 id 目錄中數字最大者
- **場景樣板**（scenario templates）：簡單模式的「快速起點」；定義在 web 層的常數 dict；4-5 個（空白 / 社團報名 / 課輔配對 / 研習分組 / 教師班級）
- **規則類型** (5 種)：對應到 5 個 expr 算子（ge/le/eq/in/role_in_target_field）；每種類型在 UI 上是一張卡片含對應欄位
- **臨時模板 snapshot**（FR-017 後半）：使用者點「以此版本再執行」但原模板不存在時，從 audit 還原寫入記憶體（不持久化）；命名為 `<id>-snapshot-<rid>`

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**：使用者可在簡單模式中**完全不寫 YAML**，從場景樣板開始、加 3 屬性 + 2 規則 + 3 預設對象 → 儲存 → 用此模板跑通一次媒合；端到端 ≤ 10 分鐘
- **SC-002**：使用者可在進階模式中複製完整 prompt（含整份 guide 文字）給 AI，貼回 YAML → 驗證 → 儲存，端到端 ≤ 5 分鐘
- **SC-003**：自訂模板儲存後**重啟 server** 仍可使用（持久化驗證；整合測試模擬重啟）
- **SC-004**：自訂模板編輯後寫 v2，原 v1 仍可在 `/templates/<id>` 「版本歷史」段查看；100% 不遺失
- **SC-005**：內建模板（teacher-class、study-group）100% 不可被覆蓋；嘗試以同 id 儲存 → 拒絕並顯示繁中錯誤
- **SC-006**：所有「自動生成 description」文案 100% 通過 FORBIDDEN_TECHNICAL_TOKENS 正則驗證（沿用前 4 feature 清單）
- **SC-007**：階段 1-3c+4a-4d 既有 281 個自動化測試 100% 繼續通過
- **SC-008**：本 feature 新增 ≥ 15 個自動化測試（端到端建立 / 編輯 / 驗證 / 版本歷史 / fork / 再執行 / 技術詞驗證）
- **SC-009**：媒合紀錄頁「以此版本再執行」與原 audit `assignment` 100% bytewise 等價（同 seed + 同 snapshot）
- **SC-010**：核心改動嚴格限定於 `template_loader.py` 內**新增**邏輯（掃描 custom dir）；既有 `parse_template_yaml` / `TemplateRegistry` 既有方法簽名不改

## Assumptions

- **無新依賴**：jinja2 已能渲染表單；HTML5 form 動態增減行可用純 JS 完成（或不做 dynamic add；用「固定 10 列空欄」省 JS——plan 階段決定）
- **持久化儲存**：純檔案系統（`data/templates/<id>/v<N>.yaml`）；無 SQLite；與既有 `data/matches/` 風格一致
- **版本控制粒度**：每次 save = 新版本；不做 draft；不做 diff 視覺化（純展示舊版內容即可）
- **內建模板永遠 read-only**：保護出廠模板；想改 → fork
- **TemplateRegistry 行為**：啟動時掃描 builtin + custom；同 id 衝突在儲存階段攔截（不允許覆蓋內建）
- **核心改動範圍**：僅 `template_loader.py` 加 `_scan_custom_dir()` 與相關方法；其他核心模組 0 改動
- **不處理**：
  - 模板共享 / 上傳到雲端
  - 模板 diff 視覺化（v1 vs v2）
  - 模板回滾（rollback）—— 想用舊版就 fork 為新模板
  - 多人同時編輯衝突 / 鎖定
  - 模板審核流程（無管理員角色概念）
  - 進階模式的 YAML 語法高亮 / 自動補全（純 textarea）
  - 簡單模式的 and/or/not 巢狀 UI（需請 user 用進階模式）
  - 模板 export 為 git-tracked 檔案（使用者自己 cp）
  - 真正的「再執行就 bytewise 相同」（seed 可改、roster 可不同；只保證模板版本對齊）

# 願景

## 問題陳述

學校行政常需要為「角色 ↔ 對象」做媒合：不同專業的老師對應不同特色的班級、
跨校研習分組、社團幹部配對等。現況痛點：

- **靠人工喬**：主任憑經驗分配，結果難以對外解釋，當事人質疑時拿不出依據。
- **靠純抽籤**：完全隨機卻浪費了「應該優先考慮專業適配」這個資訊。
- **靠 Excel 公式**：能算分數但難以解釋規則、無法重現抽籤過程、爭議時無稽核軌跡。

## 核心想法

**讓學校行政能在 30 分鐘內完成一次有公信力、爭議發生時能拿出紀錄的角色屬性媒合。**

做法：先用顯式規則篩出「資格集合」，再以可驗證的**公平分配機制**
（從內建機制清單擇一：純抽籤、隨機輪流挑、層級填滿…，詳見架構段）
將資格集合內的對象配對，全程留下可稽核的紀錄。並提供「模板」
讓不同媒合情境（教師-班級、研習分組…）能快速套用——模板包含屬性 schema、
規則、UI 表單欄位、稽核報告格式。**每場活動可獨立選擇要使用哪一種分配機制。**

## 範圍邊界

**matcher 處理**：給定角色端、對象端、規則、（選擇性的）偏好，
產生一次性的可稽核公平分配。

**matcher 不是 scheduler、不是 voter、也不是動態調整器**。三者各有各的問題類別
與公平定義，若有此類需求，請**開立獨立專案**實作，不要把這些邏輯塞進 matcher。
具體而言：

- **不處理排程（scheduler）**：多輪闖關表、賽程表、課表等——本質上需要跨時段
  協調與軟約束最佳化，與根公理「不在資格集合外做最佳化」存在實質張力。
- **不處理投票（voter）**：plurality、ranked choice、STV 等選舉機制——這是
  voting system 的範疇，公平定義不同。
- **不處理動態調整**：已分配結果的事後重新洗牌——一次完成、結果即定案。
- **不處理雙邊穩定匹配**（DA / Gale-Shapley）：暫不納入，待真有需求時再評估。

## 現狀

**階段 1、階段 2a、階段 2b、階段 3a、階段 3b、階段 4a、階段 4b 已完成**。

階段 1（commit `d1331dc`）：

- 核心媒合引擎（library + CLI）：`src/matcher/` 10 個模組
- 技術棧：Python 3.11 + Typer + PyYAML + pytest（uv 管理環境）
- 過濾／分配兩階段嚴格分離；M0 純抽籤分支實作完成
- 完整稽核紀錄 + 8 種明確錯誤類別 + preferences 介面預留但於 M0 拒絕

階段 2a 模板系統（commit `d4c373c`）：

- `Template` / `TemplateRegistry` 資料模型與載入器
- 2 個內建模板：`teacher-class`、`study-group`（後者宣告 `preferences_schema`）
- CLI 子應用：`matcher template list/show/export`
- `matcher run` 新增 `--template` / `--template-file`，與 `--rules + --roster` 三組互斥
- audit schema 升級為 v1.1，新增 `template_snapshot` 欄位

階段 2b CSV / Excel 資料匯入（commit `586fd93`，新增 openpyxl 依賴）：

- `src/matcher/data_import.py`：CSV / Excel 載入器
- 編碼啟發式 3 輪偵測（UTF-8 → UTF-8-SIG → CP950）+ BOM 優先檢測
- 模板 `AttributeDecl` 新增 `aliases`；兩個內建模板補上中文別名
- CLI 新增 `--roster-csv` / `--roster-xlsx` / `--sheet`，與 `--roster` 三組互斥
- audit schema 升級為 v1.2，新增 `import_metadata` 欄位
- 4 個新錯誤類別：RosterDecodeError(30) / ColumnMismatch(31) / TypeError(32) / SheetAmbiguous(33)
- targets 旁檔模式：`<stem>.targets.yaml`
- 自動化測試：116 個（階段 1 既有 48 + 階段 2a 既有 34 + 階段 2b 新增 34），全綠

階段 3a Web UI 主流程（commit `0384021`，新增 fastapi/uvicorn/jinja2/python-multipart/httpx 依賴）：

- `src/matcher/web/` 完整 Web 子套件：app 工廠、3 個 routes、8 個 Jinja2 樣板、極簡 CSS
- 後端 FastAPI + uvicorn；前端 HTMX + Jinja2（server-rendered，無 Node toolchain）
- CLI 新增 `matcher serve [--host] [--port] [--reload]`
- 媒合紀錄持久化於 `data/matches/<id>.json`（atomic write、無 DB）；自有 schema `match-record/1.0`
- 模板新增 `default_targets` 欄位：Web UI 不需上傳 targets 旁檔（CLI 仍支援旁檔）
- 4 個既有黃金檔重生（template_snapshot 含 default_targets；assignment 不變）
- 自動化測試：142 個（既有 116 + 階段 3a 新增 26），全綠
- ⏸ SC-001「學校行政 30 分鐘真人測試」待人工驗證

階段 3b 個別查詢視圖（commit `f8ac328`，無新依賴）：

- `src/matcher/web/{humanize,individual}.py` 兩個純函式（規則代名詞替換、audit 子集萃取）
- 端點 `GET /match/{rid}/role/{role_id}` 個別查詢頁 + `/audit.json` 個別子集下載
- 個別查詢頁四大段：基本資訊、分配結果、媒合過程說明、下載我的稽核紀錄
- admin 結果頁加入「個別查詢連結」可摺疊區段（無 JS，原生 `<details>`）
- 個別錯誤頁（`individual_error.html`）用語面向一般教師，無技術 token
- 技術詞零容忍以正則自動化驗證；同 URL 兩次訪問 response bytewise 相同
- 核心 8 個模組 **0 改動**（再次驗證教訓 5「入口無關性」）
- 自動化測試：169 個（既有 142 + 階段 3b 新增 27），全綠
- ⏸ SC-001「一般教師 5 分鐘真人測試」待人工驗證

階段 4a M1 RSD 機制（commit `91c916a`，無新依賴）：

- `src/matcher/allocator.py` 新增 `allocate_m1`（Fisher-Yates 洗牌處理順序 → 逐位選最高未滿志願）
- `_normalize_preferences`：preferences 去重 + 忽略資格集合外 id
- `pipeline.py` mechanism dispatch（M0/M1）；M1 + 全空 preferences → 拒絕
- audit schema v1.2 → v1.3：新增 `processing_order` + `allocation_trace[].{preferred_order, preference_rank, fallback_random_index}`
- CLI `--mechanism M0|M1`（不分大小寫）；不支援值 exit 2
- 新錯誤類別 `M1RequiresPreferences`（exit 40）
- 範例 `examples/study-group/roster-m1.csv`（9 學生含 1-3 志願）
- 5 個既有黃金檔重生（v1.3 + null 欄位）+ 1 個新 `study-group-m1.audit.json`
- 自動化測試：188 個（既有 169 + 階段 4a 新增 19），全綠
- **首次合法動核心 5 個模組**（allocator/pipeline/audit/errors/cli）——「分配機制就是核心職責」

階段 4b M2 Boston 機制（commit `51d7e89`，無新依賴）：

- `src/matcher/allocator.py` 新增 `allocate_m2`：層級逐次填滿、同層超額用 Fisher-Yates 取前 N、fallback 抽籤、未分配者亦寫入 trace
- `pipeline.py` dispatch 擴充為 M0 / M1 / M2 三選一
- `errors.py` `M1RequiresPreferences` 重新命名為 `MechanismRequiresPreferences`；保留 alias 維持向後相容
- `audit_trace` 條目新增 `tie_break_random_index`（M0/M1/M2 非超額為 null）
- audit schema **保持 v1.3 不升版本**（教訓 3 的最節制版本）
- CLI `--mechanism` 接受 M0/M1/M2；訊息依 mechanism 動態填寫
- 6 個既有黃金檔重生（diff 僅每筆 trace 新增 `tie_break_random_index: null`）+ 1 個新 `study-group-m2.audit.json`
- 自動化測試：210 個（既有 188 + 階段 4b 新增 22），全綠
- **第二次合法動核心** 5 個模組——符合教訓 7「新分配機制 = 核心職責擴充」判準

尚未開始：稽核報告 PDF 匯出（階段 3c）、Web UI 填志願介面（階段 4c）、K8s 部署（階段 5）、實際學校場景試行。

## 架構

關鍵決策（明確的部分）：

- **目標形態**：Web App（多使用者透過瀏覽器操作）
- **資料輸入**：CSV / Excel 匯入 ＋ 表單填寫，兩者並存
- **儲存層**：檔案系統為主——規則檔／名單檔 YAML、稽核 JSON、媒合紀錄 JSON
  （`data/matches/<id>.json`，atomic write）；不引入 SQLite 或外部資料庫，
  符合「K8s 部署簡單就好」的方向
- **模板系統**：模板為一級概念，涵蓋四層——
  屬性 schema、規則定義、UI 表單欄位、稽核報告格式。
  **動機**：非技術使用者（學校行政、教師）需要具體可用的東西才能上手；
  過度抽象會讓工具無法被採用。模板提供具體入口，自訂規則作為進階出口。
- **核心模組分離**：「過濾」與「分配」必須在程式碼結構上明確分離
  （見 `principles.md` 原則 3）
- **分配機制為上位抽象**：核心引擎的介面為 `allocate(資格集合, 志願?, seed) → 結果`。
  純抽籤是「志願為空 → 隨機分配」的退化情況；志願序是「志願非空」的多種具體實現。
  兩種模式共用同一介面與同一份稽核機制。

  **內建機制清單**：

  - **M0 純抽籤**：無偏好，從資格集合隨機分配（階段 1）
  - **M1 隨機輪流挑（RSD）**：隨機決定處理順序，每人依序挑最高未滿志願（階段 4）
  - **M2 層級填滿（Boston）**：先全塞第 1 志願（超額抽籤）→ 沒進的退到第 2 志願…（階段 4）

  **明文排除（避免未來誤用）**：

  - **加權抽籤**：給特定人/組別更高被抽中機率——直接違反原則 3。
    若需「優先權」，應改寫為過濾規則（例：「特教老師有 2 倍籤」應以資格條件表達）。
  - **先到先得（FCFS）**：報名時間決定——懲罰未及時看到通知者，違反程序公平。

  **機制擴充原則**：未來新增機制必須在此介面下實作，不可繞過稽核
  （規則 + 名單 + 志願 + seed → 過程紀錄）。
- **隨機性**：分配模組接受外部 seed，輸出可重播的過程紀錄
  （見 `principles.md` 原則 2）
- **部署**：可部署到 K8s，但保持簡單（單一 container、檔案系統儲存即可）

待定：

- 前後端技術棧（TBD，實作前再選）
- 認證/權限機制（先 TBD，可能先單機/單組織）

## 路線圖

### 階段 1：核心媒合引擎（library + CLI）

- [x] 完成（commit `d1331dc`，2026-05-22）

<!--
  交付：純函式的媒合核心——介面為 allocate(資格集合, 志願?, seed) → 結果。
  階段 1 只實作「志願為空 → 純抽籤」分支，但介面已預留 preferences 參數，
  未來階段 4 直接擴充志願序分支即可。先以 CLI 驗證，不做 UI。
  前置條件：無
-->

**成功標準：**

- [x] 過濾與分配兩階段在程式碼結構上完全分離
- [x] 介面已包含 `preferences?` 參數，但本階段僅實作 `preferences` 為空時的純抽籤分支
- [x] 給定相同（規則 + 名單 + seed）能 100% 重現結果
- [x] 「教師-班級配對」這個基準場景能用 CLI 跑通並輸出稽核紀錄
- [x] 測試覆蓋核心：規則篩選、邊界（無人符合資格、人數不足）、分配可重現性（純抽籤分支）

### 階段 2a：模板系統

- [x] 完成（commit `d4c373c`，2026-05-22）

<!--
  交付：模板格式（schema + 規則 + UI 欄位 + 報告格式）能被定義、儲存、載入；
  CLI 三子命令 list/show/export；--template / --template-file 與 --rules+--roster 三組互斥。
  前置條件：階段 1
-->

**成功標準：**

- [x] 至少 2 個內建模板：「教師-班級配對」「研習分組」
- [x] 自訂模板能匯出/匯入為單一檔案
- [x] 模板快照（template_snapshot）進入稽核紀錄，確保「相同模板 + 名單 + seed」逐位元組可重現

### 階段 2b：CSV / Excel 資料匯入

- [x] 完成（commit `586fd93`，2026-05-22）

<!--
  交付：CSV / Excel 匯入名單能對齊到模板的屬性 schema（含中文別名）；
  自動處理編碼、空值、欄位對齊；audit schema 演進為 v1.2 加 import_metadata。
  前置條件：階段 2a
-->

**成功標準：**

- [x] CSV 匯入名單能對齊到模板的屬性 schema（含 UTF-8 / UTF-8-BOM / CP950 三編碼）
- [x] Excel（.xlsx）匯入名單能對齊到模板的屬性 schema（含多工作表處理）
- [x] 匯入過程中的欄位對齊錯誤、編碼錯誤、型別錯誤、工作表歧義皆有明確繁中錯誤訊息（4 種獨立 exit code）

### 階段 3a：Web UI 主流程

- [x] 完成（commit `0384021`，2026-05-22）

<!--
  交付：瀏覽器介面主流程——選模板、上傳 CSV/Excel 名單、設定種子、執行媒合、
  查看結果頁、下載稽核紀錄、過去媒合列表。
  前置條件：階段 2a、階段 2b
-->

**成功標準：**

- [x] 學校行政能用瀏覽器完成「選模板 → 上傳名單 → 執行 → 下載稽核」主流程（30 分鐘核心想法，⏸ 真人測試待安排）
- [x] Web 與 CLI 路徑的稽核紀錄五段（qualified_set/assignment/filter_trace/allocation_trace/template_snapshot）逐位元組相同

### 階段 3b：被媒合者個別查詢視圖

- [x] 完成（commit `f8ac328`，2026-05-23）

<!--
  交付：被媒合者（老師、班級代表）可查到自己為什麼有/沒資格、是在哪一輪被抽到。
  前置條件：階段 3a
-->

**成功標準：**

- [x] 被媒合者個別查詢視圖（原則 5）可運作
- [x] 個別查詢頁面用語面向一般教師，避免技術名詞（以正則自動化驗證；⏸ 真人測試待安排）

### 階段 3c：稽核報告匯出（PDF / 結構化）

- [ ] 完成

<!--
  交付：依模板 report_fields 宣告渲染稽核報告，可下載為 PDF 或結構化檔案。
  前置條件：階段 3a
-->

**成功標準：**

- [ ] 稽核報告可匯出（PDF 或結構化檔案）
- [ ] 報告依模板 report_fields 宣告渲染欄位

### 階段 4a：M1 RSD（隨機輪流挑）機制

- [x] 完成（commit `91c916a`，2026-05-24）

<!--
  交付：啟用核心引擎中「志願非空」分支；mechanism dispatch（M0/M1）；
  CLI --mechanism M0|M1；audit schema v1.2→v1.3 加處理順序與志願排名；
  preferences 規範化（去重 + 忽略資格外）。Web UI 不動。
  前置條件：階段 1+2a+2b
-->

**成功標準：**

- [x] M1 路徑可由 seed 推導處理順序，逐位選最高未滿志願；同 seed 兩次跑出 bytewise 相同 audit
- [x] M1 + 全空 preferences 明確拒絕（`M1RequiresPreferences`，exit 40）
- [x] 既有 M0 路徑邏輯完全不變；5 個既有黃金檔重生為 v1.3 後 assignment / qualified_set 等核心欄位不變

### 階段 4b：M2 Boston（層級填滿）機制

- [x] 完成（commit `51d7e89`，2026-05-24）

<!--
  交付：新增 M2 演算法（先全塞第 1 志願→超額抽籤→沒進的退到第 2 志願…）；
  audit 對應紀錄；CLI --mechanism 擴為 M0|M1|M2。
  前置條件：階段 4a
-->

**成功標準：**

- [x] M2 路徑可在 seed 推導下完成層級填滿；audit 完整記錄每層級的超額抽籤過程（`tie_break_random_index`）
- [x] CLI / pipeline 可在 M0 / M1 / M2 三種機制間切換

### 階段 4c：Web UI 填志願介面 + 機制選擇器

- [ ] 完成

<!--
  交付：Web UI 新建媒合流程支援填志願（表單）；活動建立時可選 M0/M1/M2 機制；
  個別查詢頁顯示志願滿足度。
  前置條件：階段 4a、階段 4b
-->

**成功標準：**

- [ ] Web 新建媒合流程提供志願填寫表單欄位
- [ ] 活動建立時可選 M0 / M1 / M2 機制（下拉），不可選機制 disabled 並附說明
- [ ] 個別查詢頁顯示「您被分到第幾志願」（沿用 audit 中的 preference_rank）

### 階段 5：K8s 部署

- [ ] 完成

<!--
  交付：可部署到 K8s 的容器化版本，使用 PVC 存放檔案系統資料。
  前置條件：階段 4
-->

**成功標準：**

- [ ] 單一 Dockerfile，無外部資料庫依賴
- [ ] 提供範例 K8s manifest（Deployment + Service + PVC）
- [ ] 在 K8s 上重啟後資料與稽核紀錄不遺失

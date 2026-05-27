# 願景

## 問題陳述

學校行政常需要為「參與者 ↔ 對象」做媒合：不同專業的老師對應不同特色的班級、
跨校研習分組、社團幹部配對等。現況痛點：

- **靠人工喬**：主任憑經驗分配，結果難以對外解釋，當事人質疑時拿不出依據。
- **靠純抽籤**：完全隨機卻浪費了「應該優先考慮專業適配」這個資訊。
- **靠 Excel 公式**：能算分數但難以解釋規則、無法重現抽籤過程、爭議時無稽核軌跡。

## 核心想法

**讓學校行政能在 30 分鐘內完成一次有公信力、爭議發生時能拿出紀錄的參與者屬性媒合。**

做法：先用顯式規則篩出「資格集合」，再以可驗證的**公平分配機制**
（從內建機制清單擇一：純抽籤、隨機輪流挑、層級填滿…，詳見架構段）
將資格集合內的對象配對，全程留下可稽核的紀錄。並提供「模板」
讓不同媒合情境（教師-班級、研習分組…）能快速套用——模板包含屬性 schema、
規則、UI 表單欄位、稽核報告格式。**每場活動可獨立選擇要使用哪一種分配機制。**

## 範圍邊界

**matcher 處理**：給定參與者端、對象端、規則、（選擇性的）偏好，
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

**階段 1、階段 2a、階段 2b、階段 3a、階段 3b、階段 3c、階段 4a、階段 4b、階段 4c、階段 4d、階段 4e、階段 4f（UI 直接填名單）、階段 4g（移除 default_targets）、階段 6（登入與資源歸屬）、階段 7（配對失敗可解釋）、階段 8（對象試算表匯入 + 動態範例 + 過去紀錄重用）、階段 9（用詞統一「參與者」+ role→participant 全面更名、audit schema v1.5）已完成**。

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
- 模板新增 `default_targets` 欄位：Web UI 不需上傳 targets 旁檔（CLI 仍支援旁檔）—— **註**：該欄位於階段 4g 已完全移除
- 4 個既有黃金檔重生（template_snapshot 含 default_targets；assignment 不變）
- 自動化測試：142 個（既有 116 + 階段 3a 新增 26），全綠
- ⏸ SC-001「學校行政 30 分鐘真人測試」待人工驗證

階段 3b 個別查詢視圖（commit `f8ac328`，無新依賴）：

- `src/matcher/web/{humanize,individual}.py` 兩個純函式（規則代名詞替換、audit 子集萃取）
- 端點 `GET /match/{rid}/participant/{participant_id}` 個別查詢頁 + `/audit.json` 個別子集下載
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

階段 4c Web UI 機制選擇 + 結果頁志願展示（commit `d4697e7`，無新依賴）：

- `/match/new` 表單新增「分配機制」下拉（M0/M1/M2，預設 M0）+ 友善說明
- 結果頁顯示機制名（M0 純抽籤 / M1 RSD 隨機輪流挑 / M2 Boston 層級填滿）；M1/M2 路徑下顯示「處理順序」段與分配表「志願排名」欄
- 個別查詢頁 M1/M2 路徑下顯示三分支文案：「您被分到第 N 志願」/「您原本的志願已被分配給其他人，由公平抽籤分到」/「您未在志願清單中，由公平抽籤分到」（依 audit `preference_rank` + roster_snapshot `preferences` 長度推導）
- `humanize.py` 新增 `mechanism_label` / `preference_rank_display` 純函式
- audit schema **保持 v1.3 不升版本**——三分支邏輯純由現有欄位推導，零新增（教訓 3 的最節制版本）
- 技術詞零容忍延伸：preference_rank / processing_order / tie_break_random_index / fallback_random_index / preferred_order 全納入禁用清單
- **核心模組 0 改動**（教訓 7 純度示範——「新呈現視圖 = 周邊整合」判準下，所有變更僅限 `src/matcher/web/`）
- 自動化測試：234 個（既有 210 + 階段 4c 新增 24，2 個資料相依 skip），全綠
- Web/CLI bytewise 等價對 M1+M2 各 1 個 parametrize 測試守住

階段 4d Web UI 動態填志願表單（commit `6087ffb`，無新依賴）：

- `/match/run` 偵測「模板含 `preferences_schema` + roster 全空 + M1/M2」→ 跳到填志願中介頁面
- 新增 `POST /match/preferences` 端點：hidden inputs 攜帶 base64(roster bytes) + `pref_<participant_id>_<rank>` 動態欄位 + `_action=submit/skip`
- 新增 `preferences_form.html` 樣板：候選對象段、N 列 × max_choices 個 `<select>` 表格、「確認執行」與「跳過此步驟」兩按鈕
- 新增 `humanize.target_summary` 純函式（「程式組（容量 3 人）」格式）
- 表單驗證：同列重複、未知 target id、全空 submit → 回填志願頁 + 友善繁中訊息
- M0 + 全空、teacher-class（無 schema）+ M1、CSV 已含 prefs → 不跳填志願頁（向後相容 008）
- **D1 決策**：用 hidden inputs 而非 session 中介軟體——避免引入 stateful 機制（YAGNI 原則的具體應用）
- **D3 決策**：重新解 base64 + data_import 而非序列化 parsed roster——對複雜不可信狀態，重做 parse 比序列化更可靠
- 技術詞零容忍延伸：`default_targets` / `preferences_schema` / `max_choices` 加入禁用清單
- **核心模組 0 改動**（教訓 7 純度示範第 3 次：「新呈現視圖 + 新輸入路徑」皆為周邊整合）
- 自動化測試：256 個（既有 234 + 階段 4d 新增 22，2 個資料相依 skip），全綠
- Web/CSV bytewise 等價守住（SC-001）；50 學生 × 3 志願 = 150 select 規模測試通過

階段 3c 稽核報告 PDF 匯出（commit `76c9689`，新增 weasyprint 依賴）：

- `src/matcher/web/pdf.py` 新檔：`render_match_report_pdf` 純函式（Web + CLI 共用，教訓 5 第 4 次驗證）；`PdfRenderUnavailable` 例外
- Web 端點：`GET /match/{rid}/report.pdf`（admin 版）+ `GET /match/{rid}/participant/{participant_id}/report.pdf`（individual 版）
- CLI：`matcher report --audit X --output Y [--participant-id Z]` 子指令；`cli.py` 僅 1 行新增（cli_report.py 兄弟檔，**核心 0 改動第 4 次**）
- 2 個新樣板 `templates/pdf/{match,individual}_report.html`（A4 列印版，與螢幕樣板分離）
- **graceful degrade**：WeasyPrint 系統依賴不可用 → Web 503 + CLI exit 50 + 友善安裝指引；既有 256 測試不受影響
- 技術詞零容忍延伸至 PDF（pdftotext 驗證）；中文用系統字體渲染 + 可搜尋
- **實作偏離 spec**：D3/FR-005 要求嵌入 ~10MB Noto Sans CJK 字體；實作改用系統字體 fallback（pdftotext 已驗證 CJK 可搜尋；10MB binary 不宜入 repo）——已在 commit message 與 tasks.md 誠實揭露（教訓 4「spec 在 implement 階段被推翻」模式的再次應用）
- 新增 `tests/conftest.py`：macOS 自動設 `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib` 讓 WeasyPrint 找到 libgobject
- 自動化測試：280 個（既有 256 + 階段 3c 新增 24，2 個資料相依 skip），全綠

階段 4e 範本創作 UI + 全 UI 用詞白話化（commit `5d41473`，新增 weasyprint 之外 Tailwind Play CDN + Alpine.js）：

- `/templates/new` 新增「用表單建立」模式：基本資訊 + 參與者屬性 + 對象屬性 + 配對條件 + 是否填志願；動態加減欄位 / 規則；條件類型切換時只顯示相關欄位
- 「自己寫 YAML（或請 AI 幫忙）」進階模式：AI Prompt 助手填空 + 「複製給 AI 看的說明」按鈕（內含整份 `docs/template-authoring-guide.md`）+ YAML textarea
- 持久化：`data/templates/<id>/v<N>.yaml`，每次儲存 = 新版本；TemplateRegistry 啟動掃描 + invalidate
- **動核心 `template_loader.py`**——屬「核心職責擴充」（教訓 7 第 3 種合法情境：模板管理本就是核心職責）
- 內建範本不可覆蓋（save 階段拒絕）；id 格式限定 `[a-z0-9-]+`
- 配套全 Web UI 用詞白話化（教訓 8 的反向應用——使用者明確指出工程師詞作為對照標的）：
  - 模板 → **範本**；媒合 → **配對**；新建媒合 → **新增一次配對**；過去媒合 → **過去紀錄**
  - 分配機制 M0/M1/M2 → **純抽籤 / 輪流挑 / 依志願先後填滿**（內部代碼從使用者介面完全移除）
  - 隨機種子 → **亂數種子**（+ 完整白話 helper：「同一份名單 + 同一個種子 → 永遠抽出一樣的結果」）
  - 型別 str / int / list_str → **文字 / 數字 / 多筆文字**
  - 別稱（aliases）UI 移除；`data_import.py` 自動把顯示名稱（description）視為合法 alias，使用者不必額外填
  - 預設對象清單從建範本 UI 移除——範本只定義規則，具體對象在跑配對時提供（內建範本暫時保留 default_targets；**階段 4g 已完全移除概念**）
- **新前端技術棧**：Tailwind Play CDN + Alpine.js（兩者 CDN-only，無 Node toolchain / 無 build step / 無 npm — 符合架構決策原意）
- Pipeline / CLI 錯誤訊息也同步白話化：「『純抽籤』不接受志願輸入」「『輪流挑』需要至少一位填了志願」（保留 audit JSON 內部 mechanism 代碼）
- 新檔：`src/matcher/web/template_form.py`（簡單模式表單 → YAML dict 純函式 + SCENARIO_TEMPLATES 範例）
- 自動化測試：303 個（既有 280 + 階段 4e 新增 23，2 個資料相依 skip），全綠

階段 4f UI 直接填名單（commit `6056f98`，無新依賴）：

- `/match/new` 三選一入口：📂 上傳 / ✏️ 直接填 / 📌 過去紀錄
- 新增 `/match/new/fill` 動態渲染範本宣告欄位（加減列）+ `/match/run-from-form` endpoint
- 純函式 `assemble_roster_csv_bytes` / `assemble_targets_yaml_bytes`，UI → CSV bytes → 既有 pipeline
- SC-002 守住：UI 表單路徑與 CSV 上傳路徑 5 段 audit bytewise 等價
- M1/M2 自動跳 feature 009 志願頁
- 自動化測試：342 個（既有 326 + 16 新增），全綠
- 核心 0 改動：`src/matcher/{rules,filter,allocator,pipeline,audit,errors,data_import,template_loader,rng,roster}.py` 不動

階段 4g 移除 default_targets 概念（commit `b25af35`，無新依賴）：

- 拔除 `Template.default_targets` 欄位 + `template_snapshot.default_targets` audit 子鍵
- audit `schema_version` 升 v1.3 → v1.4
- 內建範本 teacher-class / study-group 拔除 default_targets 區段；examples 補上對應 sidecar
- `data_import._load_targets` 一律要求旁檔；錯誤訊息含明確檔名建議
- UI 填名單頁對象段永遠顯示（移除 `requires_targets` 條件）
- `/match/preferences` 新增 `targets_bytes_b64` hidden input，志願頁往返不漏 sidecar
- 向下相容：舊 YAML 含 default_targets 靜默忽略；舊 v1.3 audit viewer 不主動讀此鍵
- 自動化測試：348 個（既有 342 + 6 新增 + 既有 15+ 調整），全綠
- 動機：「公平公開」原則——使用者在 UI 填名單時就該透明知道對象有哪些

階段 6 登入與資源歸屬（merge `30443eb`，**新增 authlib、itsdangerous**）：

- Google OAuth 登入（Authlib）+ 簽章 cookie session（Starlette SessionMiddleware，無伺服器端 session、無 DB）
- 管理頁強制登入；配對紀錄/範本綁 `owner`（email）；列表只列自己的；跨使用者存取 403
- **個別連結改 itsdangerous 簽章 token**（`/r/{token}`）：無狀態、不可偽造、不可枚舉；當事人免登入可看自己結果；修掉舊 participant_id 枚舉漏洞
- 範本私有/公開兩段可見性（meta sidecar `data/templates/<id>/meta.json`，不動核心 template_loader）；公開範本他人可見可複製不可編輯
- 公開網路加固：所有 POST 表單 CSRF token、session cookie Secure/HttpOnly/SameSite、`/auth/login` 與配對執行端點記憶體 rate-limit
- `.env` 自動載入（純標準庫，setdefault 不覆蓋已設變數）+ `.env.example` 範本
- 決議：開放任何 Google 帳號登入 / 純個人私有 / 升級清空舊資料
- **核心 0 改動**：所有變更限於 `src/matcher/web/`；`src/matcher/*` 核心與 CLI 不動
- 自動化測試：380 passed, 2 skipped（新增 security token/csrf、auth flow、ownership、token link、template visibility、dotenv 等）

階段 7 配對失敗可解釋（branch `015-explain-empty-set`，無新依賴）：

- 「資格集合為空」不再只說「全部沒過」——`filter_qualified` 把已算好的 filter_trace
  與「每條規則刷掉幾組」統計**帶進 QualifiedSetEmpty 例外**（原本被丟棄），算出「元兇規則」
- CLI exit 10 多印「最可能原因：<元兇規則描述>（卡住 N/M 組）」+ 各規則淘汰數
- Web：UI 填名單空集合 → 回填名單頁 + 診斷紅字（保留輸入）；CSV 上傳 → 失敗頁渲染診斷
- 失敗頁移除英文錯誤類別名（技術 token），只留白話訊息 + 診斷
- 修內建 teacher-class R003：接受值由英文 `bilingual/arts` 改中文 `雙語/藝術`（與說明一致，
  使用者照說明填就過）；examples sidecar 同步
- **核心變動只碰 filter/errors/cli**（可解釋性職責，教訓 7）；成功 audit schema 不變
- 自動化測試：393 passed, 2 skipped（新增 rejection_summary、空集合攜帶診斷、CLI/Web 診斷等）

階段 8 對象試算表匯入 + 動態範例 + 過去紀錄重用（merge `4ae4576`，無新依賴）：

- 對象名單也能用 CSV/Excel 匯入：上傳**兩個獨立檔**（參與者一個、對象一個），不必寫 YAML 旁檔
- 核心 `data_import` 新增 `load_targets_csv/xlsx`（重用編碼偵測/表頭對齊/型別轉換）+ `load_roster_csv/xlsx(targets=)` 向後相容注入
- 對象檔編號可省略 → 自動 T001…（避開已填）；中文表頭自動對齊；分隔符容錯（；、，）
- **動態範例**：`/templates/{id}/example/{participants|targets}.{csv|xlsx}` 依範本 schema 即時產生範例（中文表頭 + 格式提示列），**涵蓋自訂範本、永遠與範本同步**；上傳頁提供下載連結
- **過去紀錄重用**：成功紀錄列出「用這份清單再配對」，從 `roster_snapshot` 還原參與者＋對象預填到填清單頁（`/match/new/fill?from_record=...`），可改後重跑；擁有者限定
- 全 UI 用詞「名單」→「清單」；抽籤方式獨立成「3. 抽籤方式」卡片（不再混在清單來源裡）
- CLI `.targets.yaml` 旁檔向後相容；對象試算表 vs YAML 旁檔 audit 等價（SC-005）
- **核心只動 data_import**（資料匯入職責，教訓 7）；audit schema 不變
- 自動化測試：420 passed, 2 skipped

階段 9 用詞統一「參與者」+ role→participant 全面更名（feature 017 + 018）：

- **使用者用詞**：全 UI／CLI／docs 的「角色」→「參與者」（對象不變）；feature 017
- **內部識別碼**：subject 側 `role`→`participant`（`Role`→`Participant`、`role_id`→`participant_id`、
  DSL 前綴 `role.`→`participant.`、URL `/role/`→`/participant/`）；保留 `Roster`/`roster` 容器
- **audit schema v1.4 → v1.5**：`roster_snapshot.participants`、`allocation_trace[].participant_id`
- **不向後相容（乾淨切斷）**：舊 `role.` 範本／舊 v1.4 audit／舊 URL 不保證可讀（沿用升級清空舊資料）
- 安全加固同批進行（feature 017）：CSP/安全標頭、修反射 XSS 與開放重導向、授權/路徑遍歷、
  token 效期、可選網域白名單；`match.py` 拆分為 match/match_view/match_exports
- 重生全部 7 個 golden（v1.5）；全套件 457 passed

尚未開始：K8s 部署（階段 5）、實際學校場景試行（UI 白話化已就緒，等真人來試）。

> 註：登入是公開網路部署的前置（階段 5）；目前憑 Google OAuth + 個人私有，尚未做組織/網域層級的共享。

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
- **技術棧（已落定）**：
  - 後端：Python 3.11 + FastAPI + Jinja2（伺服器渲染）
  - 前端：Tailwind CSS Play CDN + Alpine.js（CDN-only，**無 Node toolchain / 無 build step / 無 npm**——維持「簡單部署」精神）
  - 持久化：純檔案系統（`data/matches/`、`data/templates/<id>/v<N>.yaml`）

待定：

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

### 階段 3c：稽核報告匯出（PDF）

- [x] 完成（commit `76c9689`，2026-05-25）

<!--
  交付：admin + individual 兩版 PDF；Web 結果頁/個別頁可下載；CLI `matcher report` 指令；
  WeasyPrint 整合 + graceful degrade；技術詞零容忍延伸；core 0 改動。
  前置條件：階段 3a、3b
-->

**成功標準：**

- [x] 稽核報告可匯出為 PDF（Web `/report.pdf` 端點 + CLI `matcher report` 指令；含 admin 與 individual 兩版）
- [ ] 報告依模板 `report_fields` 宣告渲染欄位（**未完成 / 延後**：feature 010 採用固定欄位渲染（標題/紀錄資訊/機制/分配表/志願排名），未實作 `report_fields` schema 解譯；如需要可另開 feature）

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

### 階段 4c：Web UI 機制選擇 + 結果頁志願展示

- [x] 完成（commit `d4697e7`，2026-05-24）

<!--
  交付：Web UI 新建媒合流程加入機制下拉（M0/M1/M2）；結果頁與個別查詢頁
  顯示機制名、處理順序、志願排名與三分支滿足度文案。**填志願仍以 CSV/Excel
  上傳為主**——UI 動態填志願表單拆到階段 4d。
  前置條件：階段 4a、階段 4b
-->

**成功標準：**

- [x] 活動建立時可選 M0 / M1 / M2 機制（下拉，預設 M0；feature 008 D2 決策：三機制全啟用、無 disabled 邏輯）
- [x] 個別查詢頁顯示「您被分到第幾志願」或「由公平抽籤分到」三分支（沿用 audit `preference_rank` + roster_snapshot `preferences` 長度，無新增 audit 欄位）
- [x] Web 與 CLI 在 M1/M2 + 同 seed 下產出 audit 五段逐位元組相同（SC-001 延伸至 M1/M2）

### 階段 4d：Web UI 動態填志願表單

- [x] 完成（commit `6087ffb`，2026-05-24）

<!--
  交付：Web UI 新建媒合流程支援在介面上直接填志願（每位參與者 N 個下拉），
  替代 / 補充 CSV/Excel 上傳路徑。從階段 4c 拆出。
  前置條件：階段 4c
-->

**成功標準：**

- [x] Web 新建媒合流程提供志願填寫表單欄位（每位參與者可即時填寫 1..max_choices 個志願；自動偵測「模板含 schema + roster 全空 + M1/M2」時觸發）
- [x] 表單提交後產出的 audit 與「同樣志願以 CSV 上傳跑出的 audit」逐位元組相同（SC-001 of 4d，整合測試守住）

### 階段 4e：範本創作 UI + 全 UI 用詞白話化

- [x] 完成（commit `5d41473`，2026-05-25）

<!--
  交付：(a) /templates/new 表單建立自訂範本 + YAML 進階模式 + AI Prompt 助手；
  (b) data/templates/ 持久化（每存 = 新版本）+ TemplateRegistry 掃描；
  (c) 全 Web UI 用詞白話化（模板→範本、媒合→配對、M0/M1/M2 → 純抽籤/輪流挑/依志願先後填滿、隨機種子→亂數種子、別稱欄位移除、預設對象從建範本 UI 移除…）；
  (d) Tailwind Play CDN + Alpine.js（兩者 CDN-only，仍維持無 Node toolchain）。
  前置條件：階段 2a（範本系統）
-->

**成功標準：**

- [x] 一般使用者可在 `/templates/new` 不寫 YAML、建立自訂範本並跑配對成功
- [x] 進階模式提供 AI Prompt 複製按鈕（含整份 `docs/template-authoring-guide.md`）
- [x] 全 Web UI 與 CLI 錯誤訊息移除工程師導向詞彙（M0/M1/M2 內部代碼、str/int 型別、別稱、aliases、稽核紀錄 → 完整紀錄、媒合 → 配對 等）
- [x] 自訂範本持久化於 `data/templates/<id>/v<N>.yaml`；重啟後可載入
- [x] 動核心限定於 `template_loader.py`（教訓 7 第 3 種合法情境：模板管理擴充）
- [x] 自訂範本支援編輯（每次儲存產生新版本）+ 版本歷史查看 + 內建範本 Fork（US3，commit `c67c4b3`）
- [x] 配對結果頁可「以當時的範本版本再跑一次」（從 audit.template_snapshot 還原；US4 是 audit 完整性的免費延伸，呼應教訓 3）

### 階段 4f：UI 直接填名單

- [x] 完成（commit `6056f98`）

<!--
  交付：UI 上直接填參與者 / 對象名單，不必先做 CSV 檔。
  策略：純函式組 CSV bytes，走既有 data_import 路徑 → 與「上傳 CSV」5 段 audit bytewise 等價。
  M1/M2 經由 hidden inputs 跳 feature 009 志願頁（既有機制）。
  核心 0 改動：所有變動局限於 `matcher.web` 套件內。
-->

- [x] /match/new 三選一切換：📂 上傳 / ✏️ 直接填 / 📌 過去紀錄（Alpine.js）
- [x] /match/new/fill 動態渲染範本欄位 + /match/run-from-form 提交
- [x] 純函式 assemble_roster_csv_bytes / assemble_targets_yaml_bytes
- [x] UI 與 CSV 路徑 5 段 audit bytewise 等價（SC-002 守門）
- [x] M1/M2 自動跳 feature 009 志願頁

### 階段 4g：移除 default_targets 概念

- [x] 完成（commit `b25af35`）

<!--
  交付：範本不再內嵌對象資料；對象一律在配對時提供。
  動機：使用者明確要求拔黑箱 + UI 填名單頁應透明顯示對象（公平公開原則）。
  破壞性變動：audit schema v1.3 → v1.4；Template dataclass 拔欄位。
  向下相容：舊 YAML 含 default_targets 靜默忽略；舊 v1.3 audit viewer 不主動讀。
-->

- [x] Template dataclass 移除 default_targets 欄位
- [x] template_loader 對舊 YAML 含此鍵靜默忽略（漸進遷移）
- [x] data_import._load_targets 一律要旁檔；錯誤訊息升級
- [x] 內建範本拔除 default_targets；examples 補對應 sidecar
- [x] audit schema_version 升 v1.4，template_snapshot 不再含 default_targets
- [x] UI 填名單頁對象段永遠顯示（移除 requires_targets 條件）
- [x] /match/preferences 攜帶 targets_bytes_b64，志願頁往返不漏 sidecar

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

### 階段 6：登入與資源歸屬

- [x] 完成（merge `30443eb`）

<!--
  交付：Google OAuth 登入 + 資源綁擁有者 + 預設私有 + 範本私有/公開 + 刪除範本；
  個別連結改不可猜 token（免登入、不可枚舉）；CSRF / cookie flags / rate-limit；無 DB。
  前置條件：階段 4（公開網路部署的隱私前置）。詳見 specs/014-auth-ownership。
  註：資料保護「義務」由原則 6 涵蓋（推導自原則 4＋5）；本階段的登入/權限「機制」
  （Google OAuth、簽章 token、rate-limit）則是滿足該義務的務實手段、可替換。
-->

**成功標準：**

- [x] 未登入訪管理頁導向登入；個別 token 連結未登入仍可開（家長路徑不破）
- [x] 使用者只看到自己的資源 + 公開範本 + 內建；跨使用者存取 403
- [x] 範本可切私有/公開；公開範本他人可見可複製不可編輯；擁有者可刪除
- [x] 核心 `src/matcher/*`（非 web）0 改動

### 階段 7：配對失敗可解釋

- [x] 完成（merge `b7f3df3`）

<!--
  交付：資格集合為空時說明「哪條規則刷掉幾組、元兇是誰」；UI 填名單失敗回填保留輸入；
  CLI exit 10 同步診斷；修 teacher-class R003 中英文不一致。
  核心僅動 filter/errors/cli（可解釋性職責）。詳見 specs/015-explain-empty-set。
  前置條件：階段 1（核心引擎）。
-->

**成功標準：**

- [x] 空集合失敗指出元兇規則 + 各規則淘汰數（Web + CLI），無技術 token
- [x] UI 填名單空集合 → 回填名單頁、保留輸入 + 診斷
- [x] teacher-class R003 說明與接受值一致（照說明填得過）
- [x] 成功配對 audit schema 不變；核心僅動 filter/errors/cli

### 階段 8：對象試算表匯入 + 動態範例 + 過去紀錄重用

- [x] 完成（merge `4ae4576`）

<!--
  交付：對象也能用 CSV/Excel 兩檔獨立匯入（不必寫 YAML 旁檔）；依範本 schema
  即時產生範例試算表（涵蓋自訂範本、永不漂移）；成功紀錄可「用這份清單再配對」
  （從 roster_snapshot 預填填清單頁）。核心僅動 data_import（資料匯入職責，教訓 7）。
  前置條件：階段 2b（資料匯入）、階段 4f（UI 填清單預填機制）。詳見 specs/016-targets-spreadsheet-import。
-->

**成功標準：**

- [x] 對象可用 CSV/Excel 匯入（參與者、對象各一檔）；編號可省略自動生成；中文表頭對齊
- [x] 範例試算表依範本 schema 即時產生，涵蓋自訂範本且永遠與當前 schema 同步（教訓 12）
- [x] 對象試算表 vs YAML 旁檔 audit 逐位元組等價（SC-005）；CLI 旁檔向後相容
- [x] 成功紀錄可重用清單再配對（擁有者限定，從 audit roster_snapshot 還原預填）
- [x] 核心僅動 data_import；audit schema 不變

### 階段 9：用詞統一「參與者」+ role→participant 全面更名

- [x] 完成（feature 017 安全加固/用字 + feature 018 識別碼更名）

<!--
  交付：(017) 安全加固 + 全 UI 用字「角色」→「參與者」；(018) 內部識別碼與對外契約
  role→participant（audit schema v1.5、DSL participant.、URL /participant/）。
  破壞性：不向後相容（升級清空舊資料）。屬資料模型/schema 演進，獨立成 feature（教訓 9）。
  前置條件：階段 8。詳見 specs/018-rename-role-participant。
-->

**成功標準：**

- [x] 對外用字「參與者 ↔ 對象」一致（UI/CLI/docs）；內部識別碼 subject 側無 role 殘留
- [x] audit schema 升 v1.5（participants / participant_id）；同 seed bytewise 可重現仍成立（原則 2）
- [x] 舊 role. 範本明確報錯、舊 URL 404（乾淨切斷，無向後相容）
- [x] 安全加固：CSP/安全標頭、修 XSS/開放重導向、授權/路徑遍歷、token 效期、網域白名單
- [x] 全套件 457 passed；7 個 golden 以 v1.5 重生

## Backlog（待真實需求再做，未排程）

<!--
  這裡放「想到但目前用不到」的點子，避免憑想像提前做（教訓 8）。
  進入正式階段前要有實際觸發條件（不是「感覺可能要」）。
-->

### 範本列表管理增強：搜尋 / 排序 / 星標

- **觸發條件**：公開範本累積到數十個、使用者反映「找不到範本」時才做。目前量級（少數內建 + 自己建的幾個）用不到。
- **搜尋 / 排序**：便宜，不碰儲存架構（名稱/代號/描述關鍵字過濾 + 依名稱/時間/內建排序）。可先做。
- **星標 / 我的最愛**：最重。是「每個使用者的偏好狀態」，目前系統無此層（per-user 狀態只有 session）。要做需引入使用者偏好持久化（如 `data/users/<email>/...` sidecar），建議連同其他「個人設定」一起評估，非單點加。
- **判準**：呼應教訓 8——沒有「一堆範本要找」的真實場景前，不做。

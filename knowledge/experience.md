# 經驗

<!--
  這份文件記錄從開發過程中蒸餾出的教訓——不是 changelog，
  而是應該影響未來決策的模式。

  每個教訓記錄「理論」和「現實」之間的落差。
  保持簡短、可操作。詳細的事件記錄放在 knowledge/history/。
-->

## 教訓

### 黃金檔比對是「可重現性」的最強驗證手段

- **理論說**：階段 1 SC-001 要求「同樣輸入產出相同結果」，本來只打算用結構性比對
  （deep-equal）驗證稽核紀錄。
- **實際發生**：研究階段（research.md R-008）改採「逐位元組比對 JSON 黃金檔」後，
  發現它能多抓兩類隱藏問題——欄位順序不穩定（→ 用 `sort_keys=True` 修正）、
  時間戳潛入紀錄破壞跨機器重現（→ `generated_at` 固定為 `null`）。
  這些問題在結構性比對下會通過，但在實務上會讓兩台機器產出「結構相同但 bytes 不同」
  的稽核檔，PR diff 不再有意義。
- **解決方式**：所有可重現性測試一律走黃金檔逐位元組比對；序列化參數固定為
  `ensure_ascii=False, sort_keys=True, indent=2`，時間戳一律為 null。
- **教訓**：對「可重現」要求嚴格的系統，逐位元組比對 > 結構性比對。
  未來機制（M1 RSD、M2 Boston）的稽核驗證**必須沿用同樣手法**。
- **來源**：specs/001-core-allocator/research.md R-006、R-008；
  tests/integration/test_reproducibility.py。

### 介面預留「拒絕執行」的參數，是契約穩定的廉價手段

- **理論說**：原本考慮階段 1 不暴露 preferences 參數，等階段 4 再加，
  以求介面最簡。
- **實際發生**：階段 1 即把 `preferences?` 加入 `allocate(...)` 介面，但在 M0 機制
  下若收到非空 preferences 就明確拒絕（exit 17）。這做了兩件事：(a) 階段 4 不必
  動介面、所有現存呼叫端不需要重寫；(b) 使用者不會誤以為現在已支援志願。
- **解決方式**：介面預留 + 明確拒絕的三段式錯誤訊息（「不接受 / 原因 / 建議」）。
- **教訓**：對未來會擴充的能力，「**參數預留 + 拒絕分支**」比「之後再加參數」
  在介面相容性上便宜得多——只要拒絕訊息夠明確指引未來路徑，使用者不會誤判。
- **來源**：specs/001-core-allocator/spec.md User Story 3；
  src/matcher/pipeline.py `run_match` 中的 PreferencesNotSupported 判斷。
  階段 2a 再次驗證：study-group 模板宣告 `preferences_schema`，
  Participant.preferences 內嵌欄位於 M0 機制下被拒絕，無須改動 schema 即支援階段 4 的志願序機制。

### audit schema 演進採「新增可選欄位 + null 表示不適用」最乾淨

- **理論說**：階段 2a 需要把模板資訊寫入稽核紀錄；本來考慮兩條路徑——
  (A) 引入新的 audit schema 版本（如 2.0），與舊版分流；
  (B) 維持舊 schema、只在使用模板時才出現 `template_snapshot` 欄位。
- **實際發生**：兩條都不夠好。(A) 過度重型，影響所有既有測試；
  (B) 違反「相同 schema 下同一結構」的嚴格性，會讓稽核紀錄消費端難以判斷格式。
  最後採第三條路——schema 由 v1.0 升 v1.1（小版號），**新增可選欄位**
  `template_snapshot`（使用模板時為完整序列化、不使用時固定為 `null`）。
- **解決方式**：在 build_audit_record 加 `template` 參數預設 `None`；
  audit_schema_version 從 "1.0" 直接升到 "1.1"；既有黃金檔重生成一次（值不變、僅多一欄）。
- **教訓**：稽核 schema 的演進，**「新增可選欄位 + null 表示不適用」優於版本分流**——
  消費端永遠看到同一份 schema，「不適用」用 null 而非「欄位缺失」表達。
  未來新增 M1/M2 機制時，`mechanism_trace`、`preferences_resolved` 等欄位應走同樣模式。
- **來源**：specs/002-template-system/research.md R-009、R-010；
  src/matcher/audit.py `build_audit_record`；
  contracts/audit-schema-v1.1.json。
  階段 2b 再次驗證：audit schema 從 v1.1 升 v1.2 新增 `import_metadata` 欄位
  （YAML 路徑為 null），完全沿用此模式。
- **例外（nuance，feature 018）**：本教訓的「只增不破」是**常態**，不是鐵律。
  feature 018 為了用字一致（role→participant）做了**破壞性更名**——audit v1.4→v1.5、
  鍵名 `roles`→`participants`/`role_id`→`participant_id`、重生全部 golden、不向後相容。
  這是**刻意的例外**：當「術語一致 / 消除認知斷層」的價值夠高、且採「升級清空舊資料」策略時，
  破壞相容是可接受的——但必須是顯式決策（獨立 feature、spec 寫明「乾淨切斷」），不可順手破壞。
  判準：增欄位 → 走只增不破；改/刪既有鍵 → 視為破壞性，要顯式決策 + 版本升號 + golden 重生。

### 「資料來源無關性」隱藏的 ID 等價門檻

- **理論說**：階段 2b 要做到 SC-001「CSV / Excel / YAML 三路徑稽核紀錄五段相同」，
  本以為只要結構化資料相同（屬性、規則、容量、seed 全等）就成立。
- **實際發生**：CSV 載入器原本依列序自動生成 participant id（R001、R002…），
  而既有 YAML 名單用的是 T01、T02…。即使所有屬性都對齊，`assignment` 與 `qualified_set`
  的 key 仍不同——bytewise 比對永遠失敗。發現「資料結構等價」不蘊含「id 等價」。
- **解決方式**：CSV/Excel 載入器加可選 `id` 欄位（亦接受別名「編號」）；
  若提供則使用、否則才自動生成。spec/contracts 的「CSV 不能含 id 欄位」條款於 implement
  階段被推翻——這個偏離已誠實揭露於本 feature 的完成摘要中。
- **教訓**：對「資料來源無關性」要求嚴格的系統，**外部 id 必須可由匯入來源攜帶**——
  自動生成的 id 適合 quick demo，但會阻擋「跨來源等價」目標。設計匯入介面時，
  「可選 id 欄位」是低成本的必要保留位。
- **來源**：specs/003-data-import/spec.md SC-001、contracts/csv-format.md（已陳舊，
  待 minor commit 同步）；src/matcher/data_import.py `_find_id_header`、`_build_participants`；
  tests/integration/test_csv_import.py `test_csv_yaml_equivalence_core_fields`。

### library + CLI + Web 三入口共用核心的價值

- **理論說**：階段 3a 要做完整 Web UI，原本可能擔心要重寫匯入、媒合、稽核等
  「Web 友善版本」（例如 async 化、加 ORM、改錯誤類別格式以對接 HTTP），
  動到既有核心模組。
- **實際發生**：實際實作中，**完全沒動 `src/matcher/{rules,filter,allocator,pipeline,audit,data_import,template_loader,...}`**——
  Web 層僅在其上加 FastAPI HTTP wrap + Jinja2 樣板渲染 + MatchStore 持久化。
  142 個測試含 116 個既有測試 100% 通過；CLI 介面行為完全不變。
- **解決方式**：嚴格遵守「library = pure Python；CLI = library 之上的命令列 wrap；
  Web = library 之上的 HTTP wrap」分層。所有與「輸入來自哪裡」「輸出怎麼呈現」
  相關的邏輯集中在外層；核心只做「規則化資料 → 媒合 → 稽核」。
- **教訓**：核心 library 設計得夠純（無 IO、無 framework 假設），上面可以無痛加入
  任意數量的入口（CLI、Web、未來的 gRPC / 桌面 app）。**「入口無關性」是「資料來源無關性」
  （教訓 4）在更高層的延伸**——未來加任何新入口時，第一個檢查點是
  「核心 library 不需要動」。若需要動 → 表示分層不夠純。
- **來源**：specs/004-web-ui-main 整個 feature；142 測試結果；
  `src/matcher/web/` 完全新增、`src/matcher/{filter,allocator,pipeline,...}` 完全未動。
  階段 3b 再次驗證：個別查詢視圖（commit `f8ac328`）加 169 行新測試，
  仍然 0 動核心模組——「入口無關性」越來越穩固。

### 技術詞零容忍可以作為可自動化的 UX 測試

- **理論說**：階段 3b 的個別查詢頁要「面向一般教師、避免技術名詞」（原則 5）。
  傳統作法是仰賴人工 UX 審查——找一位非工程師讀過頁面、回報哪裡看不懂。
  問題是這不可重複、無法在 CI 跑、且任何文案修改都需要重審。
- **實際發生**：實作中發現「面向一般教師」這個抽象目標**可以化約為硬規則**：
  「HTML response 不含 `filter_trace` / `allocation_trace` / `qualified_set` / `random_index` /
  `exit_code` 等技術 token，且不匹配 `participant\.\w+` / `target\.\w+` 等正則 pattern」。
  這條規則可用 `assert token not in r.text` + `re.search` 自動檢驗，
  任何不小心讓技術詞洩漏到 UI 的修改都會立刻被測試擋下。
- **解決方式**：在 spec 寫明 `FORBIDDEN_TECHNICAL_TOKENS` 與 `FORBIDDEN_PATTERNS` 清單；
  在多個整合測試中（個別查詢頁、3 種錯誤頁）皆斷言「response 不含任一禁用 token / 不匹配任一禁用 pattern」。
- **教訓**：當「使用者體驗」目標可以化約為「特定字串/模式不應出現」時，
  **自動化 lint 比 UX 評審更可靠且零成本**。這是教訓 1「黃金檔比對」的進一步延伸：
  把「人類判斷」轉化為「字串/模式禁止表」是個強而簡單的工具。
  適用範圍不限介面文案——也可用於：「audit 不應含密碼/個資」「commit 訊息不應含 TODO」
  「規格文件不應含 NEEDS CLARIFICATION 殘留」「PR 描述應含 'Test plan' 字眼」等。
- **來源**：specs/005-individual-view/spec.md FR-003、SC-002；
  tests/integration/test_web_individual_view.py 的 `FORBIDDEN_TECHNICAL_TOKENS`、`FORBIDDEN_PATTERNS`、
  `test_no_technical_tokens_in_individual_view`、`test_error_pages_have_no_technical_tokens`。

### 核心職責 vs 周邊整合的分層邊界

- **理論說**：教訓 5「library + CLI + Web 三入口共用核心」似乎暗示「核心永遠不動」。
  階段 2a–3b 共 4 個 feature 都做到了。階段 4a 卻**動了核心** 5 個模組
  （allocator / pipeline / audit / errors / cli）——這是違反教訓 5 嗎？
- **實際發生**：實作中發現，動核心的合法性取決於變更的**性質**：
  - 階段 4a 加 M1 RSD 是「**新分配機制**」——核心職責「過濾 → 分配」的擴充
  - 同樣會動核心的還會有：M2、新規則型態、新稽核欄位、新隨機性來源
  - 反之，階段 2b 加 CSV/Excel 匯入、3a/3b 加 Web UI、3c 加 PDF 匯出
    都是「**新入口 / 新格式 / 新呈現視圖**」——周邊整合，不應動核心
- **解決方式**：精確化教訓 5 的判準——**「動到核心的理由必須是『核心職責的擴充』」**。
  審視 PR 時用一個簡單問題判斷：「這次變更，library 本身的能力（不考慮 IO 介面）
  變強了嗎？」若答「是」（如新增 allocate_m1）→ 動核心合法；若答「否」
  （如加新 Web 端點、新檔案格式 reader）→ 應限於外層、不動核心。
- **教訓**：分層純度不是「核心永遠不動」，而是「**動核心的理由必須對應核心職責**」。
  作為 PR 審查的硬規則：動到 `src/matcher/{rules,filter,allocator,pipeline,audit,rng}`
  的 PR 必須在描述中明確指出「擴充了哪個核心職責」；否則退回外層實作。
- **來源**：specs/006-m1-rsd-mechanism；commit `91c916a` 動核心 5 個模組；
  對比 commits `586fd93` / `0384021` / `f8ac328` 三個 feature 皆 0 動核心。

### 主觀品質的迭代需要對照標的，否則會越改越糟

- **理論說**：使用者反饋「感覺不對」時，靠多次 iteration 收集回饋就能逐漸對齊；
  自動化測試全綠就代表這次修改是正面進展。
- **實際發生**：feature 011 UI 反覆失敗 6+ 輪——「使用者不滿意 → 我改 CSS → 更糟」。
  根本問題：(a)「對 / 不對」純主觀，沒參考標的時兩端各自想像不同，每次 iteration
  其實在不同維度上跑；(b) 既有測試（9 個整合測試）只驗結構（routes 回 200、HTML
  含某字串、表單 POST 成功），完全不驗視覺品質——「測試全綠」給了虛假安全感，
  讓我繼續憑感覺大改而不停手。連續換了 3 套 CSS 方案（自寫 → Pico.css → Tailwind）
  才稍有起色，仍未真正讓使用者滿意。
- **解決方式**：第 3 輪後改變策略——主動向使用者索取「截圖 / 參考連結 / 具體哪段哪問題」
  作為對照標的，停止「猜測 → 大改」循環；無對照時誠實標示「測試綠 ≠ 品質好，
  我無法判斷方向」，並提出「退回」或「另開 feature 重做」選項，而非繼續瞎改。
- **教訓**：**主觀品質的工作**（UI 視覺、文案、API 命名、錯誤訊息可讀性等）
  **需要對照標的才能 iterate**。無對照時：(a) iteration 會放大噪音而非降噪；
  (b) 自動化測試覆蓋結構但不覆蓋主觀品質，要主動標示「綠 ≠ 好」；
  (c) 比起「再改一次看看」，更該主動向 user 索取對照（截圖、參考、具體描述）或
  誠實提議退回。同樣 pattern 適用：API 命名（「怪」要具體 use case）、
  錯誤訊息可讀性（「不友善」要具體場景）、文案（「不通」要範例）。
- **來源**：specs/011-template-author-ui Phase 3 後的 UI 反覆；
  tests/integration/test_template_authoring_simple.py（9 測試持續全綠卻視覺反覆失敗）；
  本輪對話從 commit `ff09842` 之後到下次 commit 之間的所有 UI 嘗試。

### 重大 data model 變動要獨立成 feature，不要塞進其他 feature 的 polish

- **理論說**：feature polish 階段是收尾，把「沒做完的小事」清掉就好；
  使用者反饋「順便改 X」聽起來合理就順手做。
- **實際發生**：feature 012（UI 直接填名單）的 polish 階段，使用者要求順便移除
  `default_targets` 概念。直覺看「就是拔個欄位」似乎小，實際盤點：動到 5 個核心檔
  + audit schema 升版（v1.3 → v1.4）+ 35 個測試呼叫點 + 4 個 golden audit + 內建範本
  + examples sidecar 補檔——光是中途的測試紅燈就 78 個。若塞進 012 polish，會跟 UI 工作
  交織爆炸，無法區分「UI 改壞了」vs「拔欄位改壞了」，且打破核心 0 改動的承諾。
- **解決方式**：在 polish 邊界拒絕，明確說「這是 feature 級別的變動」，走 spec-kit
  完整流程開 feature 013。寫 spec 時才發現需要：(a) audit schema 升版的相容策略
  (b) 舊 YAML 含 default_targets 的靜默忽略決策 (c) examples sidecar 補檔
  (d) /match/preferences hidden input 攜帶 sidecar bytes——這些都是寫 plan/research
  才浮現的隱藏需求，邊做邊發現會反覆走回頭路。
- **教訓**：判準「是否塞 polish」用變動的**爆炸半徑**而不是直覺感覺：
  - 動 data model（dataclass 加減欄位、audit schema 升版）→ 一定獨立 feature
  - 動到 ≥ 3 個核心檔 → 一定獨立 feature
  - 需要新增向下相容決策（舊資料如何讀）→ 一定獨立 feature
  - 預估改 ≥ 10 個測試檔 → 一定獨立 feature
  即使「合法核心變動」（呼應教訓 7），也應該獨立排程，讓 spec-kit 的 research /
  contracts 階段把隱藏複雜度先浮現出來。
- **來源**：specs/013-remove-default-targets；對比 specs/012-web-roster-form 的核心 0
  改動成績；commit `b25af35` 49 檔變動（含 audit schema v1.4 升版）。

### 觀察工具的回報 ≠ 真實狀況，視覺 bug 判斷要回到 raw HTML / 截圖

- **理論說**：用 mcp browser 工具的 `read_page`（accessibility tree）抓頁面結構，
  就能可靠判斷 UI 是否有視覺 bug。
- **實際發生**：對 matcher 做一輪 UI/UX 批評時（commit `601955d`），用 accessibility tree
  讀結果頁與個別查詢頁，回報「**4 個真實 bug**」：(a) 結果頁「使用範本：教師-班級配對（）」括號
  內 id 跑版、(b)「建立時間」標籤遺漏、(c) 過去紀錄表頭只有 2 欄、(d) 個別查詢基本資訊
  欄位值對不上 label。動手修時 grep 樣板原碼才發現**全部都是正確的**——accessibility tree
  把 `<strong>`、`<code>` 等 inline 元素拆成獨立 children 後，父段落文字看起來缺一塊
  （例：`<p><strong>使用範本</strong>：教師-班級配對（<code>teacher-class</code>）</p>`
  被 tree 拆成 `generic "：教師-班級配對（）"` + `generic "使用範本"` + `generic "teacher-class"`，
  容易誤判成括號是空的）。視覺上原本就沒問題。
- **解決方式**：判斷視覺 bug 前先用以下其一交叉驗證：
  - `javascript_tool` 直接讀 `document.querySelector(...).innerText` 抓真實文字
  - 截圖（直接看視覺輸出）
  - 直接 grep / read 樣板原碼，從 source-of-truth 倒推
  四個誤判中三個 commit 前已自我修正，但仍浪費了一輪「找 bug → 發現不是 bug」的精力。
- **教訓**：**工具給的「狀態回報」是工具的視角，不是真實狀況**。
  - accessibility tree 為輔助技術設計，會把 inline 元素扁平化——適合判斷「有沒有可達」
    但不適合判斷「視覺上長什麼樣」
  - 同 pattern 適用：log 輸出 ≠ 程式實際行為（log 可能遺漏關鍵路徑）、
    test 報告 ≠ 功能正確（測試只覆蓋斷言到的部分）、靜態分析 ≠ runtime 真實
  - 規則：對「視覺 / 主觀品質」議題，**回到最原始的呈現層**（截圖、innerText、原始碼）
    才能判斷；對「結構 / 邏輯」議題，工具回報可採信
- **來源**：commit `601955d` UI/UX 批評輪；最初列了 4 個「視覺 bug」事後發現全是
  accessibility tree 解讀問題。與教訓 8（主觀品質需對照標的）互補：教訓 8 講「無對照
  會放大噪音」，本則講「**錯誤的對照（誤把工具回報當真實）也會放大噪音**」。

### 簽章 token 取代索引檔，是「無狀態鑑權 + 不破壞無 DB 架構」的廉價解

- **理論說**：要做「不可猜、不可枚舉的個別查詢連結」，直覺是產一個隨機 token，
  存一張 `token → (資源 id, 參與者 id)` 對應表，查詢時去表裡找。
- **實際發生**：feature 014 要在「不引入 DB」的約束下做這件事。隨機 token + 對應表
  會逼出一個新的持久化結構（索引檔），帶來並發寫入、清理、跨副本同步的麻煩——等於
  偷渡一個迷你資料庫。改用 **itsdangerous 簽章**把 `(match_id, participant_id)` 直接簽進 token
  後：驗章成功就「解出」目標，**完全不需要儲存**。安全性來自 server secret（簽不出 =
  進不來），不靠保密 payload。一個函式對（sign/verify）取代整套索引機制。
- **解決方式**：`URLSafeSerializer(SECRET, salt).dumps([match_id, participant_id])` → `/r/{token}`；
  開啟時 `loads` 驗章還原目標。session 也用同手法（簽章 cookie，無伺服器端 session）。
- **教訓**：當你需要「可驗證但不可偽造的識別碼」時，先問「能不能用**簽章**取代**儲存**」。
  簽章（HMAC / itsdangerous / JWT）把「狀態」編碼進 token 本身，換來無狀態、免索引、
  免並發處理、天然跨副本——尤其在「不想引入 DB」的約束下，這幾乎總是更輕的解。
  反模式檢查：發現自己要「為了查 token 而建一張表」時，停下來想簽章。
- **來源**：specs/014-auth-ownership；`src/matcher/web/security.py` sign/verify_participant_token；
  research.md D3；對比「隨機 token + 索引檔」被否決。同案另一收穫：auth 作為周邊整合，
  全程 `src/matcher/*` 核心 0 改動（再次印證教訓 7）。

### 失敗時別把已算出的診斷資料丟掉；範本「說明」與「接受值」必須一致

- **理論說**：失敗就是失敗，丟一個錯誤碼/訊息出去即可；至於「為什麼失敗」，使用者自己看規則。
- **實際發生**：真實使用者（不是我演的）用 teacher-class 跑配對，得到「資格集合為空：所有組合皆未通過」
  就卡住——畫面不說是哪條規則殺光的、該改什麼。挖下去發現兩件事：
  (a) `filter_qualified` **其實早就逐組算好了 filter_trace**（誰過了哪些規則、被哪條刷掉），
      卻在空集合時 `raise` 把它整份丟棄——一個標榜「可解釋」的工具，最常見的失敗反而最不可解釋。
  (b) 內建 teacher-class 的 R003「說明」寫「雙語、stem、藝術」，但 `in` 算子實際只認英文
      `bilingual/stem/arts`——使用者照「說明」填中文，必然全被刷掉。**說明與接受值不一致＝陷阱**。
- **解決方式**：
  - 讓 `QualifiedSetEmpty` 例外**攜帶**那份 trace + 規則淘汰統計（誰刷掉幾組 + 元兇規則），
    上層（CLI/Web）就能說「『班級特色』把 15/15 組都刷掉了，請檢查這項的值」。零新依賴、
    成功 audit schema 不動（診斷只走失敗路徑）。
  - R003 接受值改成與說明一致的中文。
- **教訓**：
  1. **失敗路徑也是產品的一部分**——尤其當「可解釋」是核心賣點，最常見的失敗更要可解釋。
     程式內部若已經算出診斷資訊（trace、中間結果），**別在 raise / return 時丟掉**，
     用例外 payload 或回傳結構帶出來給上層用。
  2. **任何「說明文字」與「實際接受/驗證的值」必須一致**。描述寫中文、程式比對英文，
     是會讓使用者 100% 踩雷的設計。範本、表單、API 文件皆適用。
  3. 這類洞**只有真實使用者會踩到**——再次印證：演使用者（教訓 8/10）抓不到「我照說明做卻失敗」
     這種信任崩潰點，要真人來試。
- **來源**：specs/015-explain-empty-set；`filter.py` rejection_summary + QualifiedSetEmpty 攜帶診斷；
  使用者實測 data/matches 某筆 `QualifiedSetEmpty` 失敗紀錄。核心僅動 filter/errors/cli（教訓 7）。

### 範例「動態依 schema 產生」優於維護靜態檔——自動涵蓋未來、永不走鐘

- **理論說**：要給使用者「填寫範例」，就準備幾份靜態範例檔（每個內建範本一份）放著供下載。
- **實際發生**：feature 016 要為「對象試算表匯入」提供範例。原本 spec 寫「提供內建範本的靜態範例檔」，
  使用者一句「能不能動態依照範本提供範例」點醒——**靜態檔有兩個致命弱點**：
  (a) 只涵蓋內建範本，使用者自己建的自訂範本沒有範例；
  (b) 範本改了欄位，靜態範例就**走鐘**（與實際 schema 不一致，反而誤導，正是教訓「說明與接受值要一致」的近親）。
  改成「依範本 schema 即時產生範例」（表頭 = 範本屬性的中文顯示名 + 型別提示列）後：任何範本（含自訂）
  都有對應範例、且永遠與當前 schema 同步、零維護。
- **解決方式**：`example_gen.py` 純函式依 `template.attributes` 組出 CSV/Excel bytes；
  端點 `/templates/{id}/example/...` 即時回傳。不存任何靜態範例檔。
- **教訓**：當「示範/範例/樣板」是從某個**結構（schema）**衍生出來的，**優先「從結構動態產生」而非「手寫靜態副本」**。
  動態產生：(a) 自動涵蓋所有現有與未來的結構實例（含使用者自訂）；(b) 永遠與來源同步、不會漂移；
  (c) 零維護。代價是「不保證可直接跑」（範例教格式，非可執行資料）——但這通常是可接受的取捨。
  同 pattern 適用：API 範例請求、設定檔範本、表單預填說明。反模式檢查：發現自己在「為每個 X 手寫一份範例」時，
  問「能不能從 X 的定義自動生出來」。
- **來源**：specs/016-targets-spreadsheet-import；`src/matcher/web/example_gen.py` + `/templates/{id}/example/` 端點；
  使用者一句「動態依範本提供範例」改變設計方向。

### 公開網路安全加固是周邊整合；安全是原則 6 的首次實證

- **理論說**：要把工具放上公開網路承載學生個資，安全加固聽起來像要動到核心、或得重寫一堆東西。
- **實際發生**：feature 017 一輪加固（CSP/安全標頭、修反射型 XSS 與開放重導向、`owner=None` 授權
  fail-open、路徑遍歷清洗、token 效期、可選網域白名單、SESSION_SECRET production 防呆）
  **全程 `src/matcher` 0 改動**——全部落在 `matcher.web`，再次印證教訓 7「安全/部署＝周邊整合」。
  同時這是**原則 6（資料保護）的首次實證**：原則 6 講的「保護義務」在這裡化為具體機制（私有預設、
  跨使用者隔離、機密不外洩）。另一收穫：CSP **無法做到 strict**——樣板有原生 `onclick`、且 Tailwind
  Play CDN/Alpine 需 `unsafe-eval`，最後保留 `unsafe-inline`；且「測試全綠 ≠ 瀏覽器對」（CSP 會擋
  行內處理器、前端快取問題，後端測試抓不到）——這是教訓 10 在前端/部署的又一實例。
- **解決方式**：安全標頭 middleware + `tojson_attr` 修 XSS + `_safe_next` 擋開放重導向 + `safe_fs_id`
  清洗路徑；務實 CSP（擋外部 script 來源 + frame-ancestors，接受 unsafe-inline）。
- **教訓**：(1) 安全/部署是周邊整合，第一檢查點仍是「核心要不要動」（多半不用）。(2) 機制（OAuth、
  CSP、token）是滿足原則 6 的**可替換手段**，原則約束的是「保護義務」本身。(3) 前端/安全的驗收要
  回到真實瀏覽器，不能只看後端綠燈（教訓 10）。
- **來源**：feature 017（branch 017-security-hardening）；`src/matcher/web/app.py` 安全標頭、
  `security.py` token 效期、`routes/auth.py` `_safe_next`/網域白名單；核心 0 改動。

### 部署「實機才見真章」；依賴的 dev/執行期邊界要在打包前釐清

- **理論說**：本機/CI 測試綠、`kubectl apply` 成功、pod `Running`，就代表部署好了。
- **實際發生**：feature 020 部署到遠端 k3s，連踩三個「只有實機才會知道」的點：
  (a) 節點是 **amd64**，本機 Apple Silicon build 出 arm64 → `ImagePullBackOff: no match for platform`，
      要 `docker buildx --platform linux/amd64`；(b) 資源要進指定 **namespace**（`matcher`），不是 default；
  (c) **httpx 是執行期依賴**——Authlib OAuth callback 用它，但原本只列在 `[dev]`，`--no-dev` 映像會缺它、
      登入在 callback 才掛。其中 (c) 是寫 plan 的 research 階段就**推理出來**的（spec-kit 的價值），
      (a)(b) 則是 apply 後看 pod 事件才現形。
- **解決方式**：buildx 跨架構 + manifests 帶 namespace；httpx 從 `[dev]` 移到 `[project.dependencies]`
  （`pyproject` 屬專案設定、非 `src/matcher`，不破壞核心 0 改動）。
- **教訓**：(1) 「pod Running ≠ 服務正常」「apply 成功 ≠ 能用」——部署驗收要實跑（開頁面、走登入、刪 pod
  驗持久化），這是教訓 10 的部署版。(2) **依賴的「執行期 vs 測試期」邊界**容易被忽略：某套件只在測試裝
  ≠ 它只在測試用（Authlib 的 httpx 是反例）。打包 production 映像前先問「拔掉 dev extras 還跑得起來嗎」。
  (3) 跨架構（build 機 ≠ 部署機）是遠端叢集的常見坑，預設就 `--platform` 指定目標架構。
- **來源**：feature 020（specs/020-k8s-deploy）；`Dockerfile`、`deploy/k8s/*`、`pyproject.toml` httpx 移位；
  節點 `tew`（amd64 公網）。

### 「空＝不設限」做成明確選項，而非隱式行為——可解釋 > 魔法

- **理論說**：規則欄位沒填值，系統「聰明地」自動當作不設限就好，不用麻煩使用者。
- **實際發生**：真實使用者問「我沒填值代表沒有特別約束，怎麼辦？」——當時「跨側包含」規則對空/缺值是
  報錯或刷光（與「沒填=不限制」的直覺相反）。可以做成「一律隱式：空就放行」，但那又是一種**魔法**
  （正是教訓 11「說明與行為要一致」、教訓 10「隱式判斷易誤判」的陷阱根源）。使用者主動提議
  「**可以有一個打勾的選擇**」。最後做成 `empty_ok` checkbox（預設關），勾選才「空=不設限」。
- **解決方式**：`ParticipantInTargetField` 加 `empty_ok`（預設 False、golden 不變）；UI 一個 checkbox +
  白話說明 + docs。對比 feature 019 的「auto 模式靠型別自動判斷」也補上「可手動指定模式」的明確覆寫。
- **教訓**：當某個行為有「直覺但有歧義」的語意（空=不限制 vs 空=不符；list 對 list 要交集 vs 子集），
  **與其隱式猜，不如給明確、預設安全的開關**，讓使用者顯式選擇。這直接服務原則 1/5（可解釋、對使用者
  透明）：使用者看得到、選得到，行為才可預測。反模式檢查：發現自己在程式裡「貼心地自動處理空值/特例」時，
  問「這該不該是使用者明確選的選項？」
- **來源**：feature 021；`rules.py` `ParticipantInTargetField.empty_ok` + UI checkbox；
  使用者一句「可以有一個打勾的選擇」定調設計。

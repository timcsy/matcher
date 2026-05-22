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
  Role.preferences 內嵌欄位於 M0 機制下被拒絕，無須改動 schema 即支援階段 4 的志願序機制。

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

### 「資料來源無關性」隱藏的 ID 等價門檻

- **理論說**：階段 2b 要做到 SC-001「CSV / Excel / YAML 三路徑稽核紀錄五段相同」，
  本以為只要結構化資料相同（屬性、規則、容量、seed 全等）就成立。
- **實際發生**：CSV 載入器原本依列序自動生成 role id（R001、R002…），
  而既有 YAML 名單用的是 T01、T02…。即使所有屬性都對齊，`assignment` 與 `qualified_set`
  的 key 仍不同——bytewise 比對永遠失敗。發現「資料結構等價」不蘊含「id 等價」。
- **解決方式**：CSV/Excel 載入器加可選 `id` 欄位（亦接受別名「編號」）；
  若提供則使用、否則才自動生成。spec/contracts 的「CSV 不能含 id 欄位」條款於 implement
  階段被推翻——這個偏離已誠實揭露於本 feature 的完成摘要中。
- **教訓**：對「資料來源無關性」要求嚴格的系統，**外部 id 必須可由匯入來源攜帶**——
  自動生成的 id 適合 quick demo，但會阻擋「跨來源等價」目標。設計匯入介面時，
  「可選 id 欄位」是低成本的必要保留位。
- **來源**：specs/003-data-import/spec.md SC-001、contracts/csv-format.md（已陳舊，
  待 minor commit 同步）；src/matcher/data_import.py `_find_id_header`、`_build_roles`；
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

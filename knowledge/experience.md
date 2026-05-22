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

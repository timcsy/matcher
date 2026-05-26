# Research — 配對失敗可解釋

## D1：診斷資料怎麼帶出來 → 附到 QualifiedSetEmpty 例外

**Decision**：`filter_qualified` 在資格集合為空時，把 filter_trace 與 rule_stats
附到 `QualifiedSetEmpty` 例外（`err.trace`、`err.rule_stats`、`err.culprit`），再 raise。

**Rationale**：trace 已在 filter 內算好；失敗時 UI 輸入未持久化，唯有在「算出當下」帶出
才不需重算或重存。例外攜帶 payload 是最小侵入——不改 audit schema、不改 pipeline 流程。

**Alternatives**：
- ❌ 把空集合改成「成功但 assignment 全空」：破壞 exit 10 契約與大量測試
- ❌ Web 層重跑 filter：失敗時 roster 未持久化，無從重跑
- ❌ 寫進 audit：成功 audit schema 會被牽動，違反 FR-007

## D2：「元兇規則」的定義 → 失敗最多組的規則（算全部失敗，非僅首敗）

**Decision**：`rejection_summary(trace, ruleset)` 對每個 (角色,對象) 組合，
用 `matched_rules` 的補集得「這組沒過的所有規則」，逐一計數；
回 `{rule_id: 沒過的組數}` + total_pairs + culprit（計數最大者；並列時都列）。

**Rationale**：trace 既有的 `failed_rule` 只記「第一條沒過的」（短路），會低估後面的規則。
改用 `matched_rules` 補集能算出「R003 在 15 組裡卡了 15 組」這種完整圖像，對使用者更有用。
純函式、可同時服務 CLI 與 Web。

**Alternatives**：
- ❌ 只用 failed_rule（首敗）計數：規則順序影響統計，誤導

## D3：CLI 診斷輸出 → _die 針對 QualifiedSetEmpty 多印幾行

**Decision**：`_die` 檢查 `isinstance(err, QualifiedSetEmpty) and err.rule_stats`，
多印「最可能原因：<元兇規則描述>（卡住 N/總 M 組）」+ 各規則計數。退出碼維持 10。

**Rationale**：CLI 也要可解釋（FR-004）；改動局限 _die，不碰流程。

## D4：Web 失敗路徑 → UI 填名單回填、CSV 上傳走 record

**Decision**：
- `run_from_form`（UI 填）：catch QualifiedSetEmpty → 用 feature 014 既有 `_render_fill_form`
  回填使用者剛填的名單 + 顯示診斷紅字（US2 保留輸入）。不存無用的失敗 record。
- `run`（CSV 上傳）：無法回填檔案 → 維持存失敗 record，error dict 帶診斷摘要，
  結果頁失敗分支渲染。

**Rationale**：UI 填的輸入可回填（最佳體驗）；上傳檔無法回填，退而用 record 顯示診斷。
兩條都讓使用者看得到「哪條規則、卡幾組」。

## D5：teacher-class R003 修法 → 改「接受值」為中文（不是改說明）

**Decision**：R003 的 `in` set 由 `[bilingual, stem, arts]` 改為 `[雙語, stem, 藝術]`
（與既有說明「雙語、stem、藝術」一致）；examples/teacher-class/roster.targets.yaml 的
`feature` 值同步改中文；teacher-class 相關 golden 重生。

**Rationale**：使用者直覺會照「說明」填中文；把接受值貼齊使用者直覺，比要使用者背英文代碼好。
「stem」維持原樣（中文語境也常直接寫 stem）。

**衝擊**：teacher-class-baseline / teacher-class-csv / teacher-class-template golden 需重生
（template_snapshot 內嵌規則值改變；assignment 結構不變，因為 example 對象的 feature 同步改）。

**Alternatives**：
- ❌ 改說明為英文：要使用者背 bilingual/stem/arts，違反白話化方向
- ❌ 同時接受中英文：規則語意變模糊，YAGNI

## D6：成功 audit schema 不動（守 FR-007）

**Decision**：診斷只出現在「失敗」路徑（例外 payload、失敗 record 的 error、回填頁），
**完全不碰 build_audit / 成功紀錄結構**。

**Rationale**：SC-005 要求成功 audit 不變；既有 golden 只因 R003 值對齊而重生，
trace/assignment 的「結構」不變。

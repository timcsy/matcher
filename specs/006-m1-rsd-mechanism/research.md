# Research: M1 RSD 分配機制技術選型

**Branch**: `006-m1-rsd-mechanism` | **Date**: 2026-05-23

每項決策以「決策 / 理由 / 替代方案」三段式記錄。

---

## R-001 M1 演算法：Random Serial Dictatorship 標準形式

- **Decision**：採學界標準 RSD：
  1. 以 SeededRandom 對 `roster.roles` 做 Fisher-Yates 洗牌，得到「處理順序」`processing_order`
  2. 依該順序逐位處理每位 role：
     - 取得該 role 的「合格 ∩ 仍有名額」候選 = `qualified_set[role] ∩ {t : capacity[t] > 0}`
     - 從 role.preferences 中依序找第一個落在「合格 ∩ 仍有名額」的 target → 分配；記 `preference_rank` = 該志願在 preferences 中的 1-based 排名
     - 若無（全部志願已滿 / role.preferences 空）→ 從「合格 ∩ 仍有名額」中以 SeededRandom 抽一個 → 記 `preference_rank = null`
     - 若「合格 ∩ 仍有名額」也空 → 該 role 未分配（assignment[role] = None）
- **Rationale**：
  - RSD 標準形式滿足 strategyproof 性質（個別 role 誠實填志願是最佳策略）；對「公平」承諾足夠
  - 「無志願 fallback 到資格內任意」處理混合情境（部分人填志願、部分人沒填）
- **Alternatives considered**：
  - **Top Trading Cycles (TTC)**：更複雜（要處理「初始稟賦」），本場景無此假設
  - **Deferred Acceptance (DA / Gale-Shapley)**：需要雙邊偏好；vision 範圍邊界已排除（屬未來）
  - **隨意處理順序（不洗牌）**：失去公平性

---

## R-002 seed 推導兩種隨機性的順序

- **Decision**：同一 `SeededRandom(seed)` 物件，先 Fisher-Yates 洗 roles，再處理時若需要 fallback 抽籤再呼叫 `randrange`。
  順序固定：洗牌 → 逐位處理（fallback 抽籤穿插其中）。
- **Rationale**：
  - 同一 RNG 物件保證「同 seed → 同序列」；不需引入第二個 seed 或 sub-seed
  - 順序固定使得「逐位元組可重現」成立
- **Alternatives considered**：
  - **兩個獨立 RNG**（一個洗牌、一個 fallback 抽籤）：需要決定兩個 sub-seed 的推導規則，無顯著收益
  - **先 collect 所有 fallback 抽籤位置再批次抽**：增加複雜度，無收益

---

## R-003 `M1RequiresPreferences` 錯誤類別

- **Decision**：新增錯誤類別 `M1RequiresPreferences`，exit code **40**（不與既有 10-17、20-23、30-33 衝突）。
  訊息固定為：「M1 需要至少一位角色提供志願；若無志願請改用 mechanism=M0」+ 三段式（錯誤 / 細節 / 建議）。
- **Rationale**：
  - 沿用既有「明確錯誤類別 + exit code」風格（教訓不變）
  - 40 號開始為「機制相關錯誤」未來保留 41-49 給 M2、機制不支援等
- **Alternatives considered**：
  - **重用 PreferencesNotSupported**：語意相反（一個是「不接受」、一個是「需要」），混用會混淆
  - **使用 ValueError 等通用錯誤**：違反原則 V「可觀測性」

---

## R-004 audit schema v1.2 → v1.3 演進

- **Decision**：升 schema_version 至 `"1.3"`；新增兩個欄位：
  - 頂層 `processing_order: list[str] | null`（M1 時為 role id 陣列；M0 時為 null）
  - `allocation_trace[].preference_rank: int | null`（M1 時為 1-based 排名或 null；M0 時為 null）
  其餘欄位不變。沿用「新增可選欄位 + null」教訓 3。
- **Rationale**：
  - 與既有 schema 演進策略一致
  - 既有測試對「已知欄位」斷言不會 break；只有「斷言 schema_version == '1.2'」的測試需要更新
- **Alternatives considered**：
  - **加 nested `mechanism_specific` 子物件**：增加層級無收益
  - **直接升 v2.0**：過度重型；本變更為附加而非破壞

---

## R-005 mechanism dispatch 位置

- **Decision**：在 `pipeline.run_match()` 內 dispatch；不引入 strategy class / dispatcher 物件。
  ```python
  if inp.mechanism == "M0":
      if any non-empty preferences in roster: raise PreferencesNotSupported
      assignment, alloc_trace = allocate_m0(...)
      processing_order = None
  elif inp.mechanism == "M1":
      if all preferences in roster are empty: raise M1RequiresPreferences
      processing_order, assignment, alloc_trace = allocate_m1(...)
  else:
      raise ValueError("不支援的 mechanism")
  ```
- **Rationale**：
  - 簡單明白；2 個機制不需 strategy pattern（門檻是 ≥ 3 個機制）
  - dispatch 邏輯集中於一處，未來加 M2 時也只動這裡
- **Alternatives considered**：
  - **Strategy class 或 dict-based dispatcher**：YAGNI；2 個分支不值得抽象化

---

## R-006 既有黃金檔重生策略

- **Decision**：所有既有 5 個黃金檔一次性重生（M0 路徑）：
  - `teacher-class-baseline.audit.json`
  - `teacher-class-template.audit.json`
  - `teacher-class-csv.audit.json`
  - `study-group-template.audit.json`
  - `study-group-xlsx.audit.json`

  重生後 diff 應僅顯示：
  - `schema_version: "1.2" → "1.3"`
  - 新增 `processing_order: null`（在 seed 後）
  - 每筆 `allocation_trace` 條目新增 `preference_rank: null`

  邏輯欄位（assignment / qualified_set / filter_trace / template_snapshot / import_metadata）逐位元組不變。
  新增第 6 個黃金檔 `study-group-m1.audit.json`（M1 路徑）。
- **Rationale**：
  - 與階段 2a、2b 重生策略一致；commit diff 在 PR 中可被人工審視
  - SC-006 將以「diff 範圍」自動化驗證——測試會比對 diff 行數
- **Alternatives considered**：
  - **保留舊 schema 不重生**：違反 schema 嚴格性
  - **條件化輸出 processing_order**：違反 R-004「新增可選欄位」的純粹性

---

## R-007 M1 allocation_trace 條目結構

- **Decision**：M1 路徑每位處理的角色產生一筆 trace 條目：
  ```json
  {
    "step": 1,
    "role_id": "S03",
    "candidates": ["G1", "G2", "G3"],
    "candidate_with_capacity": ["G1", "G2", "G3"],
    "preferred_order": ["G2", "G1", "G3"],
    "chosen": "G2",
    "preference_rank": 1,
    "remaining_capacity_after": {"G1": 3, "G2": 2, "G3": 3}
  }
  ```
  其中 `preferred_order` 是該 role 在 preferences 中**仍在資格集合內**的部分（去除無效 target id）；
  `chosen` 是最終分配；`preference_rank` 是 1-based 排名（從 preference_order 算起）。
  若 fallback 抽籤（preferences 全滿）→ `preference_rank: null` + 增加 `fallback_random_index: <int>` 欄位記錄抽中的索引。
- **Rationale**：
  - audit 必須**完整可重播**——光看 trace 就能驗證每步決策
  - `preferred_order` 與 `chosen` 並列，方便讀者快速看出「第幾志願」
- **Alternatives considered**：
  - **只記 chosen**：無法獨立驗算
  - **記 preferences 原樣**：但 preferences 可能含資格外 / 重複 id，標準化後較清晰

---

## R-008 preferences 規範化

- **Decision**：在 M1 處理時對每位 role 的 preferences 做以下規範化：
  1. **去重**（保留第一次出現）
  2. **忽略不在 qualified_set[role] 內的 target id**（靜默忽略，不拋錯）
  規範化後的 list 即 `preferred_order`，寫入 audit。
- **Rationale**：
  - FR-008、FR-009：「不在資格集合內 → 靜默忽略；重複 → 取第一個」
  - 規範化後的版本進 audit 而非原始 preferences——可重播性更好
- **Alternatives considered**：
  - **保留原樣**：audit 中 preferred_order 含無效項，閱讀混亂
  - **對重複 / 無效 id 拋錯**：過度嚴格，使用者體驗差

---

## R-009 CLI `--mechanism` 參數

- **Decision**：CLI `matcher run --mechanism <value>`：
  - 預設值 `M0`（向後相容）
  - 接受值 `M0` 或 `M1`（不分大小寫，內部規範化為大寫）
  - 不支援值 → 明確錯誤訊息「不支援的機制 `<value>`；支援的機制：M0、M1」+ exit code 2（沿用 Typer 風格）
- **Rationale**：
  - 沿用既有 CLI 參數風格
  - 預設值維持 M0 確保所有不指定的呼叫繼續走 M0
- **Alternatives considered**：
  - **--m1 / --m0 互斥旗標**：難擴充（未來加 M2 時要再加旗標）
  - **不設預設值要求顯式**：破壞向後相容

---

## R-010 測試先紅後綠的具體做法

- **Decision**：
  - 先寫 `tests/unit/test_allocator_m1.py`（純函式測試 M1 演算法）
  - 再寫 `tests/integration/test_cli_mechanism_m1.py`（CLI 端對端）
  - 黃金檔比對：先實作完 M1 → 跑一次以產出 `study-group-m1.audit.json` → 改成自動化測試的「assert response == golden」
  - 既有 M0 測試（黃金檔比對）：將在 M1 實作完 + audit schema 升 v1.3 後**一次性重生**所有 5 個黃金檔；diff 須在 PR 中清楚審視
- **Rationale**：
  - 與既有教訓 1 一致
  - 「先紅後綠」最嚴格的形式：unit test 紅 → 實作 → unit 綠 → integration 紅 → 改 CLI → integration 綠

---

## 已解決的 NEEDS CLARIFICATION 列表

本 plan 中無 NEEDS CLARIFICATION 標記。spec.md Assumptions 標為「由 plan 決定」的項目皆於 R-001 ~ R-010 解決。

# Research: M2 Boston 分配機制技術選型

**Branch**: `007-m2-boston-mechanism` | **Date**: 2026-05-24

---

## R-001 M2 Boston 演算法標準形式

- **Decision**：
  ```text
  remaining = capacities.copy()
  unassigned_roles = roster.roles (依 role_id 字母序)
  assigned: dict[role_id, target_id] = {}
  trace: list = []
  step = 0

  max_level = max(len(preferred_order[role]) for role in roles)
  for level in 1..max_level:
      # 收集本層各 target 的競爭者
      groups: dict[target_id, list[role_id]] = {}
      for role_id in unassigned_roles 中且 level <= len(preferred_order[role_id]):
          target = preferred_order[role_id][level-1]
          if remaining[target] > 0:
              groups.setdefault(target, []).append(role_id)

      # 依 target_id 字母序處理同層各 target
      for target_id in sorted(groups.keys()):
          competitors = groups[target_id]
          cap = remaining[target_id]
          if len(competitors) <= cap:
              winners = competitors          # 全進
              tie_break_indices = [None] * len(competitors)
          else:
              # 超額：Fisher-Yates 洗牌取前 N 名
              shuffled, indices = fisher_yates_shuffle(competitors, rng)
              winners = shuffled[:cap]
              # 每位競爭者的 tie_break_random_index = 在 shuffled 中的位置
              role_to_position = {r: i for i, r in enumerate(shuffled)}
              tie_break_indices = [role_to_position[r] for r in competitors]
              # 落選者留在 unassigned，繼續下一層
          for role in winners:
              step += 1
              remaining[target_id] -= 1
              assigned[role] = target_id
              trace.append({
                  "step": step,
                  "role_id": role,
                  ...
                  "preference_rank": level,
                  "tie_break_random_index": <對應索引或 None>,
              })

  # Fallback：所有層級處理完仍未分配
  for role_id in unassigned_roles 中且 role_id not in assigned (依 role_id 字母序):
      candidates = [t for t in qualified_set[role_id] if remaining[t] > 0]
      if candidates:
          idx = rng.randrange(len(candidates))
          chosen = candidates[idx]
          remaining[chosen] -= 1
          assigned[role_id] = chosen
          trace.append({..., "fallback_random_index": idx, "preference_rank": None})
      else:
          assigned[role_id] = None
          # 也加入 trace？或不記？決定見 R-005

  processing_order = [trace_entry.role_id for trace_entry in trace]
  return processing_order, assigned, trace
  ```
- **Rationale**：
  - 標準 Boston Mechanism / Immediate Acceptance；簡單、可解釋
  - 同層 target 依字母序處理 → 確保 seed 消耗順序固定
- **Alternatives considered**：
  - **Deferred Acceptance (Gale-Shapley)**：穩定匹配但需要雙邊偏好；vision 排除
  - **TTC (Top Trading Cycles)**：需要「初始稟賦」假設，學校場景無此假設

---

## R-002 同層 target 處理順序：字母序

- **Decision**：每層內依 target_id 字母序處理各 target 的競爭者。
- **Rationale**：seed 消耗順序必須固定；字母序是最自然、無歧義的選擇。
- **Alternatives considered**：
  - **依 target 容量遞減**：可能導致小容量 target 後處理被搶光；行為較難解釋
  - **隨機順序**：消耗 seed 但無收益

---

## R-003 同層超額時 Fisher-Yates 的「索引」語意

- **Decision**：`tie_break_random_index` = 該角色在 Fisher-Yates 洗牌**結果**中的位置（0-based）。
  - 例：3 位競爭者洗牌後為 `[C, A, B]`，容量 2 → 取 [C, A]；
    - C 的 `tie_break_random_index` = 0 → 中
    - A 的 `tie_break_random_index` = 1 → 中
    - B 的 `tie_break_random_index` = 2 → 落選
  - 落選者**不**寫入此 step 的 trace；但在下一層或 fallback 處理時才寫入 trace
- **Rationale**：
  - 「在洗牌結果中的位置」是 deterministic + 直接對應「誰中、誰落選」
  - 中選者的 index < 容量；落選者的 index ≥ 容量（不在當層 trace 中，但概念上記錄）
- **Alternatives considered**：
  - **Fisher-Yates 過程中的逐步抽取 index**：更逼近實作但較難閱讀
  - **null + flag「super-quota」**：失去具體 index 不利稽核

---

## R-004 fallback 與 M1 對齊

- **Decision**：M2 所有層級處理完仍未分配的角色 → 從「合格 ∩ 仍有名額」中以同一 SeededRandom 抽一；與 M1 邏輯一致。
- **Rationale**：
  - 統一 fallback 行為，降低使用者心智負擔（M1 / M2 在 edge case 處理一致）
  - 同一 SeededRandom 保證跨層級 + fallback 的 seed 消耗順序固定
- **Alternatives considered**：
  - **M2 嚴格依層級、無 fallback**：學術上更純但實務上會留下「沒分配」的尷尬

---

## R-005 未被分配的角色是否進 trace

- **Decision**：未被分配的角色（fallback 也找不到 target）**也進 trace**，`chosen: null`、`preference_rank: null`、`fallback_random_index: null`、`tie_break_random_index: null`；`candidates: []`。這樣 trace 行數 = roles 數，與 M1 對稱。
- **Rationale**：
  - audit 完整性：每位角色都應有 trace 條目，方便個別查詢視圖（feature 005）渲染
  - 與 M1 對稱：M1 trace 也是 per-role
- **Alternatives considered**：
  - **省略未分配的 trace**：個別查詢頁需特殊處理「沒有 trace」的情境，反而複雜

---

## R-006 錯誤類別重新命名策略

- **Decision**：
  ```python
  # errors.py
  class MechanismRequiresPreferences(MatcherError):
      exit_code = 40

  # alias 維持向後相容
  M1RequiresPreferences = MechanismRequiresPreferences
  ```
  訊息模板由 caller 提供（pipeline.py 拋出時依 mechanism 動態填）：
  - M1：「M1 需要至少一位角色提供志願；若無志願請改用 mechanism=M0」
  - M2：「M2 需要至少一位角色提供志願；若無志願請改用 mechanism=M0」
- **Rationale**：
  - alias 完全不破壞既有 import / isinstance / raise 行為
  - 既有測試斷言 `M1RequiresPreferences` 仍可運作（同類別）
  - 訊息依 mechanism 變化即可，無需子類化
- **Alternatives considered**：
  - **新增 M2RequiresPreferences（兩個獨立類別）**：訊息與 exit code 都一樣，分兩類無意義
  - **完全棄用舊名強制更新**：破壞既有測試/import；違反「簡潔優先」精神（換名字無實質收益）

---

## R-007 既有黃金檔重生策略

- **Decision**：所有 6 個既有黃金檔一次性重生（含階段 4a 新增的 study-group-m1.audit.json）：
  - `teacher-class-baseline.audit.json`、`teacher-class-template.audit.json`、`teacher-class-csv.audit.json`、`study-group-template.audit.json`、`study-group-xlsx.audit.json`、`study-group-m1.audit.json`
  - 重生後 diff 應**僅**顯示：每筆 `allocation_trace` 條目新增 `"tie_break_random_index": null`
  - 邏輯欄位（assignment / qualified_set / filter_trace / processing_order / preference_rank / preferred_order / fallback_random_index）逐位元組不變
  - 新增第 7 個黃金檔 `study-group-m2.audit.json`（M2 路徑）
- **Rationale**：
  - 沿用階段 2a/2b/3a/4a 的批次重生模式
  - diff 範圍最小化、容易在 PR 中審視
- **Alternatives considered**：
  - **保留舊 schema 路徑、不重生**：違反 schema 嚴格性

---

## R-008 audit schema 不升版本

- **Decision**：保持 v1.3；新增的 `tie_break_random_index` 為 `allocation_trace` 條目的可選欄位（皆 null 在 M0/M1/M2 非超額情境）。
- **Rationale**：
  - 教訓 3「新增可選欄位 + null」的最節制版本——同一 schema 加新欄位，無需升版號
  - 既有測試對 schema_version 的斷言（`== "1.3"`）不必動
- **Alternatives considered**：
  - **升 v1.4**：對 audit schema 而言只多一欄位 + null，升版號是過度

---

## R-009 CLI `--mechanism` 擴充

- **Decision**：規範化大寫後檢查值 ∈ `{"M0", "M1", "M2"}`；其他值 → exit 2 + 訊息「不支援的機制 `<value>`；支援：M0、M1、M2」。
- **Rationale**：沿用既有風格；訊息列出當前支援機制清單。
- **Alternatives considered**：（同 4a；無新替代）

---

## R-010 SeededRandom 順序保證的回歸測試

- **Decision**：本 feature 內新增測試「以同一 roster + 同一 seed 跑 M2 兩次 → trace 完全相同」；
  另外驗證「M2 trace 中所有 tie_break_random_index 的非 null 值與 fallback_random_index 的順序，可以對應到一個確定的 SeededRandom 序列」。
- **Rationale**：教訓 1「黃金檔比對」與教訓 8（未寫入 experience 但已提及）的延伸——
  讓 audit 中的隨機 index 與 SeededRandom 消耗順序對齊，使「驗算」是可能的。
- **Alternatives considered**：（無）

---

## 已解決的 NEEDS CLARIFICATION 列表

本 plan 中無 NEEDS CLARIFICATION 標記。

# Data Model: M2 Boston 分配機制

**Branch**: `007-m2-boston-mechanism` | **Date**: 2026-05-24

---

## 新增（或修改）實體

### `allocate_m2`（新函式）

```text
def allocate_m2(
    qualified_set: dict[str, list[str]],
    preferences_map: dict[str, list[str]],
    capacities: dict[str, int],
    rng: SeededRandom,
    role_order: list[str],
) -> tuple[list[str], dict[str, Optional[str]], list[dict]]:
    """
    回傳：(processing_order, assignment, allocation_trace)
    - processing_order: trace 中 role 出現的順序
    - assignment: role_id → target_id 或 None
    - allocation_trace: 每位 role 一筆條目
    """
```

實作步驟見 research.md R-001。

### `MechanismRequiresPreferences`（重新命名既有實體）

```text
class MechanismRequiresPreferences(MatcherError):
    exit_code = 40

# 向後相容 alias
M1RequiresPreferences = MechanismRequiresPreferences
```

訊息模板由 caller 依 mechanism 動態填寫；既有所有 `isinstance(..., M1RequiresPreferences)` 與 `raise M1RequiresPreferences(...)` 仍正常運作。

### `MatcherInput`（既有實體擴充）

```text
mechanism: Literal["M0", "M1", "M2"]   # 從 Literal["M0", "M1"] 擴展
```

### `AuditRecord`（schema 保持 v1.3）

`allocation_trace[]` 條目新增**可選欄位**：

| Field | Type | Notes |
|---|---|---|
| `tie_break_random_index` | `int \| null` | M2 + 同層超額 → 角色在 Fisher-Yates 洗牌結果中的位置；其他情境（M0、M1、M2 非超額）皆 null |

既有欄位（`step`、`role_id`、`candidates`、`random_index`、`chosen`、`remaining_capacity_after`、`preferred_order`、`preference_rank`、`fallback_random_index`）皆保留語意：

- **M2 路徑下**：
  - `step`：trace 中的序號（依分配發生時序）
  - `random_index`：在 processing_order 中的位置（與 M1 同義）
  - `preferred_order`：規範化後的 preferences（與 M1 同義）
  - `preference_rank`：被分配對象在 preferred_order 中的 1-based 排名（即層級）；fallback 抽中為 null
  - `fallback_random_index`：fallback 抽籤時的索引；其他為 null
  - `tie_break_random_index`：**新**——同層超額時為非 null

`schema_version` 保持 `"1.3"`。

---

## 驗證規則

| Check | 對應 FR | 觸發錯誤 |
|---|---|---|
| `mechanism="M0"` + 任一 role.preferences 非空 | （沿用） | `PreferencesNotSupported` |
| `mechanism in ("M1", "M2")` + 所有 role.preferences 皆空 | FR-003 | `MechanismRequiresPreferences` |
| `mechanism` 不在 `{M0, M1, M2}` | FR-008 | `ValueError`（CLI → exit 2） |
| 其他驗證 | 沿用既有 | 沿用既有 |

---

## 狀態轉移

```text
MatcherInput(mechanism=M2, preferences非空)
  → [validate]
  → [filter] → qualified_set
  → [allocate_m2] → (processing_order, assignment, trace)
      1. 依層級 L=1, 2, ...：
         - 收集本層各 target 的競爭者
         - 同 target 競爭者 ≤ cap → 全進；> cap → fisher_yates_shuffle 取前 N
         - 依 target_id 字母序處理同層 targets
      2. fallback：未分配的角色從合格 ∩ 仍有名額者抽一
      3. 完全沒對象的角色 → chosen=null，仍加入 trace
  → [audit + processing_order + tie_break_random_index] → AuditRecord (v1.3)
```

---

## 既有黃金檔重生範圍

6 個既有 + 1 個新增 = 7 個黃金檔總計：

| 檔案 | 路徑 | 變更 |
|---|---|---|
| `teacher-class-baseline.audit.json` | M0 | 每筆 trace 新增 `tie_break_random_index: null` |
| `teacher-class-template.audit.json` | M0 + template | 同上 |
| `teacher-class-csv.audit.json` | M0 + CSV | 同上 |
| `study-group-template.audit.json` | M0 + YAML | 同上 |
| `study-group-xlsx.audit.json` | M0 + xlsx | 同上 |
| `study-group-m1.audit.json` | M1 | 同上 |
| `study-group-m2.audit.json` | **新** M2 | 完整 M2 路徑 audit |

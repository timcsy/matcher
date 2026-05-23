# Data Model: M1 RSD 分配機制

**Branch**: `006-m1-rsd-mechanism` | **Date**: 2026-05-23

---

## 新增（或修改）實體

### `allocate_m1`（新函式）

```text
def allocate_m1(
    qualified_set: dict[str, list[str]],
    preferences_map: dict[str, list[str]],          # role_id → preferences (list[target_id])
    capacities: dict[str, int],
    rng: SeededRandom,
) -> tuple[list[str], dict[str, Optional[str]], list[dict]]:
    """
    回傳：(processing_order, assignment, allocation_trace)
    - processing_order: 洗牌後的 role_id 序列
    - assignment: role_id → target_id（未分配為 None）
    - allocation_trace: 每位 role 的決策紀錄
    """
```

實作步驟見 research.md R-001。

### `M1RequiresPreferences`（新錯誤類別）

```text
class M1RequiresPreferences(MatcherError):
    exit_code = 40
```

訊息固定包含「M1 需要至少一位角色提供志願；若無志願請改用 mechanism=M0」。

### `MatcherInput`（既有實體擴充）

```text
mechanism: Literal["M0", "M1"]   # 從 Literal["M0"] 擴展
```

### `AuditRecord`（schema 升級 v1.2 → v1.3）

新增頂層欄位：

| Field | Type | Notes |
|---|---|---|
| `processing_order` | `list[str] \| null` | M1 時為 role_id 陣列；M0 時為 null |

新增 `allocation_trace[]` 條目欄位：

| Field | Type | Notes |
|---|---|---|
| `preferred_order` | `list[str] \| null` | M1 路徑：規範化後的 preferences；M0 為 null |
| `preference_rank` | `int \| null` | M1 路徑：被分配對象的 1-based 排名；fallback 抽中或 M0 為 null |
| `fallback_random_index` | `int \| null` | M1 路徑 fallback 抽籤時為抽中索引；其他為 null |

既有欄位（`step`、`role_id`、`candidates`、`random_index`、`chosen`、`remaining_capacity_after`）皆**保留語意**但在 M1 路徑下意義略不同：
- `random_index`：M0 為「在 candidates 中抽中索引」；M1 為「Fisher-Yates 洗牌中該 role 的位置」（即 processing_order 中的索引）
- `candidates`：M0 為「該 role 的合格 ∩ 仍有名額」；M1 同樣意義（仍為合格 ∩ 仍有名額的列表）

`schema_version`：`"1.2"` → `"1.3"`

---

## 驗證規則（解析期執行）

| Check | 對應 FR | 觸發錯誤 |
|---|---|---|
| `mechanism="M0"` + 任一 role.preferences 非空 | FR-005 | `PreferencesNotSupported`（沿用階段 1） |
| `mechanism="M1"` + 所有 role.preferences 皆空 | FR-003 | `M1RequiresPreferences`（新） |
| `mechanism` 既非 M0 也非 M1 | FR-008 | `ValueError`（CLI 層 → exit 2） |
| 其他驗證（規則、屬性、容量等） | 沿用既有 | 沿用既有 |

---

## 狀態轉移

```text
MatcherInput(mechanism=M1, preferences非空)
  → [validate] (含 R-005 dispatch 邏輯)
  → [filter] → qualified_set
  → [allocate_m1] →
      1. processing_order = fisher_yates_shuffle(roles, rng).indices
      2. for role in processing_order:
            candidates_with_capacity = [t for t in qualified_set[role] if capacity[t] > 0]
            preferred_order = normalize(role.preferences, qualified_set[role])
            first_pref_with_capacity = first(preferred_order ∩ candidates_with_capacity)
            if first_pref_with_capacity:
                chosen = first_pref_with_capacity
                preference_rank = preferred_order.index(chosen) + 1
            elif candidates_with_capacity:
                chosen = rng.choice(candidates_with_capacity)
                preference_rank = None
                fallback_random_index = ...
            else:
                chosen = None
            capacity[chosen] -= 1 (if chosen)
            trace.append({...})
  → [audit + processing_order + preference_rank] → AuditRecord (schema 1.3)
```

---

## 規範化規則（preferences）

從 role.preferences 製作 preferred_order：

```text
def normalize_preferences(role_prefs: tuple[str], qualified_for_role: list[str]) -> list[str]:
    seen: set = set()
    out: list = []
    for tid in role_prefs:
        if tid in seen:
            continue          # 去重
        seen.add(tid)
        if tid not in qualified_for_role:
            continue          # 忽略資格外
        out.append(tid)
    return out
```

---

## 既有黃金檔重生範圍

5 個既有 + 1 個新增 = 6 個黃金檔總計：

| 檔案 | 路徑 | 變更 |
|---|---|---|
| `teacher-class-baseline.audit.json` | M0、無 template | schema 1.2→1.3 + processing_order: null + 每筆 trace 新增 3 個 null 欄位 |
| `teacher-class-template.audit.json` | M0、含 template | 同上 |
| `teacher-class-csv.audit.json` | M0、CSV 匯入 | 同上 |
| `study-group-template.audit.json` | M0、YAML | 同上 |
| `study-group-xlsx.audit.json` | M0、xlsx | 同上 |
| `study-group-m1.audit.json` | **新** M1 路徑 | 含 processing_order 與 preference_rank |

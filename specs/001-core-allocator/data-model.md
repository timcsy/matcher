# Data Model: 核心媒合引擎

**Branch**: `001-core-allocator` | **Date**: 2026-05-22

本文件定義階段 1 所有實體與型別的結構。所有名稱皆為英文識別字（依 constitution）；說明文字為繁中。

---

## 實體一覽

```text
Role          角色（待媒合的個體，例如老師）
Target        對象（被分配的容器，例如班級；具容量）
Attribute     屬性（鍵值對；型別為 str / int / list[str]）
RuleExpr      規則表達式 AST（Eq / In / Ge / Le / And / Or / Not）
Rule          一條規則（含表達式與自然語言說明）
Ruleset       規則集（多條規則的集合）
Roster        名單（roles + targets）
QualifiedSet  資格集合（合法的角色-對象 候選配對）
Assignment    最終配對（role_id → target_id）
AuditRecord   稽核紀錄（完整可重播紀錄）
MatcherInput  完整輸入（rules + roster + seed + preferences?）
MatcherResult 完整輸出（qualified_set + assignment + audit）
```

---

## 詳細欄位

### Role

| Field | Type | Notes |
|---|---|---|
| `id` | `str` | 唯一識別碼；同一 roster 內不可重複 |
| `attributes` | `dict[str, AttrValue]` | 角色屬性（如 `{"speciality": "國文", "seniority": 7}`） |

### Target

| Field | Type | Notes |
|---|---|---|
| `id` | `str` | 唯一識別碼；同一 roster 內不可重複 |
| `attributes` | `dict[str, AttrValue]` | 對象屬性（如 `{"required_subjects": ["國文", "數學"]}`） |
| `capacity` | `int` | 容量上限；`capacity ≥ 1` |

### AttrValue

`AttrValue = str | int | list[str]`

不支援巢狀 dict、float、bool；理由：避免規則表達式評估時的型別歧義。

### RuleExpr（AST 節點）

```text
Eq(field: str, value: AttrValue)              欄位等值
In(field: str, set: list[AttrValue])           欄位值落在集合中
RoleInTargetField(role_field, target_field)    role.{role_field} ∈ target.{target_field}（基本跨側匹配）
Ge(field: str, value: int)                     ≥
Le(field: str, value: int)                     ≤
And(children: list[RuleExpr])
Or(children: list[RuleExpr])
Not(child: RuleExpr)
```

`field` 採前綴標示 side：`role.speciality`、`target.required_subjects`。

### Rule

| Field | Type | Notes |
|---|---|---|
| `id` | `str` | 規則識別碼 |
| `description` | `str` | 繁中自然語言說明（FR-002 強制） |
| `expr` | `RuleExpr` | 表達式 AST |

### Ruleset

| Field | Type | Notes |
|---|---|---|
| `rules` | `list[Rule]` | 所有規則；解讀為 AND（必須全部通過才算有資格） |
| `version` | `str` | 規則檔版本字串（自由填寫，會寫入稽核快照） |

### Roster

| Field | Type | Notes |
|---|---|---|
| `roles` | `list[Role]` |  |
| `targets` | `list[Target]` |  |

### QualifiedSet

```text
QualifiedSet = dict[role_id: str, list[target_id: str]]
```

每個角色對應到「該角色有資格被分配到的對象 id 清單」。`list` 內保持來源順序（不可比較隨機性）。

### Assignment

```text
Assignment = dict[role_id: str, target_id: str | None]
```

`None` 代表該角色未被分配（容量耗盡的合法情境，但本階段透過容量檢查通常已拒絕此情境，留作邊界保險）。

### AuditRecord

```text
{
  "schema_version": "1.0",
  "mechanism": "M0",
  "seed": <int>,
  "rules_snapshot": <Ruleset 完整內容>,
  "roster_snapshot": <Roster 完整內容>,
  "qualified_set": <QualifiedSet>,
  "filter_trace": [
    {
      "role_id": "...",
      "target_id": "...",
      "qualified": true,
      "matched_rules": ["R001", "R003"]
    }
    # 對每個 role × target 組合一筆，含過濾結果與通過的規則 id
  ],
  "allocation_trace": [
    {
      "step": 1,
      "role_id": "...",
      "candidates": ["T01", "T03"],
      "random_index": 0,
      "chosen": "T01",
      "remaining_capacity_after": {"T01": 1, "T03": 2}
    }
    # 每一步隨機決策的完整紀錄
  ],
  "assignment": <Assignment>,
  "generated_at": null
}
```

`generated_at` 永遠為 `null`，避免時間戳破壞跨機器重現性；外部紀錄（如 git commit、PR）足以追溯時間。

### MatcherInput

| Field | Type | Notes |
|---|---|---|
| `ruleset` | `Ruleset` |  |
| `roster` | `Roster` |  |
| `seed` | `int` | 必須提供（FR-003） |
| `preferences` | `Preferences \| None` | 本階段：若非 None / 非空 → 拒絕 |
| `mechanism` | `Literal["M0"]` | 本階段固定 M0 |

### Preferences（介面預留，本階段不使用）

```text
Preferences = dict[role_id: str, list[target_id: str]]
```

階段 4 將使用；本階段如收到非空 preferences → 引發 `PreferencesNotSupported`。

### MatcherResult

| Field | Type | Notes |
|---|---|---|
| `qualified_set` | `QualifiedSet` |  |
| `assignment` | `Assignment` |  |
| `audit` | `AuditRecord` |  |

---

## 驗證規則（在輸入解析期執行）

| Check | 對應 FR | 觸發錯誤 |
|---|---|---|
| `roles` 非空 | FR-011 | `EmptyRoster` |
| `role.id` 與 `target.id` 各自唯一 | FR-011 | `DuplicateIdentity` |
| 規則表達式中所有 `field` 引用皆存在於對應側屬性 | FR-011 | `UnknownAttribute` |
| `seed` 為整數且明確提供 | FR-003 | `SeedMissing` |
| `preferences` 為 None 或空 dict | FR-010 | `PreferencesNotSupported` |
| 規則無內部矛盾（同一條 `And` 中含 `Eq(f, v)` 與 `Not(Eq(f, v))` 之類） | FR-011 | `RuleContradiction` |

---

## 狀態轉移

本階段為純函式管線，無狀態轉移：

```text
MatcherInput
  → [validate]
  → [filter] → QualifiedSet
  → [check capacity & feasibility]
  → [allocate M0] → Assignment
  → [assemble audit] → AuditRecord
  → MatcherResult
```

任一階段失敗即丟出對應 Exception；錯誤後不繼續流程（FR-011）。

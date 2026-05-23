# CLI Contract: matcher run --mechanism

**Branch**: `006-m1-rsd-mechanism` | **Date**: 2026-05-23

---

## 修改：`matcher run`

```text
matcher run \
  ( --template <id> | --template-file <path> | --rules <path> ) \
  ( --roster <yaml> | --roster-csv <path> | --roster-xlsx <path> [--sheet <name>] ) \
  --seed <int>
  [--mechanism <M0|M1>]                 # ← 本 feature 改：從固定 M0 擴為 M0/M1
  [--preferences <path>]
  [--output <audit.json>]
```

### 變更

- `--mechanism` 從「文件存在但僅接受 M0」改為「接受 M0 或 M1」
- 不指定 → 預設 M0（向後相容）
- 不分大小寫；內部規範化為大寫
- 不支援值 → exit 2 + 訊息「不支援的機制 `<value>`；支援的機制：M0、M1」

### Dispatch 規則

| `mechanism` | roster 中至少一位 preferences 非空 | 行為 |
|---|---|---|
| `M0` | 否 | 走 M0 純抽籤（沿用階段 1） |
| `M0` | 是 | `PreferencesNotSupported`（沿用階段 1，exit 17） |
| `M1` | 否 | `M1RequiresPreferences`（**新**，exit 40） |
| `M1` | 是 | 走 M1 RSD |

### 訊息範例

```text
# Exit 40（M1 + 全空 prefs）
錯誤：M1 需要至少一位角色提供志願；若無志願請改用 mechanism=M0。
細節：roster 中所有 5 位角色的 preferences 皆為空陣列。
建議：請至少為一位角色填入志願（CSV 「志願組別」欄填分號分隔字串），或改用 `--mechanism M0`。
```

```text
# Exit 2（不支援的機制值）
錯誤：不支援的機制 `M5`。
細節：目前支援：M0、M1。
建議：請以 --mechanism M0 或 --mechanism M1 重試。
```

---

## stdout 輸出格式

M1 路徑下，stdout 摘要新增「處理順序」與「每位的選擇」段：

```text
=== 分配階段（M1 RSD 隨機輪流挑）===
seed：2026
處理順序：S03 → S01 → S05 → S02 → S04 → ...
最終配對：
  S01（小明）→ G2（自然組） — 第 1 志願
  S02（小華）→ G1（程式組） — 第 2 志願
  S03（小美）→ G3（人文組） — 第 1 志願
  ...
```

M0 路徑下 stdout 維持階段 1 既有格式。

---

## 退出碼擴充

| Code | 意義 | 對應錯誤類別 | 來源 |
|---|---|---|---|
| 0–17 | 沿用 | （沿用） | 階段 1 |
| 20–23 | 沿用 | （沿用） | 階段 2a |
| 30–33 | 沿用 | （沿用） | 階段 2b |
| **40** | M1 需要至少一位角色提供志願 | `M1RequiresPreferences` | **本 feature 新增** |
| 2 | CLI 參數錯誤（含不支援的 mechanism） | Typer | 沿用 |

---

## 不變式（契約測試會驗證）

- **向後相容**：未指定 `--mechanism` 或指定 `M0` 時，audit 中 `processing_order: null`、`preference_rank: null`；assignment 邏輯不變
- **可重現性**：同 seed + 同 roster + mechanism=M1 → 兩次稽核紀錄逐位元組相同（含 processing_order、每人選擇）
- **拒絕邏輯**：M1 + 全空 prefs → exit 40；M0 + 任一非空 prefs → exit 17（既有）
- **規範化**：preferences 中**不在資格集合內**的 target id 在 audit `preferred_order` 中**不出現**；**重複** id 只保留第一個
- **CLI 與 Web 分離**：本 feature 對 Web 端點無影響；Web 仍只跑 M0

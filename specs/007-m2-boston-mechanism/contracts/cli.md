# CLI Contract: matcher run --mechanism M2

**Branch**: `007-m2-boston-mechanism` | **Date**: 2026-05-24

---

## 修改：`matcher run`

```text
matcher run \
  ( --template <id> | --template-file <path> | --rules <path> ) \
  ( --roster <yaml> | --roster-csv <path> | --roster-xlsx <path> [--sheet <name>] ) \
  --seed <int>
  [--mechanism <M0|M1|M2>]              # ← 本 feature 擴：從 M0|M1 擴為 M0|M1|M2
  [--preferences <path>]
  [--output <audit.json>]
```

### Dispatch 規則

| `mechanism` | roster 至少一位 preferences 非空 | 行為 |
|---|---|---|
| `M0` | 否 | 走 M0 純抽籤 |
| `M0` | 是 | `PreferencesNotSupported`（沿用，exit 17） |
| `M1` | 否 | `MechanismRequiresPreferences`（exit 40） |
| `M1` | 是 | 走 M1 RSD |
| `M2` | 否 | `MechanismRequiresPreferences`（exit 40） |
| `M2` | 是 | 走 M2 Boston |

### 訊息範例

```text
# Exit 40（M2 + 全空 prefs）
錯誤：M2 需要至少一位角色提供志願；若無志願請改用 mechanism=M0。
細節：roster 中所有角色的 preferences 皆為空。
建議：請至少為一位角色填入志願（CSV「志願組別」欄填分號分隔字串），或改用 `--mechanism M0`。
```

```text
# Exit 2（不支援的機制值）
錯誤：不支援的機制 `M3`。
細節：目前支援：M0、M1、M2。
建議：請以 --mechanism M0、M1 或 M2 重試。
```

---

## stdout 輸出格式

M2 路徑下，stdout 摘要顯示「M2 Boston 層級填滿」與處理順序：

```text
=== 分配階段（M2 Boston 層級填滿）===
seed：2026
處理順序：S01 → S03 → S02 → S05 → ...
最終配對：
  S01（小明）→ G2（自然組） — 第 1 志願
  S02（小華）→ G1（程式組） — 第 1 志願
  S03（小美）→ G3（人文組） — 第 1 志願
  ...
```

M0 / M1 路徑維持既有格式。

---

## 退出碼

| Code | 意義 | 對應錯誤類別 | 來源 |
|---|---|---|---|
| 0–17 | 沿用 | （沿用） | 階段 1 |
| 20–23 | 沿用 | （沿用） | 階段 2a |
| 30–33 | 沿用 | （沿用） | 階段 2b |
| 40 | 機制需要至少一位角色提供志願 | `MechanismRequiresPreferences`（=既有 `M1RequiresPreferences`，重新命名 + alias） | 4a → 本 feature 通用化 |

---

## 不變式（契約測試會驗證）

- **向後相容**：M0 / M1 路徑邏輯不變；既有 188 測試 100% 通過；既有 6 個黃金檔重生 diff 僅新增 `tie_break_random_index: null` 一行
- **可重現性**：同 seed + 同 roster + mechanism=M2 → 兩次稽核紀錄 bytewise 相同
- **拒絕邏輯**：M1 與 M2 + 全空 prefs → exit 40；訊息依 mechanism 動態填寫
- **錯誤 alias**：既有測試斷言 `M1RequiresPreferences` 透過 alias 仍可運作（`isinstance` / `raise` 都 OK）
- **超額抽籤**：`tie_break_random_index` 為 Fisher-Yates 洗牌結果的 0-based 索引；中選者 index < 容量、落選者下層繼續

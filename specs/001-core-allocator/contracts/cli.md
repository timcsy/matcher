# CLI Contract: `matcher`

**Branch**: `001-core-allocator` | **Date**: 2026-05-22

本檔定義階段 1 CLI 的命令介面、退出碼與輸出格式。所有錯誤訊息為繁中（FR-014）。

---

## 命令：`matcher run`

```text
matcher run \
  --rules <rules.yaml> \
  --roster <roster.yaml> \
  --seed <int> \
  [--preferences <preferences.yaml>] \
  [--mechanism M0] \
  [--output <audit.json>]
```

### 參數

| Flag | 必填 | Type | 預設 | 說明 |
|---|---|---|---|---|
| `--rules` | ✅ | path | — | 規則檔（YAML） |
| `--roster` | ✅ | path | — | 名單檔（YAML） |
| `--seed` | ✅ | int | — | 整數種子；未提供 → exit code 13 |
| `--preferences` | ❌ | path | None | 志願檔（YAML）；本階段提供非空即拒絕 |
| `--mechanism` | ❌ | str | `M0` | 機制名稱；本階段僅接受 `M0` |
| `--output` | ❌ | path | `audit.json` | 稽核紀錄輸出路徑 |

### 成功行為

1. 解析輸入並驗證（見 data-model.md 驗證規則）。
2. 執行過濾 → 輸出資格集合摘要到 stdout（繁中可讀）。
3. 執行 M0 純抽籤分配 → 輸出最終配對摘要到 stdout（繁中可讀）。
4. 將完整 `AuditRecord` 寫入 `--output` 指定路徑（JSON，UTF-8，`ensure_ascii=False`，`sort_keys=True`，`indent=2`）。
5. exit code 0。

### 退出碼

| Code | 意義 | 對應錯誤類別 |
|---|---|---|
| 0 | 成功 | — |
| 10 | 資格集合為空 | `QualifiedSetEmpty` |
| 11 | 容量不足以容納所有角色 | `CapacityShortage` |
| 12 | 規則內部矛盾 | `RuleContradiction` |
| 13 | seed 未提供 | `SeedMissing` |
| 14 | 名單為空 | `EmptyRoster` |
| 15 | 名單有重複身分 | `DuplicateIdentity` |
| 16 | 規則引用未定義屬性 | `UnknownAttribute` |
| 17 | preferences 非空但機制為 M0 | `PreferencesNotSupported` |
| 2 | CLI 參數錯誤（缺檔、檔案格式錯誤等） | Typer 處理 |
| 1 | 未預期錯誤 | — |

### 退出時的訊息範例

```text
# Code 17
錯誤：此機制（M0 純抽籤）不接受志願輸入。
原因：FR-010；志願序機制（M1 / M2）將於階段 4 加入。
建議：移除 --preferences 參數，或等待後續版本。
```

```text
# Code 11
錯誤：容量不足以容納所有角色。
細節：角色 12 人，所有對象總容量 10；超額 2 人。
建議：增加對象容量、減少角色，或調整資格條件以排除部分角色。
```

---

## 命令：`matcher filter`（可選，但實作必須提供）

只執行過濾階段（FR-005「外部呼叫者可只執行過濾」的 CLI 對應）。

```text
matcher filter --rules <rules.yaml> --roster <roster.yaml> [--output <qualified.json>]
```

輸出資格集合（JSON），不執行分配，不要求 seed。

### 退出碼

僅 0、10、12、14、15、16、2、1。

---

## stdout 輸出格式

`matcher run` 的 stdout 為**繁中可讀摘要**（非 JSON），結構固定供使用者瀏覽：

```text
=== 規則檔 ===
（規則 ID 與自然語言說明清單）

=== 過濾階段 ===
資格集合大小：N 個合法配對；M 位角色至少有一個可分配對象。

=== 分配階段（M0 純抽籤）===
seed：123456
最終配對：
  教師 T01（國文）→ 班級 C03（雙語）
  ...

=== 完成 ===
稽核紀錄已寫入：audit.json
```

機讀內容一律走 `--output` 的 JSON 檔。

---

## 不變式（契約測試會驗證）

- 同一組 `(--rules, --roster, --seed, --preferences)` 在任意 Python 3.11+ 平台執行兩次 → 兩個 `audit.json` 逐位元組相同（SC-001）。
- `audit.json` 中 `assignment` 的每個 `(role_id, target_id)` 對 → 該對必定出現在 `qualified_set[role_id]` 中（過濾／分配分離的形式保證）。
- 任何非 0 退出碼必然伴隨對應的繁中錯誤訊息與「建議」段（FR-011 的可操作性要求）。

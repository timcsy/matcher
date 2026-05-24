# Phase 1 — Data Model：Web UI 機制選擇 + 結果頁志願展示

本 feature **無新增持久化 schema、無新增 audit 欄位**。所有資料皆來自既有 audit JSON（schema v1.3）+ record JSON（schema 1.0）。本檔記錄「視圖模型（view model）」——即 routes 從 audit / record 萃取後注入模板的 context 形狀。

## 1. NewMatchFormViewModel（既有 + 新增 1 欄位）

`/match/new` GET 端點注入模板的 context：

| 欄位 | 型別 | 來源 | 新增 / 既有 |
|---|---|---|---|
| `templates` | list[dict] | template_loader.list_templates() | 既有 |
| `selected_template` | str \| None | query string | 既有 |
| `mechanisms` | list[tuple[str, str]] | 寫死 `[("M0", "M0 純抽籤"), ("M1", "M1 RSD（隨機輪流挑）"), ("M2", "M2 Boston（層級填滿）")]` | **新增** |
| `default_mechanism` | str | `"M0"` | **新增** |

**驗證**：mechanisms 在 routes/match.py 內為模組級常數，避免每次請求重新建構。

## 2. MatchRunFormInput（新增 1 欄位）

`POST /match/run` 接受的表單：

| 欄位 | 型別 | 預設 | 新增 / 既有 |
|---|---|---|---|
| `template_name` | str | (required) | 既有 |
| `roster_file` | UploadFile | (required) | 既有 |
| `seed` | int \| None | None | 既有 |
| `mechanism` | str | `"M0"` | **新增** |

**驗證流程**：
1. `mechanism = (mechanism or "M0").strip().upper()`
2. `if mechanism not in {"M0", "M1", "M2"}: raise HTTPException(400, "不支援的機制：{mechanism}（請選 M0、M1、M2）")`
3. 傳給 `MatcherInput(..., mechanism=mechanism)`（既有欄位）

## 3. MatchResultViewModel（既有 + 新增 3 欄位 + 1 欄位語意明確化）

`match_result.html` 渲染所需 context：

| 欄位 | 型別 | 來源 | 新增 / 既有 |
|---|---|---|---|
| `record` | dict | record JSON | 既有 |
| `audit` | dict | audit JSON (record.audit) | 既有 |
| `mechanism` | str | audit.mechanism | **新增**（顯式注入而非 audit 字典查找） |
| `mechanism_label` | str | humanize.mechanism_label(audit.mechanism) | **新增** |
| `processing_order_display` | list[tuple[str, str]] \| None | M0 → None；M1/M2 → [(role_id, display_name)] | **新增** |
| `allocation_rows` | list[dict] | 既有「分配表」資料 + 新增 `preference_rank_display` 欄 | 既有 + 1 欄 |

`preference_rank_display` 規則（每筆 trace entry 推導）：
- M0 路徑：欄整體隱藏（模板 if）
- M1/M2 + `preference_rank` 非 null：`"第 N 志願"`
- M1/M2 + `fallback_random_index` 非 null：`"抽籤"`

## 4. IndividualViewModel（既有 + 新增 3 欄位）

`individual_view.html` 渲染所需 context（routes/individual.py 萃取）：

| 欄位 | 型別 | 來源 | 新增 / 既有 |
|---|---|---|---|
| 既有所有欄位 | … | … | 既有 |
| `mechanism` | str | audit.mechanism | **新增** |
| `preference_rank` | int \| None | audit.allocation_trace[該 role].preference_rank | **新增** |
| `preferred_count` | int | len(audit.roster_snapshot.roles[role_id].preferred_order) 或回退 0 | **新增** |

> **註**：`preferred_count` 來自 roster snapshot 中該角色的志願序列長度（若無 preferred_order 欄則為 0）。**不**新增 audit 欄位——純粹由現有資料推導。

**三分支邏輯**（在模板 jinja2）：
```
preference_rank is not none       → "您被分到第 N 志願：…"
preference_rank is none + preferred_count > 0 → "您原本的志願已被分配給其他人，由公平抽籤分到 …"
preference_rank is none + preferred_count = 0 → "您未在志願清單中，由公平抽籤分到 …"
```

當 `mechanism == "M0"` 或角色未分配時，整段不渲染。

## 5. 既有 audit schema 引用（不修改）

本 feature 使用的既有欄位（v1.3 已穩定）：

```
audit.mechanism                                          str  ("M0" | "M1" | "M2")
audit.processing_order                                   list[str] | None
audit.allocation_trace[i].role_id                        str
audit.allocation_trace[i].assigned_to                    str | None
audit.allocation_trace[i].preference_rank                int | None
audit.allocation_trace[i].fallback_random_index          int | None
audit.allocation_trace[i].tie_break_random_index         int | None  (僅 M2)
audit.roster_snapshot.roles[role_id].name                str
audit.roster_snapshot.roles[role_id].preferred_order     list[str] | (missing) 視 4a/4b 實作而定
```

> **重要**：本 feature **MUST 不**升 audit schema（仍 v1.3），**MUST 不**新增 trace 欄位。所有顯示由現有資料推導。

## 6. State transitions

無——本 feature 純讀取既有 record / audit；無 record 生命週期變更。

## 7. Validation rules

- `mechanism` 表單值 ∈ {"M0", "M1", "M2"} 後規範化；非法值 → 400
- `preference_rank` 顯示時應為 1-based int ≥ 1（既有 trace 已保證；模板不再驗證）
- `preferred_count` 為 0 時顯示「未在志願清單中」分支（即使路徑為 M1/M2）

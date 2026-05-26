# Data Model — 對象名單試算表匯入

## 變更概覽

| 實體 | 變更 |
|---|---|
| `data_import.load_targets_csv/xlsx`（新）| spreadsheet → `tuple[Target,...]` |
| `data_import.load_roster_csv/xlsx` | 加可選參數 `targets=None`（給定則用、否則旁檔） |
| 範例試算表（動態產生）| 依範本 schema 即時組出 CSV/Excel bytes |

無 DB；audit schema 不變；Target/Roster dataclass 不變。

## 對象試算表格式（CSV / Excel）

```
| 編號（選填）| 容量 | <對象屬性1 顯示名> | <對象屬性2 顯示名> | ... |
| C01        | 2   | 三年甲班           | 國文;數學          | 雙語 |
```
- 表頭：可用「中文顯示名稱」或屬性英文 key（沿用 resolve_header 別名比對）
- 編號欄可省略 → 自動 `T001…`（避開檔內已有 id）
- 容量：必要欄，int，< 1 報錯；某列空白 → 略過該列
- list_str 欄：分號/頓號/逗號分隔（沿用 _MULTI_SEP 概念，coerce_value 處理）

## load_targets_csv / xlsx（新函式）

```python
load_targets_csv(path, template) -> tuple[Target, ...]
load_targets_xlsx(path, template, sheet=None) -> tuple[Target, ...]
```
- 驗證：重複 id → DuplicateIdentity；容量非法 → ValueError；缺容量欄 → RosterColumnMismatch
- 回傳結構與 `_load_targets`（YAML）一致 → 保證 SC-005 等價

## load_roster_csv / xlsx（簽名擴充）

```python
load_roster_csv(path, template, targets=None) -> (Roster, meta)
# targets is None → 沿用 _load_targets(旁檔)；給定 tuple → 直接用
```
- 向後相容：預設 None，CLI / 既有測試不受影響

## 範例試算表（動態）

```python
# src/matcher/web/example_gen.py
role_example_bytes(template, fmt: "csv"|"xlsx") -> bytes
target_example_bytes(template, fmt: "csv"|"xlsx") -> bytes
```
- 角色範例表頭：`編號` + 每個角色屬性的 description（或 key）
- 對象範例表頭：`編號` + `容量` + 每個對象屬性的 description
- 第二列：格式提示（int→（數字）、list_str→（多筆用分號隔開）、str→（文字））

## 端點

| 端點 | 說明 |
|---|---|
| `GET /templates/{id}/example/roles.csv` | 角色範例 CSV（登入 + 可見性） |
| `GET /templates/{id}/example/roles.xlsx` | 角色範例 Excel |
| `GET /templates/{id}/example/targets.csv` | 對象範例 CSV |
| `GET /templates/{id}/example/targets.xlsx` | 對象範例 Excel |
| `POST /match/run` | 第二檔 `targets_file`（CSV/Excel/YAML）依副檔名解析 |

## 不變
- Target / Roster dataclass、audit schema、CLI `.targets.yaml` 旁檔行為

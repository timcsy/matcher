# Data Model — 配對失敗可解釋

## 變更概覽

| 實體 | 變更 |
|---|---|
| `QualifiedSetEmpty` 例外 | 新增屬性 `trace`、`rule_stats`、`culprit`、`total_pairs` |
| 規則淘汰統計（新，純衍生）| `rejection_summary(trace, ruleset)` 的回傳 |
| 失敗 MatchRecord.error | 新增 `diagnostic` 子物件（僅失敗、僅 CSV 上傳路徑） |
| teacher-class R003 | `in` set 值英文→中文 |

**無 DB；成功 audit schema 不變。**

## QualifiedSetEmpty（擴充後）

```python
class QualifiedSetEmpty(MatcherError):
    exit_code = 10
    def __init__(self, message, *, trace=None, rule_stats=None,
                 culprit=None, total_pairs=0):
        super().__init__(message)
        self.trace = trace or []
        self.rule_stats = rule_stats or {}      # {rule_id: 失敗組數}
        self.culprit = culprit                  # 失敗最多的 rule_id（或 None）
        self.total_pairs = total_pairs
```

## rejection_summary（純函式回傳）

```python
{
  "total_pairs": 15,                  # 角色數 × 對象數
  "rule_stats": {"R001": 3, "R002": 0, "R003": 15},  # 各規則「沒過的組數」
  "culprit": "R003",                  # 失敗最多者；並列最大時取規則順序第一
}
```
- 計法：每組 (role,target) 的「沒過規則」= 全部規則 − matched_rules；逐一累加
- culprit：rule_stats 中數值最大的 rule_id

## 失敗 MatchRecord.error（CSV 上傳路徑）

```jsonc
"error": {
  "type": "QualifiedSetEmpty",
  "exit_code": 10,
  "message": "資格集合為空：...",
  "diagnostic": {                      // ★ 新增（僅此失敗類型）
    "total_pairs": 15,
    "rule_stats": {"R001": 3, "R003": 15},
    "culprit": "R003",
    "rules": {"R001": "老師的專業...", "R003": "班級特色..."}  // id→描述，供渲染
  }
}
```

## teacher-class R003（修正）

```yaml
# before
- {id: R003, description: "班級特色屬於核心三類之一（雙語、stem、藝術）",
   expr: {in: {field: target.feature, set: [bilingual, stem, arts]}}}
# after
- {id: R003, description: "班級特色屬於核心三類之一（雙語、stem、藝術）",
   expr: {in: {field: target.feature, set: [雙語, stem, 藝術]}}}
```
examples/teacher-class/roster.targets.yaml 的 `feature` 值同步：bilingual→雙語、arts→藝術、stem 不變。

## 不變

- 成功配對 audit（qualified_set/assignment/filter_trace/allocation_trace/template_snapshot）結構不變
- 「部分角色有資格」路徑不變（不 raise，個別頁照舊解釋）

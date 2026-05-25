# Data Model — 移除 default_targets

## 變更概覽

| 實體 | 變更 |
|---|---|
| `Template` dataclass | 移除 `default_targets: tuple` 欄位 |
| `audit.template_snapshot` | 移除 `default_targets` 子鍵 |
| `audit.schema_version` | `"1.3"` → `"1.4"` |
| Built-in YAML | teacher-class / study-group 拔 `default_targets:` 區段 |

無新增實體。

## Template（變更後）

```python
@dataclass(frozen=True)
class Template:
    schema_version: str
    id: str
    name: str
    description: str
    attributes: AttributeSchema
    ruleset: Ruleset
    ui_fields: tuple = ()
    report_fields: tuple = ()
    preferences_schema: Optional[PreferencesSchema] = None
    # default_targets 移除（原 line 65）
```

驗證規則：
- 無新增約束
- parse_template 對舊 YAML 含 `default_targets` 鍵 → 靜默忽略（research D1）

## audit JSON 結構（v1.4）

頂層：

```jsonc
{
  "schema_version": "1.4",   // ← 從 "1.3" 升
  "mechanism": "M0" | "M1" | "M2",
  "seed": 2026,
  "qualified_set": { ... },
  "assignment": { ... },
  "filter_trace": [ ... ],
  "allocation_trace": [ ... ],
  "roster_snapshot": {
    "roles": [...],
    "targets": [...]         // ← 本次配對使用的對象（不變）
  },
  "rules_snapshot": { ... },
  "template_snapshot": {
    "schema_version": "1.0",
    "id": "teacher-class",
    "name": "...",
    "description": "...",
    "attributes": { ... },
    "rules": [ ... ],
    // "default_targets": [...] ← 移除
    "ui_fields": [...],
    "report_fields": [...],
    "preferences_schema": {...}
  },
  "import_metadata": { ... }
}
```

## examples/*/roster.targets.yaml 結構（新增）

```yaml
targets:
  - id: <string>           # 唯一對象代號
    capacity: <int>        # 容量，≥ 1
    attributes:            # 依範本宣告的 target attributes
      <key>: <value>
  # ...
```

驗證規則（沿用 data_import._load_targets 既有邏輯）：
- 頂層必須有 `targets:` 鍵，值為非空 list
- 每個 entry 必須有 `id` 與 `capacity ≥ 1`
- `attributes` 內容由範本宣告的 target attributes 決定（type coercion）

## State Transitions

無。本 feature 純粹移除欄位、不引入新狀態。

## Backwards Compatibility

| 場景 | 行為 |
|---|---|
| 載入舊 YAML（含 `default_targets:`）| 靜默忽略該鍵，其餘正常解析 |
| 載入舊 v1.3 audit JSON 到 viewer | viewer 若不存取 `template_snapshot.default_targets`，無感；存取則回 None |
| CLI 跑配對缺 `.targets.yaml` | 報錯（不再 fallback） |
| Web 上傳 CSV 缺 sidecar | HTTP 400 |

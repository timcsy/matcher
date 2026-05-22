# Data Model: 模板系統

**Branch**: `002-template-system` | **Date**: 2026-05-22

本文件定義階段 2 新增的實體與既有實體的擴充。所有名稱為英文識別字；說明文字為繁中。

---

## 新增實體

```text
Template              模板（自包含的媒合情境定義）
TemplateRegistry      內建模板的查詢入口
AttributeSchema       屬性 schema 宣告（角色/對象側）
AttributeDecl         單一屬性宣告（key + type + required）
UIFieldDecl           UI 欄位宣告（key + label + type + ...）
ReportFieldDecl       稽核報告欄位宣告（key + label + source）
PreferencesSchema     志願欄位 schema 宣告
TemplateSnapshot      稽核紀錄中的模板快照（凍結版本）
```

---

## 詳細欄位

### Template

| Field | Type | Notes |
|---|---|---|
| `schema_version` | `str` | 固定為 `"1.0"`；未支援版本拋 `UnknownSchemaVersion` |
| `id` | `str` | 英文 kebab-case，例 `teacher-class` |
| `name` | `str` | 顯示名稱（繁中） |
| `description` | `str` | 一句話描述（繁中） |
| `attributes` | `AttributeSchema` | 必填 |
| `ruleset` | `Ruleset` | 必填（沿用階段 1 的型別） |
| `ui_fields` | `list[UIFieldDecl]` | 選填，預設空 |
| `report_fields` | `list[ReportFieldDecl]` | 選填，預設空 |
| `preferences_schema` | `PreferencesSchema \| None` | 選填 |

### AttributeSchema

| Field | Type | Notes |
|---|---|---|
| `roles` | `list[AttributeDecl]` | 角色側必須具備的屬性 |
| `targets` | `list[AttributeDecl]` | 對象側必須具備的屬性 |

### AttributeDecl

| Field | Type | Notes |
|---|---|---|
| `key` | `str` | 屬性鍵名（例 `speciality`） |
| `type` | `Literal["str", "int", "list_str"]` | 限定型別（對齊 data-model 階段 1 的 AttrValue） |
| `required` | `bool` | 預設 True |
| `description` | `str` | 繁中說明 |

### UIFieldDecl

| Field | Type | Notes |
|---|---|---|
| `key` | `str` | 表單欄位鍵名 |
| `label` | `str` | 繁中顯示文字 |
| `type` | `Literal["text", "number", "select", "multiselect", "textarea"]` | 表單元件類型 |
| `required` | `bool` | 預設 True |
| `options` | `list[str] \| None` | type 為 select/multiselect 時必填 |
| `placeholder` | `str \| None` |  |
| `help` | `str \| None` | 繁中說明 |

### ReportFieldDecl

| Field | Type | Notes |
|---|---|---|
| `key` | `str` | 報告欄位鍵名 |
| `label` | `str` | 繁中顯示文字 |
| `source` | `str` | 點分式路徑指向稽核紀錄欄位 |

### PreferencesSchema

| Field | Type | Notes |
|---|---|---|
| `max_choices` | `int` | 每人最多可填志願數 |
| `required` | `bool` | 是否強制填寫 |
| `description` | `str` | 繁中說明 |

### TemplateRegistry

```text
class TemplateRegistry:
    def list_ids(self) -> list[str]
    def get(self, id: str) -> Template       # 找不到 → TemplateNotFound
    def has(self, id: str) -> bool
```

### TemplateSnapshot（稽核紀錄欄位）

序列化形式（JSON）：

```json
{
  "id": "teacher-class",
  "schema_version": "1.0",
  "name": "教師-班級配對",
  "description": "...",
  "attributes": {...},
  "rules": [...],
  "ui_fields": [...],
  "report_fields": [...],
  "preferences_schema": null
}
```

---

## 既有實體擴充

### MatcherInput（修改）

新增欄位 `template: Template | None`；當非 None 時，`ruleset` 從 `template.ruleset` 取得，呼叫端不可同時提供 `ruleset` 與 `template`。

### AuditRecord（schema 升級為 1.1）

| 新欄位 | Type | Notes |
|---|---|---|
| `template_snapshot` | `TemplateSnapshot \| null` | 無模板路徑時為 null |

schema_version 從 `"1.0"` 升為 `"1.1"`。其他欄位不變。

---

## 驗證規則（輸入解析期執行）

| Check | 對應 FR | 觸發錯誤 |
|---|---|---|
| 頂層 `schema_version` 存在且為支援版本 | FR-002 | `UnknownSchemaVersion` |
| 頂層 `id`、`name`、`description`、`attributes`、`rules` 皆存在 | FR-001、FR-004 | `TemplateMissingField` |
| 模板 id 不衝突（內建 + 外部不可同 id 同時載入） | FR-013 | `TemplateConflict` |
| `attributes.roles` / `attributes.targets` 中每筆有 `key`、`type` | FR-003 | `TemplateMissingField` |
| `type` 在限定集合內（`str`/`int`/`list_str`） | FR-003 | `TemplateMissingField`（或 `UnknownAttributeType`，沿用 `TemplateMissingField` 即可，本階段不細分） |
| `ui_fields[].type` 在限定集合內 | FR-003 | `TemplateMissingField` |
| `ui_fields[].type ∈ {select, multiselect}` 時必填 `options` | FR-003 | `TemplateMissingField` |
| `preferences_schema` 非 None 且匯入名單帶有非空 preferences 值且 mechanism=M0 | FR-011 | `PreferencesNotSupported`（沿用階段 1） |
| 載入模板後執行時，名單缺少 attributes schema 宣告的必要屬性 | FR-001 + spec edge case | `UnknownAttribute`（沿用階段 1） |

---

## 狀態轉移

延續階段 1 的純函式管線；模板層為前置的「合成步驟」：

```text
TemplateInput（id 或檔案路徑）
  → [load_template] → Template
  → [resolve to MatcherInput] → 既有 pipeline → MatcherResult
  → [audit + template_snapshot] → AuditRecord (schema 1.1)
```

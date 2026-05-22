# Data Model: 個別查詢視圖

**Branch**: `005-individual-view` | **Date**: 2026-05-23

本 feature 為純呈現視圖，**不新增持久化實體**；所有資料皆從既有 audit 推導。

---

## 新增（純運算）函式

### `humanize_rule_description(description: str, template: Template) -> str`

將模板規則描述中的技術 token 替換為一般用語：

| Pattern | 替換為 |
|---|---|
| `role.<key>` | 「您的 <顯示名>」 |
| `target.<key>` | 「該對象的 <顯示名>」 |

`<顯示名>` 查找順序：
1. `template.attributes.{roles,targets}` 中對應 `AttributeDecl.description`
2. 若無 description → 用 `key` 原樣

`<key>` 不存在於模板 attributes → 替換為「您的 <key>」/「該對象的 <key>」（fallback，避免崩潰）。

### `build_individual_audit_subset(audit: dict, role_id: str) -> dict`

從完整 audit 中萃取屬於該角色的部分：

```python
{
    "schema_version": "individual-audit/1.0",
    "record_seed": <audit.seed>,
    "role_id": "<role_id>",
    "role_attributes": <audit.roster_snapshot.roles[role_id].attributes>,
    "role_preferences": <audit.roster_snapshot.roles[role_id].preferences>,
    "assignment": {
        "target_id": "<id|None>",
        "target_attributes": "<None | the target's attributes>"
    },
    "filter_trace_subset": [
        # 只含 audit.filter_trace 中 role_id 等於該 role 的條目
    ],
    "allocation_step": <None 或 audit.allocation_trace 中該 role 的單一 step 物件>
}
```

若 `role_id` 不存在於 audit.roster_snapshot.roles → 拋 `MatchRecordNotFound`
（其 status_code = 404，由 Web 層處理）。

---

## Web 層常數

### `FORBIDDEN_TOKENS`（在 humanize.py 或專屬 testing helper）

```python
FORBIDDEN_TECHNICAL_TOKENS = (
    "filter_trace",
    "allocation_trace",
    "qualified_set",
    "random_index",
    "exit_code",
)
FORBIDDEN_PATTERNS = (
    r"\brole\.\w+",
    r"\btarget\.\w+",
)
```

整合測試以此為清單斷言「response.text 不含任何禁用 token / 不匹配任何禁用 pattern」。

---

## 既有實體擴充

- **audit**：完全不變。
- **MatchRecord**：完全不變。
- **Template**：完全不變。
- **AttributeDecl**：使用既有 `description` 欄位作為「顯示名」來源。

---

## 路由與資料流

```text
User → GET /match/{rid}/role/{role_id}
     → 後端:
        1. store.get(rid) → MatchRecord
        2. 若 record.status == "failed" → 404 個別錯誤頁
        3. 若 role_id 不在 record.audit.roster_snapshot.roles → 404 個別錯誤頁
        4. 模板 = TemplateRegistry().get(record.template_id)
        5. 渲染 individual_view.html，context 包含:
           - role_attrs
           - assignment_target_attrs (或 None)
           - filter_trace_subset
           - allocation_step
           - humanized_rule_lines（已替換的規則說明）

User → GET /match/{rid}/role/{role_id}/audit.json
     → 後端:
        1. 同上 1-3
        2. subset = build_individual_audit_subset(record.audit, role_id)
        3. return JSON download
```

---

## 驗證規則

| Check | 對應 FR | 觸發回應 |
|---|---|---|
| record_id 不存在 | FR-006 | 404 + individual_error.html「找不到該次媒合的紀錄」 |
| record.status == "failed" | FR-006 | 404 + individual_error.html「該次媒合執行失敗」 |
| role_id 不在 record.audit | FR-006 | 404 + individual_error.html「您不在這次媒合的名單中」 |
| 個別查詢頁 HTML response 含禁用 token | FR-003 + SC-002 | 自動化測試失敗 |

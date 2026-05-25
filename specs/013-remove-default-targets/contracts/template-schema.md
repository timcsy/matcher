# Contract — Template Schema 變更

## Template dataclass

**Before**：
```python
@dataclass(frozen=True)
class Template:
    ...
    preferences_schema: Optional[PreferencesSchema] = None
    default_targets: tuple = ()  # ← 移除
```

**After**：
```python
@dataclass(frozen=True)
class Template:
    ...
    preferences_schema: Optional[PreferencesSchema] = None
```

## template_loader.parse_template

| 輸入 YAML | 變更前 | 變更後 |
|---|---|---|
| 含 `default_targets:` 段 | 解析成 `tuple[Target, ...]` 並指派 | **靜默忽略** |
| 不含 `default_targets:` | `default_targets=tuple()` | 不變（無此欄位） |
| `default_targets[].id` 缺 | 報錯 `TemplateMissingField` | 不會觸發（整段忽略） |

## template_loader.dump_template

| 輸入 | 變更前輸出 | 變更後輸出 |
|---|---|---|
| Template 物件 | `{... default_targets: [...]}` 若非空 | **永不輸出** `default_targets` 鍵 |

## Internal API 影響點（必須一次性更新）

| 檔/呼叫點 | 變更 |
|---|---|
| `audit.py:111` `default_targets: [t.to_dict() for t in tpl.default_targets]` | 刪整段 |
| `data_import.py:278-280` `if template.default_targets: return template.default_targets` | 刪 fallback 分支 |
| `data_import.py:283-285` 錯誤訊息 | 改為 research D2 文字 |
| `web/roster_form.py:82` `if template.default_targets: return None` | 改為「未填對象 → 回 None」邏輯 |
| `web/template_form.py:147-163` `# 5. default_targets ... tpl["default_targets"] = ...` | 刪整段 |
| `web/routes/pages.py:124` `for i, t in enumerate(tpl.default_targets or []):` | 刪迴圈（template_detail 不再顯示預設對象段） |
| `web/routes/match.py` 各處 `tpl.default_targets`、`not tpl.default_targets`、`requires_targets` | 對象段一律必填，邏輯簡化 |
| `web/templates/roster_form_fill.html` `{% if requires_targets %}` | 條件拿掉 |
| `web/templates/template_detail.html` 預設對象展示段 | 刪 |
| `templates/builtin/teacher-class.yaml` `default_targets:` 區段 | 刪 |
| `templates/builtin/study-group.yaml` `default_targets:` 區段 | 刪 |

## 向下相容（read 路徑）

- 載入舊自訂範本 YAML（user data dir 中的 v1.yaml 等）：靜默忽略 `default_targets:`
- 載入舊 v1.3 audit JSON：viewer 不主動讀 `template_snapshot.default_targets`；若讀 → undefined（可能 KeyError，但既有 viewer 不會這麼做）

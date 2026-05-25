# Phase 1 — Data Model：模板創作工具 UI

無新增 audit / record schema；新增持久化檔案佈局 + 3 個 view model + 1 個純函式介面。

## 1. 自訂模板持久化檔案佈局

```
data/templates/                           # 根目錄；不入 git 但加 .gitkeep
├── <template-id>/                        # 每個自訂模板一個目錄
│   ├── v1.yaml                           # 第一版
│   ├── v2.yaml                           # 第二版（編輯後產生）
│   └── v<N>.yaml                         # 第 N 版
└── ...
```

**規則**：
- 目錄名 = template id（限定 `[a-z0-9-]+`）
- 檔名 = `v<N>.yaml`，N 為正整數，自動遞增
- 「目前版本」= 該目錄中數字最大的 `v<N>.yaml`
- 檔內為合法 `parse_template_yaml` 可接受的 YAML

## 2. TemplateRegistry 擴充（核心職責擴充）

**新增方法**（不改既有方法簽名）：

```python
class TemplateRegistry:
    def __init__(self, custom_dir: Path = Path("data/templates")) -> None:
        self._cache: dict[str, Template] = {}
        self._custom_versions: dict[str, dict[int, Template]] = {}  # id -> {version_n: Template}
        self._custom_dir = custom_dir
        self._scan()                       # 既有：掃 builtin
        self._scan_custom_dir()            # 新增

    def _scan_custom_dir(self) -> None:
        """掃 data/templates/<id>/v<N>.yaml；最新版本進 _cache；所有版本進 _custom_versions。"""

    def is_builtin(self, template_id: str) -> bool:
        """區分內建 vs 自訂。"""

    def list_versions(self, template_id: str) -> list[int]:
        """回此自訂模板的所有版本號（排序）。內建模板 → []。"""

    def get_version(self, template_id: str, version: int) -> Template:
        """取指定版本（用於版本歷史查看 + 編輯預載）。"""

    def invalidate(self) -> None:
        """重新掃描所有來源；POST /templates/save 後呼叫。"""

    def save_custom(self, tpl_dict: dict) -> tuple[str, int]:
        """寫入新版本檔案；返回 (id, version)；id 衝突拒絕（raise ValueError）。"""
```

## 3. SimpleFormViewModel（簡單模式表單）

`POST /templates/save` 接受的表單欄位（multipart / form-urlencoded）：

| 欄位 | 型別 | 必填 | 說明 |
|---|---|---|---|
| `mode` | str | ✓ | `"simple"` 或 `"advanced"` |
| `template_id` | str | ✓ | kebab-case |
| `template_name` | str | ✓ | 顯示名 |
| `template_description` | str | ✓ | 一句描述 |
| `scenario_template` | str | – | （簡單模式）場景樣板代號 |
| `role_attr_<i>_key` / `role_attr_<i>_type` / `role_attr_<i>_required` / `role_attr_<i>_description` / `role_attr_<i>_aliases` | str (i=0..N) | – | 動態屬性表行；空白即略過 |
| `target_attr_<i>_*` | str | – | 同上對象屬性 |
| `rule_<i>_type` | str | – | `"ge"/"le"/"eq"/"in"/"role_in_target_field"` |
| `rule_<i>_id` | str | – | 「R001」等 |
| `rule_<i>_field` / `rule_<i>_value` / `rule_<i>_set` / `rule_<i>_role_field` / `rule_<i>_target_field` | str | – | 依規則類型填 |
| `rule_<i>_custom_description` | str | – | 若提供則覆蓋自動生成 |
| `target_<i>_id` / `target_<i>_capacity` / `target_<i>_attr_<key>` | str | – | 預設對象 |
| `prefs_enabled` | bool | – | 啟用 preferences_schema |
| `prefs_max_choices` | int | – | 啟用後填 |
| `prefs_description` | str | – | 啟用後填 |

**進階模式**只需：`mode=advanced`、`template_id`、`raw_yaml`。

`assemble_template_yaml(form: dict) -> dict` 純函式負責把這份 dict 組成標準模板 YAML dict（可被 parse_template 接受）。

## 4. AdvancedFormViewModel

`POST /templates/save` 進階模式僅需：

| 欄位 | 型別 | 必填 |
|---|---|---|
| `mode` | str = `"advanced"` | ✓ |
| `raw_yaml` | str | ✓ |

後端直接 `yaml.safe_load(raw_yaml)` → 走相同 `parse_template` + 儲存流程。

## 5. ValidationResultViewModel

`POST /templates/validate` 與 `POST /templates/save` 失敗時的 JSON 回應：

```json
{
  "ok": true|false,
  "errors": ["錯誤訊息 1", "錯誤訊息 2"],
  "summary": {
    "id": "club-signup",
    "name": "社團報名",
    "attribute_count": {"roles": 3, "targets": 3},
    "rule_count": 2,
    "has_preferences_schema": false,
    "default_target_count": 3
  }
}
```

## 6. TemplateDetailViewModel（修改）

`/templates/<id>` 頁面新增 context 欄位：

| 欄位 | 型別 | 來源 |
|---|---|---|
| `is_builtin` | bool | `registry.is_builtin(id)` |
| `versions` | list[(int, str)] | (N, mtime ISO) for each v<N>.yaml |
| `current_version` | int \| None | 自訂模板才有 |

樣板規則：
- `is_builtin == True` → 顯示「Fork 為自訂模板」按鈕；無「編輯」「版本歷史」段
- `is_builtin == False` → 顯示「編輯」按鈕 +「版本歷史」段；列出 versions 表格

## 7. ScenarioTemplate（場景樣板常數）

`src/matcher/web/template_form.py` 內 module-level 常數 dict：

```python
SCENARIO_TEMPLATES = {
    "blank": {...},               # 全空
    "club-signup": {...},         # 社團報名（3 屬性 + 2 規則 + 3 default_targets）
    "tutoring": {...},            # 課輔配對
    "study-group-like": {...},    # 仿研習分組
    "teacher-class-like": {...},  # 仿教師班級
}
```

每個 scenario 是 `assemble_template_yaml` 接受的 form-shape dict（不是最終 YAML），讓 jinja2 預填表單。

## 8. 不變的契約

- 既有 audit / record / template schema：完全不變
- `parse_template`, `Template` dataclass：不改
- `TemplateRegistry.__init__` 簽名擴充（加 `custom_dir` optional 參數，預設行為相容）
- 既有 `list_ids()`, `get()`, `has()`：不改實作（僅 cache 內容變多）

## 9. State transitions

```
建立模板：
  使用者填表 → POST /templates/validate → 顯示 ok + summary
            → POST /templates/save → 寫 data/templates/<id>/v1.yaml
            → registry.invalidate() → 新 id 出現在所有列表

編輯模板（id 已存在）：
  GET /templates/<id>/edit → 載入 v_max → 渲染表單
                          → POST /templates/save (mode=advanced/simple, id=<同>)
                          → 寫 data/templates/<id>/v(N+1).yaml
                          → registry.invalidate()
                          → 「目前版本」變為 N+1，舊版仍可查

Fork 內建模板：
  GET /templates/<builtin-id> → 點「Fork」→ 跳 /templates/new?fork=<id>
  → 表單預填 builtin 內容 + id="<原id>-fork"
  → 使用者改 id → 儲存 → 變新自訂模板 v1
```

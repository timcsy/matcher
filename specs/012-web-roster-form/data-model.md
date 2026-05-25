# Phase 1 — Data Model：Web UI 直接填名單

無新增持久化 / audit schema 改動。新增 1 個轉換層（UI 表單 → CSV bytes）+ 2 個 view model。

## 1. UI 填寫頁表單欄位

`POST /match/run-from-form` 接受的表單欄位：

| 欄位 | 必填 | 說明 |
|---|---|---|
| `template_id` | ✓ | hidden input；從 query string 帶來 |
| `seed` | ✓ | 整數，使用者輸入 |
| `mechanism` | ✓ | `"M0"` / `"M1"` / `"M2"`，使用者選 |
| `role_<i>_id` | – | 角色代號；空白則自動生成 |
| `role_<i>_<key>` | 依範本 required | 對應範本「角色資料欄位」每個 key 一個 input |
| `target_<j>_id` | (US2) ✓ | 對象代號 |
| `target_<j>_capacity` | (US2) ✓ | 對象容量 |
| `target_<j>_<key>` | (US2) 依範本 | 對應「對象資料欄位」 |

**收集邏輯**：
- `_collect_indexed_rows()`（feature 011 既有）可直接重用
- 收完後產出 `list[dict]`：每個 dict 是一筆角色 / 對象

## 2. UI 表單 → CSV bytes 轉換（新純函式）

`src/matcher/web/roster_form.py`（新檔）：

```python
def assemble_roster_csv_bytes(form: dict, template: Template) -> bytes:
    """UI 表單 → CSV bytes（與直接上傳 CSV 路徑 bytewise 等價）。

    流程：
    1. 蒐集 role_<i>_<key> 欄位 → list[dict]
    2. 過濾空白行（全部 key 都空 → 略過）
    3. 組 CSV header：id + 範本宣告的每個 attribute key
    4. 對每位角色寫一行
    5. 回 bytes（utf-8-sig，與既有 CSV path 一致）
    """


def assemble_targets_yaml_bytes(form: dict, template: Template) -> bytes | None:
    """UI 表單對象段 → sidecar YAML bytes。

    無對象資料（範本有 default_targets，使用者沒填）→ 回 None。
    有對象資料 → 組合 targets: [...] dict + yaml.safe_dump（utf-8）。
    """
```

## 3. RosterFormViewModel（填寫頁渲染 context）

`/match/new/fill?template_id=X` 注入的 context：

| 欄位 | 型別 | 來源 |
|---|---|---|
| `template` | Template | TemplateRegistry.get(template_id) |
| `role_attrs` | list[AttributeDecl] | template.attributes.roles |
| `target_attrs` | list[AttributeDecl] | template.attributes.targets |
| `requires_targets` | bool | template.default_targets 為空 → True |
| `has_prefs_schema` | bool | template.preferences_schema 非 None |
| `mechanisms` | list[(code, label)] | 沿用 MECHANISMS 常數 |

## 4. ThreeWayChooserViewModel（new_match.html 三選一）

`/match/new` 新增的 Alpine 局部 state：

```js
{
  mode: 'upload',  // 'upload' | 'fill' | 'from-record'
}
```

模板：
```jinja
<div x-data="{ mode: 'upload' }">
  <div class="flex gap-2">
    <button @click="mode='upload'" :class="...">📂 上傳名單檔</button>
    <button @click="mode='fill'" :class="...">✏️ 直接填名單</button>
    <a href="/matches">📌 從過去紀錄</a>
  </div>
  <div x-show="mode === 'upload'">{# 既有上傳 form #}</div>
  <div x-show="mode === 'fill'">{# 範本選 + 跳轉按鈕 #}</div>
</div>
```

## 5. POST /match/run-from-form 流程

```
1. 接收表單 → form dict
2. 取 template = TemplateRegistry.get(form["template_id"])
3. 驗證 mechanism、seed
4. 組 CSV bytes:
   csv_bytes = assemble_roster_csv_bytes(form, template)
5. 組 targets YAML bytes（若 template.default_targets 為空）:
   targets_yaml = assemble_targets_yaml_bytes(form, template)
6. 寫到 tempfile（.csv + .targets.yaml sidecar）
7. 呼叫 load_roster_csv(tmp_path, template)
8. 後續：
   a. 若 mechanism=M0 → 直接 run_match → record → redirect /match/{rid}
   b. 若 mechanism in (M1,M2) AND template.preferences_schema → 不跑 pipeline；轉發到 /match/preferences 頁面（hidden inputs 含 roster_bytes_b64 + targets_bytes_b64 + template_id + mechanism + seed）
   c. 若 mechanism in (M1,M2) AND not preferences_schema → run_match → 預期 MechanismRequiresPreferences 拒絕 → 失敗 record
```

## 6. 不變的契約

- record / audit / template schema：完全不變
- `data_import.load_roster_csv()`, `_load_targets()`：簽名與行為不動
- `Template`、`Roster`、`Role`、`Target` dataclass：不動
- feature 009 `/match/preferences` 端點：不動（只是多了個新呼叫者）
- 既有 `/match/new` GET：行為加碼但不破壞（mode='upload' 預設 = 原行為）

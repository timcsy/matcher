# CLI Contract: matcher template ＋ matcher run（擴充）

**Branch**: `002-template-system` | **Date**: 2026-05-22

本檔定義階段 2 新增與修改的 CLI 介面、退出碼與輸出格式。所有錯誤訊息為繁中。

---

## 新增：`matcher template` 子應用

### `matcher template list`

```text
matcher template list [--format text|json]
```

#### 行為
列出所有可用模板（目前僅內建）。預設輸出為繁中表格（id / 名稱 / 描述）。

#### 範例輸出（text）

```text
ID             名稱            一句話描述
-------------  --------------  -----------------------------------
teacher-class  教師-班級配對   依專業與班級需要科目配對任課教師
study-group    研習分組        依年級與容量限制分配學生到研習組別
```

#### 退出碼

| Code | 意義 |
|---|---|
| 0 | 成功 |
| 2 | CLI 參數錯誤（Typer 處理） |

---

### `matcher template show <id>`

```text
matcher template show <id> [--format text|yaml|json]
```

#### 行為
列出指定模板的完整內容；預設 text 為繁中可讀摘要，可改 `--format yaml` 印原始檔。

#### 退出碼

| Code | 意義 | 對應錯誤類別 |
|---|---|---|
| 0 | 成功 | — |
| 20 | 模板 id 不存在 | `TemplateNotFound` |
| 2 | 參數錯誤 | — |

#### `TemplateNotFound` 訊息範例

```text
錯誤：找不到模板 `no-such`。
細節：目前可用模板：teacher-class、study-group。
建議：執行 `matcher template list` 檢視所有可用模板。
```

---

### `matcher template export <id> --output <path>`

```text
matcher template export <id> --output <path>
```

#### 行為
將指定內建模板序列化為 YAML 寫入 `--output`；該檔可由 `matcher run --template-file <path>` 重新匯入。

#### 不變式

- 匯出的檔案重新匯入後，`Template` 物件結構完全相同（key 排序、欄位完整）。
- 給定相同名單與 seed，使用「`--template <id>`」與「先 export 後 `--template-file <path>`」兩條路徑產生的稽核紀錄逐位元組相同（SC-003）。

#### 退出碼

| Code | 意義 | 對應錯誤類別 |
|---|---|---|
| 0 | 成功 | — |
| 20 | 模板 id 不存在 | `TemplateNotFound` |
| 2 | 參數錯誤 | — |

---

## 修改：`matcher run`

```text
matcher run \
  ( --template <id> | --template-file <path> | --rules <path> --roster <path> ) \
  --roster <path>          # 使用 --template 時仍需提供名單檔
  --seed <int>
  [--preferences <path>]
  [--mechanism M0]
  [--output <audit.json>]
```

### 三組參數互斥規則（FR-016）

呼叫端必須恰好提供以下三組之一：

| 組合 | 說明 |
|---|---|
| (A) `--template <id>` + `--roster <path>` | 使用內建模板 |
| (B) `--template-file <path>` + `--roster <path>` | 使用外部模板 |
| (C) `--rules <path>` + `--roster <path>` | 階段 1 既有路徑（向後相容） |

任意組合違反互斥（例如同時提供 `--template` 與 `--rules`）→ CLI 立即以明確繁中訊息拒絕、exit 2。

### 退出碼擴充

| Code | 意義 | 對應錯誤類別 | 來源 |
|---|---|---|---|
| 0–17 | 階段 1 既有 | （沿用） | 階段 1 |
| 20 | 模板 id 不存在 | `TemplateNotFound` | 階段 2 新增 |
| 21 | schema_version 不支援 | `UnknownSchemaVersion` | 階段 2 新增 |
| 22 | 模板必填欄位缺失 | `TemplateMissingField` | 階段 2 新增 |
| 23 | 模板 id 衝突 | `TemplateConflict` | 階段 2 新增（罕見） |

### stdout 摘要擴充

模板路徑下的 stdout 摘要新增一段「使用的模板」：

```text
=== 模板 ===
ID：teacher-class
名稱：教師-班級配對
版本：1.0

=== 規則檔（來自模板）===
（沿用既有摘要）

...（其餘與階段 1 一致）...
```

---

## 不變式（契約測試會驗證）

- **向後相容（SC-007）**：任何**不**使用 `--template` / `--template-file` 的呼叫，行為與階段 1 完全一致；階段 1 既有 48 個自動化測試 100% 通過。
- **template_snapshot 完整性（SC-004）**：使用模板路徑時，`audit.template_snapshot` 為完整 Template 物件；不使用模板路徑時為 `null`。
- **匯出-匯入冪等（SC-003）**：`export` 後 `--template-file` 載入，給定相同名單與 seed → 稽核紀錄逐位元組相同。
- **preferences 拒絕（SC-006）**：「研習分組」模板宣告 `preferences_schema`，匯入名單帶有非空 preferences 時，M0 機制下回應 exit 17。
- **三組參數互斥（SC-008）**：同時提供 → exit 2 + 繁中提示。

# Data Model: Web UI 主流程

**Branch**: `004-web-ui-main` | **Date**: 2026-05-22

---

## 新增實體

```text
MatchRecord       媒合紀錄（每次 Web 執行一筆）
MatchStore        媒合紀錄儲存（檔案系統）
default_targets   模板 schema 新增的選填欄位（將 target 資料內嵌進模板）
```

---

## 詳細欄位

### MatchRecord（持久化於 `data/matches/<id>.json`）

| Field | Type | Notes |
|---|---|---|
| `schema_version` | `Literal["match-record/1.0"]` | media record 自有 schema 版本（與 audit 分離） |
| `id` | `str` | `<YYYY-MM-DDTHH-MM-SS>-<uuid8>`；也是檔名（去 `.json`） |
| `created_at` | `str` | ISO 8601 時間字串 |
| `template_id` | `str` | 模板 id |
| `seed` | `int` |  |
| `input_file` | `str` | 上傳檔的 basename；無上傳時為 `null`（內建範例情境） |
| `mechanism` | `Literal["M0"]` | 本階段固定 M0 |
| `status` | `Literal["success", "failed"]` |  |
| `audit` | `dict \| null` | status=success 時為完整 audit；失敗時 null |
| `error` | `dict \| null` | status=failed 時為 `{type, exit_code, message}`；成功時 null |

### MatchStore（無狀態類別）

```text
class MatchStore:
    base_dir: Path                                  # 預設 data/matches/

    def save(record: MatchRecord) -> str             # 寫入並回傳 id
    def list(limit: int = 50) -> list[MatchRecord]   # 依時間遞減
    def get(record_id: str) -> MatchRecord           # 找不到 → MatchRecordNotFound
```

寫入時採 atomic write：先寫 `<id>.json.tmp` → `os.replace` 為 `<id>.json`。

### `Template.default_targets`（既有實體擴充）

| Field | Type | Notes |
|---|---|---|
| `default_targets` | `tuple[Target, ...]` | 預設空 `()`；模板可內嵌預設對象資料 |

`template_loader.parse_template()` 新增解析；`template.py` 的 `Template` dataclass 新增此欄位。

---

## 新增錯誤類別

```text
MatchRecordNotFound          exit n/a（Web 層回 404）
UploadTooLarge               exit n/a（Web 層回 400 + 訊息）
UploadInvalidMime            exit n/a（Web 層回 400 + 訊息）
```

這些不繼承 `MatcherError`（不在 CLI 層使用），直接由 Web routes 拋出並由 FastAPI exception handler 處理。

---

## HTTP 路由與資料流（簡介，詳細於 contracts/http-endpoints.md）

```text
GET  /                            首頁
GET  /templates                   模板列表
GET  /templates/{id}              模板詳情
GET  /match/new                   新建媒合（step 1）
POST /match/new/step{2,3}         向導下一步（HTMX swap）
POST /match/run                   執行媒合（上傳檔 + seed）→ 302 → /match/{record_id}
GET  /match/{record_id}           結果頁
GET  /match/{record_id}/audit     下載 audit JSON
GET  /matches                     過去媒合列表
GET  /static/{path}               靜態資源
```

---

## 驗證規則

| Check | 觸發錯誤 | HTTP code |
|---|---|---|
| 上傳檔 > 5 MB | `UploadTooLarge` | 400 |
| 上傳檔 MIME 不在 csv/xlsx 白名單 | `UploadInvalidMime` | 400 |
| seed 非整數 | 表單驗證錯誤 | 400 |
| 模板 id 不存在 | `TemplateNotFound`（沿用階段 2a） | 404 |
| MatchRecord id 不存在 | `MatchRecordNotFound` | 404 |
| 既有的所有 MatcherError 子類 | 對應之 exit code 映射為訊息，渲染於結果頁 | 200 + 失敗紀錄寫入 |

---

## 狀態轉移

```text
User → GET /match/new
     → POST /match/run（上傳 + seed + template）
        → 後端：
            1. 驗證上傳大小與 MIME
            2. 將檔寫到 tmp → load_roster_csv 或 load_roster_xlsx
            3. 載入 template（內含 default_targets）
            4. run_match(MatcherInput(...))
            5a. 成功 → MatchRecord(status=success, audit=...) → MatchStore.save
            5b. 失敗 → MatchRecord(status=failed, error=...) → MatchStore.save
            6. tmp.unlink()
            7. redirect 到 /match/{record_id}
```

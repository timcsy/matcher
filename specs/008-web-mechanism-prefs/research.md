# Phase 0 — Research：Web UI 機制選擇 + 結果頁志願展示

本 feature 無 NEEDS CLARIFICATION（spec 階段已釐清）。本檔記錄技術決策——皆採既有約束 + 已驗證做法的最簡延伸。

## D1：mechanism 表單參數的接收與驗證

**Decision**：`POST /match/run` 新增 `mechanism: str = Form("M0")`；在 routes 內 `.upper().strip()` 後白名單比對 `{"M0", "M1", "M2"}`；非法值 → `HTTPException(400)`，由既有錯誤頁顯示。

**Rationale**：
- FastAPI Form 預設可選 + 預設值；既有 routes/match.py 已是此 pattern。
- 白名單比對 vs Enum：白名單 3 行程式碼 vs Enum 加類別宣告——遵循 YAGNI；mechanism 名是穩定 token，非翻譯需求。
- 大小寫規範化讓 CLI 與 Web 行為一致（CLI 已有同樣處理）。

**Alternatives**：
- (a) Pydantic Enum / Literal — 過度抽象，無 schema 共用需求。
- (b) 不規範化、嚴格 case-sensitive — 與 CLI 行為不一致，使用者易撞錯。

## D2：UI 機制下拉的「說明文案」呈現

**Decision**：下拉旁直接放一行 `<small>` 提示：「無志願選 M0；有志願選 M1（隨機輪流挑）或 M2（先填高志願）」。**不加 tooltip / popover / 模板說明連結**。

**Rationale**：
- 教訓 6：技術詞零容忍；簡短中文比 hover 細節更友善。
- 模板說明本身已在 `/templates/{name}` 頁面（沿用 2a），重複資訊會稀釋。
- YAGNI：tooltip 需引入 alpine.js / 額外 CSS，違反「無新依賴」。

**Alternatives**：
- (a) Tooltip 含長解釋 — 多引入 JS，違反「無新依賴」。
- (b) 不放任何提示 — 使用者無從判斷該選哪個。

## D3：「處理順序」與「志願排名欄」的渲染位置

**Decision**：
- **處理順序段**：放在 `match_result.html` 結果表上方、機制名稱下方；單行排列「S03 → S01 → S05 → ...」並以 `roster_snapshot` 取出顯示名（如「王小明」）。
- **志願排名欄**：在現有分配表新增一欄；M0 路徑 `{% if mechanism != 'M0' %}` 整欄隱藏；M1/M2 路徑顯示「第 N 志願」或「抽籤」。

**Rationale**：
- 沿用 audit `processing_order` + `allocation_trace[i].preference_rank` + `fallback_random_index`，無新欄位。
- conditional 欄而非 conditional 行：保持表格寬度穩定、易讀。
- 文案「第 N 志願」/「抽籤」皆中文，通過 FORBIDDEN_TECHNICAL_TOKENS。

**Alternatives**：
- (a) 將「處理順序」放在分配表的一欄 — N 角色時表會擠；用獨立段較清楚。
- (b) 不顯示 fallback 識別 — 違反原則 5「對使用者透明」。

## D4：個別查詢頁的三分支文案

**Decision**：在 `individual_view.html` 加 jinja2 if/else：

```jinja
{% if mechanism in ('M1', 'M2') and assigned %}
  {% if preference_rank is not none %}
    <p>您被分到第 {{ preference_rank }} 志願：{{ assigned_display }}</p>
  {% elif preferred_count > 0 %}
    <p>您原本的志願已被分配給其他人，由公平抽籤分到 {{ assigned_display }}。</p>
  {% else %}
    <p>您未在志願清單中，由公平抽籤分到 {{ assigned_display }}。</p>
  {% endif %}
{% endif %}
```

**Rationale**：
- 三分支邏輯由 `preference_rank` (None/N) + `preferred_count` (audit 中該角色的 `preferred_order` 長度) 推導；無新 audit 欄位。
- `preferred_count` 由 routes/individual.py 從 audit 預先計算後注入 context；模板只做純展示。
- M0 路徑或未分配時整段不顯示——符合 SC-003 第二句。

**Alternatives**：
- (a) 將三分支邏輯放模板 macro — 只有 1 處使用，違反 YAGNI。
- (b) 新增 audit 欄位 `assignment_kind: "preference" | "fallback_after_prefs" | "fallback_no_prefs"` — 動核心、升 schema，違反 FR-011 與教訓 7。

## D5：Web/CLI bytewise 等價的測試做法

**Decision**：在 `test_web_cli_audit_equivalence.py` 內：
1. CLI runner 跑 `app run --template study-group --roster-csv ... --seed 2026 --mechanism M2 --output cli.json`
2. FastAPI TestClient POST `/match/run` 同 template + 同 file upload + seed=2026 + mechanism=M2，取得 record_id；讀 `data/matches/{rid}.json`，從中取 audit 五段
3. 比對兩個 audit dict 的 `qualified_set`、`assignment`、`filter_trace`、`allocation_trace`、`template_snapshot` 各自 `json.dumps(..., sort_keys=True, ensure_ascii=False)` 是否相等

**Rationale**：
- 不比整檔（record 含 created_at 等時間戳），只比 5 個核心欄位。
- 既有 3a 已驗證「Web 與 CLI 同 seed → 五段相同」對 M0；此測試延伸到 M1/M2。

**Alternatives**：
- (a) 比 audit JSON 整檔 — 會被 import_metadata.original_filename 等差異打掉。
- (b) 僅比 `assignment` — 弱保證；不能抓出 trace 順序差異。

## 既有依賴沿用

- FastAPI / uvicorn / jinja2 / python-multipart：所有 Web 機制已具備
- httpx (dev)：TestClient 已使用
- pytest fixtures：沿用 `tmp_path`、現有 `tests/conftest.py`（若有）

**結論**：所有未知已解，可進 Phase 1。

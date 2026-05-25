# Phase 0 — Research：模板創作工具 UI

無 NEEDS CLARIFICATION（7 個方向問題已釐清）。本檔記錄 6 項技術決策。

## D1：自訂模板持久化檔案佈局

**Decision**：`data/templates/<id>/v<N>.yaml`，N 從 1 開始單調遞增。

**範例**：
```
data/templates/
├── .gitkeep
├── club-signup/
│   ├── v1.yaml
│   └── v2.yaml
└── tutoring/
    └── v1.yaml
```

**Rationale**：
- 每個 id 自己一個目錄、版本獨立檔案——git 友善（diff 一目了然，雖然 data/ 不入 git）
- 「目前版本」= max(v\d+\.yaml)，邏輯簡單
- 同 id 多版本不衝突；不同 id 完全隔離
- 與 `data/matches/<id>.json` 同檔案系統風格（沿用 vision 架構決策）

**Alternatives**：
- (a) `data/templates/<id>.yaml` + 歷史在 `.history/<id>-<timestamp>.yaml` — 兩處同步麻煩
- (b) SQLite — 違反 vision 架構「不引入 DB」

## D2：TemplateRegistry 掃描策略

**Decision**：`TemplateRegistry.__init__` 同時掃描 builtin + custom；新增 `_scan_custom_dir(custom_dir: Path = Path("data/templates"))` 方法。**每次 `list_ids()` / `get()` 呼叫不重新掃描**——使用者新建模板 → POST /templates/save 顯式呼叫 `registry.invalidate()` 讓下次取用時重新掃。

**Rationale**：
- 不每次重新掃描：避免 N+1 IO；FastAPI Web 一個請求可能呼叫多次 `get()`
- 顯式 invalidate：寫入後立即可見；其他請求即時生效
- TemplateRegistry 在 FastAPI 中為 module-level singleton 或 dependency；保持單一 instance 是必要

**Alternatives**：
- (a) 每次 `list_ids()` rescan — 簡單但 IO 成本
- (b) 純 file watcher — 增依賴 + macOS/Linux 差異

## D3：內建 vs 自訂 id 衝突解決

**Decision**：**儲存階段拒絕**——`POST /templates/save` 在寫檔前檢查 builtin id 集合（hardcoded for now 或從 `_builtin_cache.keys()` 取）；衝突 → 400 + 繁中錯誤訊息。

執行階段（`get(id)` 查詢）若同 id 存在於兩處（不可能發生，但保險），優先 builtin。

**Rationale**：
- 儲存階段攔截最早，使用者意圖最明確
- 不允許「自訂覆蓋內建」——保護內建模板黃金檔測試
- 「想改內建」的正確路徑是「Fork as 自訂模板」（US3 已有）

**Alternatives**：
- (a) 允許自訂覆蓋內建 — 黃金檔測試會破壞；違反 spec FR-010 + SC-005
- (b) 自訂模板自動加前綴（如 `custom-`）— 命名規則強加使用者，不友善

## D4：簡單模式 → YAML 組裝邏輯

**Decision**：新增 `src/matcher/web/template_form.py` 含純函式 `assemble_template_yaml(form_data: dict) -> dict`：

```python
def assemble_template_yaml(form: dict) -> dict:
    """
    輸入：表單 POST 資料 dict（schema 見 data-model.md）
    輸出：完整模板 YAML dict（可被 parse_template 接受）

    特別處理：
    - rules[i] 依 type（"ge"/"le"/"eq"/"in"/"role_in_target_field"）組對應 expr
    - 自動生成 description（如「角色年級必須 ≥ 4」），但若 form 提供 custom_description 則用使用者版
    - 屬性表 / 對象表 / 預設對象表的空白行自動過濾
    """
```

並含子函式：
- `_build_expr(rule_type, fields) -> dict`
- `_auto_description(rule_type, fields, attributes) -> str`（依規則類型 + 角色/對象的中文 description 組合，如「角色的學生姓名等於 X」）

**Rationale**：
- 純函式集中於一處，易單元測試（覆蓋 5 種規則類型 + auto-description）
- 不依賴 jinja2/HTTP；理論上 CLI 也可用（雖然本 feature 不開 CLI）
- 自動生成 description 邏輯集中，便於統一通過技術詞零容忍正則

**Alternatives**：
- (a) 把組裝邏輯散在 jinja2 樣板中 — 不可測試
- (b) 在 routes 內 inline — 違反單一責任

## D5：US4「以此版本再執行」的 audit-snapshot 還原機制

**Decision**：在 `routes/match.py` 新增 helper：
```python
def _resolve_template_from_match_or_snapshot(template_id: str | None, snapshot_rid: str | None) -> Template:
    """偏好 template_id；若提供 snapshot_rid（且該 record 存在），從 audit.template_snapshot 還原為臨時 Template instance。"""
```

`/match/new?template_snapshot=<rid>` 路徑：
1. 讀 record → 取 `audit.template_snapshot`
2. 用既有 `parse_template(snapshot_dict)` 還原為 Template
3. 暫存於 request-scope（FastAPI Request state）
4. 渲染 `new_match.html` 時下拉預選此模板（label 為「<原 name>（以歷史 audit 還原）」）

**Rationale**：
- audit.template_snapshot 已是完整序列化 schema → parse_template 直接接受
- 不持久化此「臨時模板」（避免污染 `data/templates/`）
- 使用者真要存就走 US3 fork 流程

**Alternatives**：
- (a) 把 snapshot 寫入臨時檔案再讀 — IO 浪費
- (b) 強制使用者 fork 才能用 — 多一步、UX 差

## D6：JS 範圍限制（YAGNI）

**Decision**：純 vanilla JS，**僅 2 個用途**：
1. **clipboard API**：「複製完整 Prompt」「複製 YAML」按鈕
2. **動態增刪行**：屬性表、規則卡、預設對象表 的「+ 加一行」「× 刪此行」

無 framework、無 reactive、無 state management。HTML form 仍是 multipart POST，server 渲染。

**Rationale**：
- vision 架構「無 JS framework」精神延續
- 教訓 7「周邊整合不應動核心」延伸到「不引入新工具鏈」
- 2 個用途用 ~50 行 vanilla JS 即可；無需 alpine.js / htmx

**Alternatives**：
- (a) 引入 htmx — 雖然 vision 提過 htmx，但本 feature 互動量小，純 vanilla 更簡單
- (b) 引入 Alpine.js — 違反 YAGNI

**File**：`src/matcher/web/static/template_form.js`

## 沿用既有依賴

- jinja2：渲染表單與版本歷史頁
- PyYAML：解析 / 序列化模板
- pytest + TestClient：整合測試

**結論**：所有未知已解，可進 Phase 1。

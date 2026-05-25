# Phase 0 — Research：Web UI 直接填名單

無 NEEDS CLARIFICATION。本檔記錄 5 項技術決策。

## D1：UI 表單 → audit 等價的實作策略

**Decision**：把 UI 表單資料**在 Web 層組成 CSV bytes**（in-memory），透過 `tempfile.NamedTemporaryFile` 寫入暫存，呼叫既有 `load_roster_csv(tmp_path, tpl)` 載入，後續走完整既有 pipeline。

**Rationale**：
- **bytewise 等價最直接**：CSV path 已有完整測試驗證、id 自動生成、aliases 對齊等所有邏輯。UI 路徑只是另一個 CSV 來源。
- **核心 0 改動**（FR-010）：不繞過 data_import；不重寫 Roster 組裝邏輯
- 避免「資料來源無關性」教訓 4 再次踩雷
- 對象問題同理：UI 對象段 → 組 `<roster>.targets.yaml` sidecar bytes（與 CSV path 同 sidecar 機制）

**Alternatives**：
- (a) 直接在 Web 層組 `Roster` dataclass — 繞過 data_import 邏輯；要重做 id 生成、aliases 對齊；高風險偏離
- (b) 寫新 `load_roster_from_dict()` 在 core — 動核心，違反 FR-010

## D2：對象段處理（範本無 default_targets）

**Decision**：UI 對象段把表單資料組成 `<roster_stem>.targets.yaml` bytes，與 roster CSV 一起放暫存目錄；既有 `data_import._load_targets()` 會自動找 sidecar。

**Rationale**：
- 沿用既有 sidecar 機制（contracts/csv-format.md）
- 不動 `_load_targets`；不引入新對象載入路徑
- 與「填名單轉 CSV bytes」對稱

**Alternatives**：
- (a) 把對象直接塞 audit.roster_snapshot.targets — 違反 SC-002 bytewise 等價
- (b) 強制範本必須有 default_targets — 違反 US2

## D3：M1/M2 銜接 feature 009 的方式

**Decision**：UI 填名單 + 選 M1/M2 + 範本有 `preferences_schema` → POST `/match/run-from-form` → 後端發現「需填志願」→ 把 UI 填的 roster 轉 CSV bytes（含對象 sidecar 若需）+ base64 → render `/match/preferences` 頁面（feature 009 既有路徑）；hidden inputs 攜帶 `roster_bytes_b64`、`roster_filename`、`template_id`、`mechanism`、`seed`。

**Rationale**：
- **重用 feature 009 整個機制**（4d hidden inputs + 填志願表單 + POST /match/preferences）
- 不在 UI 直接填名單時就接著填志願（避免單頁複雜度爆炸）
- 使用者體驗：跟「上傳 CSV + M1/M2」走的是同條路徑（檔案上傳 path 早已支援）

**Alternatives**：
- (a) 同頁一次填名單 + 志願 — 單頁太多區塊；測試複雜度爆炸
- (b) 新做志願頁專為 UI-filled — 重複 feature 009；違反 YAGNI

## D4：填寫頁的對象 sidecar yaml 結構

**Decision**：UI 填的對象組成符合 `<roster>.targets.yaml` 既有格式：

```yaml
targets:
  - id: C1
    capacity: 3
    attributes:
      name: 三年甲班
      required_subjects: [國文, 數學]  # list_str 已分號解析後成 list
      feature: bilingual
```

**Rationale**：
- 既有格式（specs/003-data-import 已定義）；不發明新格式
- `_load_targets()` 已會解析 list_str（YAML 原生 list）

**Alternatives**：
- (a) 一個整檔包含 roles + targets — 違反 sidecar 慣例
- (b) 對象寫成 CSV — sidecar 慣例是 YAML

## D5：「直接填名單」的入口位置

**Decision**：`/match/new` 同頁三選一（Alpine `x-data="{mode: 'upload'}"`）：
- 預設 `mode='upload'`（不破壞既有路徑）
- radio 切到 `mode='fill'` → 顯示「選範本 + 跳填寫頁」段
- radio 切到 `mode='from-record'` → 連結 `/matches`（不在本 feature 範圍）

填寫頁本身為獨立 URL `/match/new/fill?template_id=X`，避免 `/match/new` 一頁塞兩種 form。

**Rationale**：
- 同頁三選一保留既有 user flow
- 填寫頁獨立 URL：方便 deep-link、書籤
- Alpine state 在 `/match/new` 控制顯隱即可；填寫頁是 server-render

**Alternatives**：
- (a) 三條完全獨立 URL — 入口分散；首頁缺乏統一說明
- (b) 填寫頁也在 `/match/new` — 一頁兩 form 過複雜

## 沿用既有依賴

- Alpine.js + Tailwind Play CDN：已在 feature 011 範本創作頁載入；本 feature 在新樣板套同 CDN
- python-multipart：form upload 沿用
- pytest + TestClient：整合測試

**結論**：所有未知已解，可進 Phase 1。

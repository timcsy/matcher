# Phase 0 — Research：Web UI 動態填志願表單

無 NEEDS CLARIFICATION（spec 已釐清）。本檔記錄 5 項技術決策。

## D1：中介狀態的攜帶方式（hidden inputs vs session vs 暫存檔）

**Decision**：採 **hidden inputs**——填志願頁將「template_id、mechanism、seed、原始 roster bytes（base64）、roster filename」嵌入 HTML form 的 `<input type="hidden">`。

**Rationale**：
- 無需引入 session 中介軟體（YAGNI）；無需引入暫存目錄管理
- 完全 stateless——填志願頁可在不同 process / 重啟後仍可提交（無 session id 失效問題）
- 與既有 Web 層風格一致（純 form + jinja2，無 JS）
- 5MB 上限的 roster 經 base64 後 ~6.7MB；FastAPI 預設表單 max ~16MB 可容（Starlette `MAX_FORM_FILE_SIZE` 預設無限制，僅多部分上傳檔有 limit）

**Alternatives**：
- (a) **Session（cookie / server-side）**——需引入 `starlette.middleware.sessions` 或 redis；違反 YAGNI；session 失效會讓填志願頁突然送不出去
- (b) **暫存到 `data/tmp/<token>.bytes`**——引入過期清理邏輯、檔案 GC、token 衝突；多伺服器無共享儲存時失效
- (c) **第二次 POST 時要求重傳檔**——使用者體驗極差（要再上傳一次同檔）

**風險與緩解**：
- hidden input 含原始 bytes，HTML 變大——對 5MB roster + base64 後 ~6.7MB；單頁 HTML ~7MB；FastAPI render 與瀏覽器接收皆可承受（測試覆蓋）
- 使用者重整頁面 → bytes 重新從 hidden inputs 讀回，不需上傳——與 (c) 比是優勢

## D2：填志願頁的觸發時機與位置

**Decision**：在既有 `POST /match/run` 端點內判斷——讀完 upload bytes + 解析 roster 後，若符合三條件（模板含 `preferences_schema` + 所有 roles 的 preferences 為空 + mechanism ∈ {M1, M2}），**返回 `preferences_form.html`** 而非執行 pipeline。否則維持 008 既有行為。

**Rationale**：
- 不引入新端點分支；使用者體驗連續（同一個 form submit）
- 判斷需要「解析後的 roster」，必須在 data_import 之後；不可能在 client side 判斷
- 後續「填志願頁送出」走新端點 `POST /match/preferences`，因為要區分兩個 form 的不同欄位

**Alternatives**：
- (a) **新增 `GET /match/preferences?...`**——需把 roster bytes 塞到 URL，不可行
- (b) **多步驟向導頁 `/match/wizard/1, /wizard/2...`**——過度抽象、影響既有結構

## D3：填志願頁 POST 後的執行路徑

**Decision**：新增 `POST /match/preferences` 端點——讀 hidden inputs（template_id, mechanism, seed, roster bytes base64, filename）+ 表單志願（`pref_<role_id>_<rank>` 欄位）→ 驗證（同列重複、白名單 target id、至少一人有志願）→ 解碼 bytes 重新跑 data_import → 把表單志願 merge 進 roster.roles 的 preferences → 走既有 pipeline → 寫 record → 重導到結果頁。

**Rationale**：
- 與 `/match/run` 區隔；後者保留純「直接執行」職責，前者專責「攜帶志願執行」
- merge 邏輯：用 `dataclasses.replace(role, preferences=tuple(form_prefs))`；不動 roster 模組
- 重新解 data_import 而非把解析結果塞 hidden（roles 結構複雜、序列化困難）

**Alternatives**：
- (a) 共用 `/match/run` 端點 — 兩種 form 結構不同，會讓 routes 變很複雜
- (b) 把 parsed roster 序列化塞 hidden — roles 結構含 frozen dataclass，無天然 JSON；複雜度高

## D4：表單欄位命名規範

**Decision**：`pref_<role_id>_<rank>`，例：`pref_S01_1=G2`、`pref_S01_2=G3`、`pref_S01_3=`（空白）。後端用 `request.form()` 一次讀全部 + 按 `role_id` 分組。

**Rationale**：
- 命名直觀；無需 JSON / 巢狀 form structure
- FastAPI Form 不支援動態欄位；必須改用 `await request.form()` 拿原始 dict
- `<select name="pref_S01_1">` 在 HTML 中直接可用

**Alternatives**：
- (a) 多選 `<select multiple>` — 失序、無法表達志願順序
- (b) JSON 欄位 — 需 client side JS 組裝，違反「無 JS framework」

## D5：UI 文案的可解釋性處理（教訓 6）

**Decision**：在 `humanize.py` 新增 `target_summary(target: dict) -> str`，回傳「程式組（容量 3 人）」格式。填志願頁的「候選對象段」與下拉選項皆用此函式。

**Rationale**：
- 統一中文呈現邏輯，避免散落樣板
- 易於未來擴充（如顯示更多 attributes）
- 純函式、易單元測試

**Alternatives**：
- (a) 全在 jinja2 模板拼字串 — 重複邏輯；模板難測
- (b) 不顯示 capacity — 失去「使用者看清楚再選」的透明度（違反原則 1+5）

## 沿用既有依賴

- FastAPI（既有）：`Request.form()` 取得動態欄位
- jinja2（既有）：`base64` filter 已內建可用（`{{ value | b64encode }}`，但較少用——直接在 routes 端 encode 後傳入 context 更清晰）
- pytest + TestClient（既有）：多步驟 form flow 整合測試

**結論**：所有未知已解，可進 Phase 1。

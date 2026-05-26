# Tasks — 登入與資源歸屬

**Feature**: 014-auth-ownership
**Branch**: `014-auth-ownership`
**MVP**：Phase 2 + Phase 3（US1 登入＋私有）+ Phase 4（US2 token 連結）—— 兩個 P1 必須一起到位才有「可公開部署」的隱私底線。US3（範本公開）是 P2，可作 v2。

## 任務組織原則

- TDD（Constitution I）：每端點先寫測試（紅）再實作（綠）
- 核心 0 改動（FR-014/SC-006）：所有變更限於 `src/matcher/web/` + `pyproject.toml`
- 無 DB（FR-015）：擁有者/可見性存進既有 JSON/YAML；token 無狀態簽章
- OAuth 測試以 monkeypatch 模擬 callback，不打真 Google

## Phase 1：Setup

- [x] T001 在 `pyproject.toml` 加依賴 `authlib>=1.3`、`itsdangerous>=2.1`；`uv sync` 確認可裝
- [x] T002 定義環境變數讀取（`src/matcher/web/auth.py` 內）：`GOOGLE_CLIENT_ID/SECRET`、`OAUTH_REDIRECT_URI`、`SESSION_SECRET`；缺值時本機給 dev 預設、production 缺 SESSION_SECRET 則啟動報錯
- [x] T003 清空既有開發資料 `data/matches/`、`data/templates/`（FR-017；保留目錄、刪內容），並在 `.gitignore` 確認 `data/` 已忽略

## Phase 2：Foundational（blocking）

**目標**：登入機制 + session + CSRF + token 簽章工具就位，後續 US 才能掛上去。

### Tests（先紅）

- [x] T010 [P] 撰寫 `tests/unit/test_security_token.py`：token 簽章/驗章 round-trip；竄改 token → 驗章失敗；A 角色 token 解出只含 A
- [x] T011 [P] 撰寫 `tests/unit/test_security_csrf.py`：CSRF token 產生、相符通過、不符/缺失被拒
- [x] T012 [P] 撰寫 `tests/integration/test_web_auth_flow.py`：monkeypatch OAuth callback 寫入 session email；未登入訪 `/matches` → 302 `/login`；登出清 session

### 實作（綠）

- [x] T013 建立 `src/matcher/web/security.py`：`sign_role_token(match_id, role_id)` / `verify_role_token(token)`（itsdangerous URLSafeSerializer，salt="role-link"）；`generate_csrf` / `validate_csrf`
- [x] T014 建立 `src/matcher/web/auth.py`：Authlib Google OAuth client；`require_login` 依賴（未登入 302 `/login?next=`）；`current_user(request)`；login/logout/callback 處理函式
- [x] T015 建立 `src/matcher/web/routes/auth.py`：`GET /login`、`GET /auth/login`、`GET /auth/callback`、`POST /logout`
- [x] T016 建立 `src/matcher/web/templates/login.html`：登入頁（用 Google 登入按鈕 + 友善說明）
- [x] T017 修改 `src/matcher/web/app.py`：加 `SessionMiddleware`（secret、https_only、SameSite=Lax）；註冊 auth router；把 `current_user` 注入樣板全域
- [x] T018 修改 `src/matcher/web/templates/base.html`：頁首顯示登入者 email + 登出鈕（未登入顯示登入連結）
- [x] T019 執行 `uv run pytest tests/unit/test_security_token.py tests/unit/test_security_csrf.py tests/integration/test_web_auth_flow.py -q` 確認綠（Phase 2 出口）

**Checkpoint**：能登入/登出、session 運作、token 與 CSRF 工具可用。

---

## Phase 3：User Story 1 — 行政登入後只看到自己的（P1）

**Independent Test**：A 登入建配對 → B 登入 `/matches` 看不到 → B 開 A 的 `/match/{id}` 得 403；未登入訪管理頁導向登入。

### Tests（先紅）

- [x] T020 [P] [US1] 撰寫 `tests/integration/test_web_auth_ownership.py::test_matches_list_only_owner` —— A 建 2 筆、B 建 1 筆 → A 的 `/matches` 只列 2、B 只列 1
- [x] T021 [P] [US1] `::test_cross_user_match_detail_403` —— B 開 A 的 `/match/{id}`、`/audit`、`/report.pdf`、舊個別路徑 → 403
- [x] T022 [P] [US1] `::test_admin_pages_require_login` —— 未登入訪 `/matches`、`/match/new`、`/match/{id}`、`/templates/new` → 302 `/login`
- [x] T023 [P] [US1] `::test_post_requires_csrf` —— `/match/run-from-form` 缺 CSRF token → 403；帶正確 token → 通過

### 實作（綠）

- [x] T024 [US1] 修改 `src/matcher/web/store.py`：`MatchRecord` 加 `owner` 欄位；`MatchStore.list(owner=None)` 支援過濾；存檔寫入 owner
- [x] T025 [US1] 修改 `src/matcher/web/routes/match.py`：`run`、`run_from_form`、`submit_preferences` 建 record 時 `owner=current_user`；加 `require_login`
- [x] T026 [US1] 修改 `src/matcher/web/routes/match.py`：`match_detail`、`download_audit`、`download_report_pdf`、舊個別路徑加 `require_login` + owner 檢查（非 owner 403）
- [x] T027 [US1] 修改 `src/matcher/web/routes/match.py`：`new_match`、`new_match_fill` 加 `require_login`
- [x] T028 [US1] 修改 `src/matcher/web/routes/records.py`：`/matches` 加 `require_login`，`store.list(owner=current_user)`
- [x] T029 [US1] 建立 `src/matcher/web/security.py` 的 CSRF 整合：所有 POST 表單樣板加 hidden `csrf_token`；POST handler 前驗 CSRF（match.py / pages.py 的 POST）
- [x] T030 [US1] 加 403 友善頁（沿用 error_page.html 或新 forbidden 區塊），繁中、無技術碼
- [x] T031 [US1] 執行 `uv run pytest tests/integration/test_web_auth_ownership.py -q` 確認綠

---

## Phase 4：User Story 2 — token 個別連結，免登入（P1）

**Independent Test**：結果頁個別連結為 `/r/{token}`；未登入可開、只顯示該角色；舊路徑匿名被擋；亂猜 token → 404。

### Tests（先紅）

- [x] T040 [P] [US2] 撰寫 `tests/integration/test_web_token_link.py::test_token_link_anonymous_ok` —— 簽一個合法 token，未登入 GET `/r/{token}` → 200 顯示該角色
- [x] T041 [P] [US2] `::test_token_link_only_own_role` —— A 的 token 顯示 A 的資料，不含 B
- [x] T042 [P] [US2] `::test_forged_or_random_token_404` —— 亂字串 / 竄改 token → 404
- [x] T043 [P] [US2] `::test_old_individual_path_blocked_for_anon` —— 未登入 `/match/{id}/role/{rid}` → 302/403（不再匿名可枚舉）
- [x] T044 [P] [US2] `::test_result_page_shows_token_links` —— 結果頁個別連結 href 為 `/r/...`（非 `/match/{id}/role/...`）

### 實作（綠）

- [x] T045 [US2] 新增 `GET /r/{token}` 於 `src/matcher/web/routes/match.py`：驗章 → (match_id, role_id) → 渲染既有 `individual_view.html`；失敗 404
- [x] T046 [US2] 新增 `GET /r/{token}/audit.json`、`GET /r/{token}/report.pdf`：同驗章 → 既有個別下載邏輯
- [x] T047 [US2] 修改 `src/matcher/web/routes/match.py` 結果頁 context：`roles_for_links` 改帶 `sign_role_token(record.id, role_id)` 產生的 token url
- [x] T048 [US2] 修改 `src/matcher/web/templates/match_result.html`：個別連結與複製按鈕改用 `/r/{token}`
- [x] T049 [US2] 舊個別路徑 `/match/{id}/role/{rid}` 確認已在 T026 改 owner-only（匿名擋掉）
- [x] T050 [US2] 執行 `uv run pytest tests/integration/test_web_token_link.py -q` 確認綠

---

## Phase 5：User Story 3 — 範本私有/公開（P2）

**Independent Test**：A 建私有範本 B 看不到；A 設公開後 B 看得到、可複製、不可編輯。

### Tests（先紅）

- [x] T060 [P] [US3] 撰寫 `tests/integration/test_web_template_visibility.py::test_private_template_hidden_from_others`
- [x] T061 [P] [US3] `::test_public_template_visible_and_forkable`
- [x] T062 [P] [US3] `::test_non_owner_cannot_edit_public_template`（→ 403，但可 fork）
- [x] T063 [P] [US3] `::test_builtin_visible_to_all_logged_in`

### 實作（綠）

- [x] T064 [US3] 範本版本 YAML 加 `owner` + `visibility`（`src/matcher/web/routes/pages.py` save 時寫入；預設 private）
- [x] T065 [US3] 範本載入/列表加可見性過濾：`owner==me ∪ public ∪ 內建`（pages.py + TemplateRegistry 包裝層，注意不動核心 template_loader）
- [x] T066 [US3] `/templates/{id}` 詳細頁 + `/edit` + `/save`（既有 id）加 owner 檢查；非 owner 403
- [x] T067 [US3] 範本詳細頁（owner）加「設為公開 / 設為私有」切換（POST + CSRF）
- [x] T068 [US3] 執行 `uv run pytest tests/integration/test_web_template_visibility.py -q` 確認綠

---

## Phase 6：Polish & Cross-cutting

- [x] T070 [P] rate-limit（FR-016）：對 `/auth/*` 與 `/match/run*` 加簡易記憶體限流；若引入 slowapi 記入 plan Complexity Tracking
- [x] T071 [P] 修補既有測試：現有 web 整合測試大量未帶 session → 加 autouse fixture 注入「已登入」session（類似 feature 013 的 conftest 攔截手法），或為各測試補登入步驟
- [x] T072 確認 cookie flags（Secure/HttpOnly/SameSite）於 app.py 設定正確（SC-007）
- [x] T073 執行 quickstart SC-006：`git diff main --name-only -- 'src/matcher/*.py' ':!src/matcher/web' ':!src/matcher/templates'` 為空（核心 0 改動守門）
- [x] T074 執行 `uv run pytest -q` 全綠
- [x] T075 更新 `knowledge/vision.md`：新增階段 6「登入與資源歸屬」完成紀錄 + tech stack 加 authlib/itsdangerous
- [x] T076 評估 `knowledge/experience.md` 是否新增 lesson（如「簽章 token 取代索引檔達成無狀態鑑權」「auth 作為周邊整合維持核心 0 改動」）

---

## 任務統計

| Phase | Tasks | 預估 |
|---|---|---|
| Setup | 3 (T001-T003) | 30 min |
| Foundational | 10 (T010-T019) | 3-4 小時（OAuth + session + 工具）|
| US1 登入＋私有 | 12 (T020-T031) | 3-4 小時 |
| US2 token 連結 | 11 (T040-T050) | 2 小時 |
| US3 範本公開 | 9 (T060-T068) | 2 小時 |
| Polish | 7 (T070-T076) | 2-3 小時（含修補既有測試）|
| **Total** | **52** | **~14 小時** |

## Dependencies

```
Setup (T001-T003)
   ↓
Foundational (T010-T019) ── OAuth/session/CSRF/token 工具
   ↓
US1 (T020-T031) ── 登入守門 + owner 過濾 + CSRF（依賴 Foundational）
   ↓
US2 (T040-T050) ── token 連結（依賴 Foundational 的簽章工具；舊路徑封鎖依賴 US1 的 T026）
   ↓
US3 (T060-T068) ── 範本可見性（依賴 Foundational 登入；獨立於 US2）
   ↓
Polish (T070-T076) ── rate-limit、修補既有測試、knowledge、核心 0 改動守門
```

US2 與 US3 在 US1 後可並行（不同檔/不同關注點）。

## 並行範例

- **Foundational tests**：T010/T011/T012 同時寫
- **US1 tests**：T020/T021/T022/T023 同時寫
- **US2 tests**：T040-T044 同時寫
- **US3 tests**：T060-T063 同時寫

## Implementation Strategy

1. **Setup + Foundational 先做完**（登入跑得起來才有後續）
2. **US1（登入＋私有）= 隱私底線的一半**：管理頁守門 + owner 隔離
3. **US2（token 連結）= 隱私底線的另一半**：修掉枚舉漏洞、保住家長免登入路徑
   - **US1 + US2 合起來才是「可公開部署」的 MVP**
4. **US3（範本公開）**：錦上添花，P2
5. **Polish**：T071（修補既有 352 測試的登入需求）是這個 feature 對既有測試衝擊最大的一項，預留時間
6. 全程盯 T073 核心 0 改動守門

## 對既有測試的衝擊（重要）

加上 `require_login` 後，**現有大量 web 整合測試會 302 失敗**（它們沒登入）。T071 用 conftest autouse fixture 注入已登入 session 是關鍵收尾——預期類似 feature 013 conftest 攔截手法的規模。實作 US1 時就要同步處理，否則中途紅燈會爆量。

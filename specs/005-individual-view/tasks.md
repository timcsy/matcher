---

description: "Task list for 個別查詢視圖（Individual View）"
---

# Tasks: 個別查詢視圖（Individual View）

**Input**: Design documents from `/specs/005-individual-view/`
**Prerequisites**: plan.md ✅、spec.md ✅、research.md ✅、data-model.md ✅、contracts/ ✅、quickstart.md ✅

**Tests**: 包含。Constitution v1.0.0 原則 I（TDD）為不可妥協條款。

**Organization**：依 spec.md 中 P1 / P2 / P3 三條 user story 分組。

## Format: `[ID] [P?] [Story] Description`

- **[P]**：可平行執行（檔案不同、無前置未完成任務）
- **[Story]**：對應的 user story 標籤（US1 / US2 / US3）

---

## Phase 1：Setup

**目的**：本 feature **無新依賴、無新增目錄**；Setup 階段為空（保留 phase 結構）。

（無任務）

---

## Phase 2：Foundational（阻塞所有 user story）

**目的**：兩個純函式（humanize / individual subset）的測試先行 + 實作。

- [x] T001 [P] `tests/unit/test_web_humanize.py`：先紅測試 `humanize_rule_description(description, template)`——(a) `role.X` 替換為「您的 <顯示名>」；(b) `target.Y` 替換為「該對象的 <顯示名>」；(c) 多次匹配同一句中皆替換；(d) 模板無對應 description 時 fallback 用 key；(e) 不含 role./target. token 的字串原樣回傳
- [x] T002 [P] `tests/unit/test_web_individual_subset.py`：先紅測試 `build_individual_audit_subset(audit, role_id)`——(a) role_id 存在 → 回傳含 role_attributes、assignment、filter_trace_subset、allocation_step 的 dict；(b) role 未分配 → assignment.target_id 為 null；(c) filter_trace_subset 條目數 == audit.filter_trace 中該 role 條目數；(d) role_id 不存在 → 拋 `MatchRecordNotFound`
- [x] T003 建立 `src/matcher/web/humanize.py`：實作 `humanize_rule_description(description: str, template: Template) -> str`；以 `re.sub(r"role\.(\w+)", ...)` 與 `r"target\.(\w+)"` 替換；查找顯示名於 `template.attributes.{roles,targets}.description`（依賴 T001）
- [x] T004 [P] 建立 `src/matcher/web/individual.py`：實作 `build_individual_audit_subset(audit: dict, role_id: str) -> dict` 與 `INDIVIDUAL_AUDIT_SCHEMA_VERSION = "individual-audit/1.0"`；role_id 不在 audit.roster_snapshot.roles → 拋 `MatchRecordNotFound`（依賴 T002）

**Checkpoint**：foundational 完成，US 可開始。

---

## Phase 3：User Story 1 — 老師個別查詢頁（P1）🎯 MVP

**Goal**：`GET /match/{record_id}/role/{role_id}` 顯示個別視圖；技術詞零容忍。

**Independent Test**：跑一次 teacher-class 媒合 → 訪問 `/match/<id>/role/T01` → 看到基本資訊 + 分配 + 媒合說明；HTML response 不含任何技術 token。

### 測試（先寫且必須先紅）⚠️

- [x] T005 [P] [US1] `tests/integration/test_web_individual_view.py`（建立檔案，含 US1 相關測試）：(a) 成功媒合 + 已分配的 role → 200 + 含「您被分到」+ 對象顯示名；(b) 成功媒合 + 未分配的 role → 200 + 含「未分配」+ 原因；(c) 技術詞零容忍——response.text 不含 FORBIDDEN_TECHNICAL_TOKENS 任一 + 不匹配 `r"\brole\.\w+"` 或 `r"\btarget\.\w+"`；(d) 規則描述中的 `role.speciality` 顯示為「您的 老師專業科目」

### 實作

- [x] T006 [US1] 在 `src/matcher/web/routes/match.py` 新增 `GET /match/{record_id}/role/{role_id}` 路由：取 record（store.get）、檢查 status / role_id 是否存在（皆 → 404 走 individual_error.html）；構造 context 含 `role_attrs`、`assignment_target_attrs`、`filter_trace_subset`、`allocation_step`、`humanized_rule_lines`；渲染 `individual_view.html`
- [x] T007 [P] [US1] 建立 `src/matcher/web/templates/individual_view.html`：依 contracts/http-endpoints.md 規範；四大段：「您的基本資訊」「您的分配結果」「媒合過程說明」「下載我的稽核紀錄」；所有顯示文字繁中，**完全不含**技術 token；規則描述以 humanized 後的文字呈現
- [x] T008 [P] [US1] 在 `src/matcher/web/app.py` 註冊 humanize Jinja2 filter：`templates.env.filters["humanize_rule"] = humanize_rule_description`（讓 individual_view.html 可呼叫 `{{ rule.description | humanize_rule(template) }}`）

**Checkpoint**：US1 完成。MVP 可獨立驗證——quickstart 第 3 節通過。

---

## Phase 4：User Story 2 — admin 結果頁加「個別查詢連結」（P2）

**Goal**：admin 結果頁列出所有角色的個別查詢 URL。

**Independent Test**：跑一次媒合 → 訪問 `/match/<id>` → 展開「個別查詢連結」`<details>` → 看到 N 列表格（N = 角色數）。

### 測試（先寫且必須先紅）⚠️

- [x] T009 [P] [US2] 在 `tests/integration/test_web_individual_view.py` 新增 US2 測試：(a) 成功媒合的結果頁含「個別查詢連結」字串；(b) 列表中的 URL 數 == 該 record 的角色數；(c) 失敗紀錄的結果頁**不含**「個別查詢連結」字串

### 實作

- [x] T010 [US2] 修改 `src/matcher/web/templates/match_result.html`：在「下載稽核紀錄」按鈕之後、僅在 status=="success" 時，加入 `<details><summary>個別查詢連結（共 N 位）</summary>...</details>` 區段，內含表格（姓名 / role_id / 連結）
- [x] T011 [US2] 修改 `src/matcher/web/routes/match.py` 的 `match_detail` 路由：為成功紀錄附加 `roles` context（從 audit.roster_snapshot.roles 提取 id + name）給樣板使用

**Checkpoint**：US2 完成。SC-004 通過。

---

## Phase 5：User Story 3 — 404 錯誤情境 + 個別 audit 下載（P3）

**Goal**：3 種 404 情境用語友善；個別 audit 子集下載端點正常。

**Independent Test**：3 種錯誤情境分別回 404 + 友善訊息；下載個別 audit 子集 JSON。

### 測試（先寫且必須先紅）⚠️

- [x] T012 [P] [US3] 在 `tests/integration/test_web_individual_view.py` 新增 US3 測試：(a) record 不存在 → 404 + 含「找不到該次媒合的紀錄」；(b) role_id 不在 record → 404 + 含「您不在這次媒合的名單中」；(c) failed 紀錄 → 404 + 含「執行失敗」；(d) 三種錯誤頁皆**不含** error.type 等技術詞
- [x] T013 [P] [US3] `tests/integration/test_web_individual_audit_download.py`：(a) GET /match/<id>/role/T01/audit.json → 200 + Content-Type JSON + attachment header；(b) JSON 含 schema_version "individual-audit/1.0"、role_id、role_attributes、assignment、filter_trace_subset；(c) filter_trace_subset 條目數等於 audit.filter_trace 中該 role 的條目數（SC-006）
- [x] T014 [P] [US3] `tests/integration/test_web_individual_reproducibility.py`：同 record + role_id 訪問兩次 → response.text 完全相同（SC-005）

### 實作

- [x] T015 [P] [US3] 建立 `src/matcher/web/templates/individual_error.html`：依 contracts/http-endpoints.md 三種訊息範例；用語友善、不顯示技術 token、附「請聯絡發送連結的行政人員」建議
- [x] T016 [US3] 在 `src/matcher/web/routes/match.py` 完成 US1 路由中的 404 分支（呼叫 individual_error.html，不重用 admin error_page.html）；訊息選擇依據三種 case
- [x] T017 [US3] 在 `src/matcher/web/routes/match.py` 新增 `GET /match/{record_id}/role/{role_id}/audit.json` 路由：呼叫 `build_individual_audit_subset`，序列化 JSON（`ensure_ascii=False, sort_keys=True, indent=2`）+ 設 `Content-Disposition: attachment; filename="<rid>-<role>.individual.json"`；同樣 404 路徑沿用 US1

**Checkpoint**：US3 完成。SC-003、SC-005、SC-006 通過。

---

## Phase 6：Polish & Cross-Cutting

- [x] T018 [P] `tests/integration/test_web_individual_view.py`：補上跨 US 的整體性測試——(a) 個別查詢頁含「下載我的稽核紀錄」連結；(b) 連結指向 audit.json 端點；(c) 樣板繼承 base.html（含 lang=zh-Hant）
- [x] T019 [P] 更新 `README.md`：在「Web UI」段補上「個別查詢」說明（提及 `/match/<id>/role/<role_id>` URL 結構與行政可下發給當事人）
- [x] T020 [P] 跑 `quickstart.md` 全 8 節，逐項勾選驗證
- [x] T021 [P] 全量回歸：`uv run pytest` 必須全綠（既有 142 + 階段 3b 新增 ≈ 15，總計 ≈ 157）

---

## Dependencies & Execution Order

### Phase 相依

- **Setup (1)**：空
- **Foundational (2)**：純函式 + 先紅測試；阻塞所有 user story
- **US1 (3)**：依賴 Foundational；MVP 核心
- **US2 (4)**：依賴 US1（共用 admin 結果頁）；US2 樣板修改要等 US1 確認 URL 結構
- **US3 (5)**：依賴 US1（共用 routes/match.py 中的 404 邏輯）；可與 US2 平行
- **Polish (6)**：依賴 US1+US2+US3 完成

### Parallel Opportunities

- Foundational：T001 / T002 [P]；T003 / T004 部分平行（T003 依 T001、T004 依 T002）
- US1：T007 / T008 平行於 T006 內路由實作
- US2：T010 / T011 緊鄰但屬不同檔案——可平行
- US3：T015 / T013 / T014 / T012 多個 [P]
- Polish：全 [P]

---

## Implementation Strategy

### MVP First（只到 US1）

1. Phase 2：Foundational
2. Phase 3：US1
3. **STOP & VALIDATE**：跑 quickstart 第 3 + 7 節；驗證 SC-002（技術詞零容忍）

### Incremental Delivery

1. Foundational → 純函式測試先行
2. US1 → 個別查詢頁可獨立使用
3. US2 → admin 連結列表（配套）
4. US3 → 錯誤頁 + audit 下載
5. Polish → README + quickstart 驗證 + 真人實測（SC-001 待安排）

### TDD 嚴格度

- 純函式 T003 / T004 先紅測試（T001 / T002）
- 路由 T006 先紅測試（T005）
- 404 路徑 T016 先紅測試（T012）
- bug 修補先補測試

---

## Notes

- 本 feature 為 read-only 視圖，無資料寫入；測試只需 GET
- 技術詞零容忍（SC-002）為硬要求，T005 與 T012 兩處都驗證
- 既有 142 測試**完全不應**被本 feature 動到——若任一既有測試失敗即表示 admin 結果頁的 `<details>` 區段引入破壞性變更
- **SC-001（5 分鐘真人測試）為人工驗證**，不在本任務清單；feature 完成後安排

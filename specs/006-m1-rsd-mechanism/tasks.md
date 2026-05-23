---

description: "Task list for M1 RSD 分配機制"
---

# Tasks: M1 RSD 分配機制（隨機輪流挑）

**Input**: Design documents from `/specs/006-m1-rsd-mechanism/`
**Prerequisites**: plan.md ✅、spec.md ✅、research.md ✅、data-model.md ✅、contracts/ ✅、quickstart.md ✅

**Tests**: 包含。Constitution v1.0.0 原則 I（TDD）為不可妥協條款。

**Organization**：依 spec.md 中 P1 / P2 / P3 三條 user story 分組。

## Format: `[ID] [P?] [Story] Description`

- **[P]**：可平行執行（檔案不同、無前置未完成任務）
- **[Story]**：對應的 user story 標籤（US1 / US2 / US3）

---

## Phase 1：Setup

**目的**：本 feature **無新依賴、無新目錄**；Setup 階段為空（保留 phase 結構）。

（無任務）

---

## Phase 2：Foundational（阻塞所有 user story）

**目的**：errors 新增、audit schema v1.3 升版、pipeline dispatch 骨架（純函式測試先行）。

- [x] T001 [P] `tests/unit/test_pipeline_dispatch.py`：先紅測試 `run_match` 的 mechanism dispatch——(a) mechanism=M0 + 任一 prefs 非空 → `PreferencesNotSupported`（沿用既有）；(b) mechanism=M1 + 全空 prefs → `M1RequiresPreferences`；(c) mechanism=M1 + 至少一位 prefs 非空 → 正常進入 M1 分支；(d) 不支援的 mechanism 值 → 既有錯誤路徑
- [x] T002 在 `src/matcher/errors.py` 新增 `M1RequiresPreferences`（exit_code = 40），繼承 `MatcherError`
- [x] T003 在 `src/matcher/audit.py` 將 `schema_version` 從 `"1.2"` 改為 `"1.3"`；`build_audit_record` 新增 `processing_order: list[str] | None = None` 參數；輸出含 `processing_order` 欄位（None → null）
- [x] T004 在 `src/matcher/pipeline.py` 的 `MatcherInput` 將 `mechanism` 型別擴為 `Literal["M0", "M1"]`（或保持 `str` 但加 validation）；`run_match` 加 dispatch 邏輯（M0 沿用既有；M1 引入下一階段的 `allocate_m1`，本 task 先寫 dispatch + raise NotImplementedError 待 US1 補完）

**Checkpoint**：foundational 完成；既有 M0 流程在 schema v1.3 下仍可跑（黃金檔會失敗，於 T013 重生修正）。

---

## Phase 3：User Story 1 — M1 RSD 端對端跑通（P1）🎯 MVP

**Goal**：M1 演算法 + CLI --mechanism + 新黃金檔。

**Independent Test**：以 study-group 模板 + 含 preferences 的 CSV + seed 2026 + `--mechanism M1` 跑通；兩次同輸入 bytewise 相同。

### 測試（先寫且必須先紅）⚠️

- [x] T005 [P] [US1] `tests/unit/test_allocator_m1.py`：純函式測試 `allocate_m1`——(a) 處理順序為 Fisher-Yates 洗牌結果（同 seed 同序）；(b) 每位 role 取「合格 ∩ 仍有名額」中第一個志願；(c) 志願全滿時 fallback 抽籤；(d) preferences 去重；(e) preferences 含資格外 id 忽略；(f) 容量耗盡邊界
- [x] T006 [P] [US1] `tests/integration/test_cli_mechanism_m1.py`：(a) `matcher run --template study-group --roster-csv ... --seed 2026 --mechanism M1` 跑通 exit 0；(b) audit 含 `mechanism: "M1"`、`schema_version: "1.3"`、非 null 的 `processing_order`；(c) 兩次同 seed 兩次同輸入 bytewise 相同；(d) preference_rank 為合法值（1-based 或 null）

### 實作

- [x] T007 [US1] 在 `src/matcher/allocator.py` 新增 `allocate_m1(qualified_set, preferences_map, capacities, rng) -> tuple[list[str], dict, list[dict]]`：依 data-model.md「狀態轉移」段實作；含 `normalize_preferences` 內部函式（去重 + 忽略資格外）；fallback 抽籤用 `rng.randrange`
- [x] T008 [US1] 在 `src/matcher/pipeline.py` 完成 dispatch 分支：M1 路徑呼叫 `allocate_m1`，將返回的 `processing_order` 傳給 `build_audit_record`；preference_rank 等資訊已在 allocation_trace 中（由 allocate_m1 構造）
- [x] T009 [US1] 在 `src/matcher/cli.py` 將 `--mechanism` 參數的 `Literal` 擴為 `"M0|M1"`（或保持 str + validation）；保留預設 `"M0"`；CLI summary 在 M1 路徑下印「處理順序」段（依 contracts/cli.md stdout 範例）
- [x] T010 [P] [US1] 建立 `examples/study-group/roster-m1.csv`：以 study-group 模板的 9 位學生 + 每人 1-3 個志願組別（分號分隔）為內容；對應旁檔 `roster-m1.targets.yaml` 可重用既有 `study-group/roster.targets.yaml`（建符號連結或複製）
- [x] T011 [US1] 跑 `matcher run --template study-group --roster-csv examples/study-group/roster-m1.csv --seed 2026 --mechanism M1 --output tests/golden/study-group-m1.audit.json` 產生新黃金檔（依賴 T007、T008、T010）

**Checkpoint**：US1 完成。MVP 可獨立驗證——quickstart 第 1、2 節通過。

---

## Phase 4：User Story 2 — 拒絕邏輯（P2）

**Goal**：M1 + 全空 prefs 明確拒絕；mechanism 值驗證；訊息明確。

**Independent Test**：3 種拒絕情境分別回對應 exit code 與訊息。

### 測試（先寫且必須先紅）⚠️

- [x] T012 [P] [US2] `tests/integration/test_m1_reject.py`：(a) M1 + 既有 study-group/roster.yaml（全空 prefs）→ exit 40 + 訊息含「M1 需要至少一位角色提供志願」與「請改用 --mechanism M0」；(b) `--mechanism M5` → exit 2 + 訊息含「不支援的機制 `M5`」、「支援：M0、M1」；(c) M0 + 任一非空 prefs → 沿用既有 exit 17（向後相容驗證）

### 實作

- [x] T013 [US2] 完善 `src/matcher/cli.py` 與 `src/matcher/pipeline.py` 的拒絕分支：M1 + 全空 prefs 拋 `M1RequiresPreferences`；CLI 對不支援值給明確訊息

**Checkpoint**：US2 完成。SC-003、SC-010 通過。

---

## Phase 5：User Story 3 — 既有 M0 路徑向後相容（P3）

**Goal**：重生 5 個既有黃金檔（schema v1.3 + null 欄位）；既有 169 測試 100% 通過。

**Independent Test**：跑全量測試 100% 綠；黃金檔 diff 僅 schema/null 差異。

### 測試（先寫且必須先紅）⚠️

- [x] T014 [P] [US3] `tests/integration/test_m0_backward_compat.py`：(a) M0 路徑（既有 examples）跑出的 audit `processing_order` 為 null；(b) 每筆 `allocation_trace` 條目的 `preference_rank` / `preferred_order` / `fallback_random_index` 皆為 null；(c) schema_version 為「1.3」

### 實作

- [x] T015 [US3] 重生 5 個既有黃金檔：
  - `tests/golden/teacher-class-baseline.audit.json`（`matcher run --rules ... --roster ... --seed 123456`）
  - `tests/golden/teacher-class-template.audit.json`（`--template teacher-class --roster ...`）
  - `tests/golden/teacher-class-csv.audit.json`（`--template teacher-class --roster-csv ...`）
  - `tests/golden/study-group-template.audit.json`（`--template study-group --roster ...`）
  - `tests/golden/study-group-xlsx.audit.json`（`--template study-group --roster-xlsx ...`）
- [x] T016 [US3] 同步更新既有黃金檔比對測試（`tests/integration/test_reproducibility.py`、`test_backward_compatibility.py`）的 schema_version 期望值：v1.2 → v1.3；若有 audit.json 內容硬編碼，皆改為比對重生後的黃金檔
- [x] T017 [US3] 更新 `tests/unit/test_audit.py` 與 `tests/integration/test_baseline.py` 的 `schema_version` 期望值至 `"1.3"`；補上「`processing_order` 欄位存在且為 null」斷言
- [x] T018 [US3] 更新 `tests/integration/test_template_audit_snapshot.py` 中 `test_audit_schema_version_is_1_2` 改為 `test_audit_schema_version_is_1_3`；同樣更新 `tests/integration/test_template_run.py` 與 `test_backward_compatibility.py`

**Checkpoint**：US3 完成。SC-005、SC-006 通過。

---

## Phase 6：Polish & Cross-Cutting

- [x] T019 [P] 更新 `README.md`：在 Web UI 段之後新增「分配機制」段，含 `--mechanism M0|M1` 用法與 M1 範例
- [x] T020 [P] 跑完整 quickstart.md 第 1-7 節，逐項勾選驗證
- [x] T021 [P] 全量回歸：`uv run pytest` 必須全綠（既有 169 + 階段 4a 新增 ≈ 13 = 182 ±）
- [x] T022 [P] 跨平台確定性驗證（時間允許時）：在 Python 3.11 / 3.12 各跑一次 M1 黃金檔，確認 bytewise 相同（沿用教訓 1）

---

## Dependencies & Execution Order

### Phase 相依

- **Setup (1)**：空
- **Foundational (2)**：errors / schema / dispatch 骨架；阻塞所有 user story
- **US1 (3)**：依賴 Foundational；MVP 核心
- **US2 (4)**：依賴 US1（共用 dispatch 邏輯與訊息）
- **US3 (5)**：依賴 US1（schema v1.3 + processing_order 已產生）
- **Polish (6)**：依賴 US1+US2+US3 完成

### Parallel Opportunities

- Foundational：T001 可平行於 T002（不同檔案）
- US1 測試：T005 / T006 [P]
- US1 範例與實作：T010 平行於 T007/T008/T009
- US2 / US3 可平行進行（不同檔案）
- Polish：全 [P]

---

## Implementation Strategy

### MVP First（只到 US1）

1. Phase 2：Foundational（errors / schema / dispatch 骨架）
2. Phase 3：US1（先寫紅測試 → M1 演算法 → CLI → 範例 CSV → 新黃金檔）
3. **STOP & VALIDATE**：跑 quickstart 第 1、2 節；驗證 SC-001、SC-002

### Incremental Delivery

1. Foundational → schema 與 dispatch 就緒
2. US1 → M1 端對端跑通（CLI-only；Web 不動）
3. US2 → 拒絕邏輯與訊息明確
4. US3 → 既有 5 個黃金檔重生 + 169 測試持續通過
5. Polish → README + quickstart + 跨版本驗證

### TDD 嚴格度

- 純函式 T007 先紅測試 T005
- CLI 整合 T009 先紅測試 T006
- 拒絕邏輯 T013 先紅測試 T012
- 向後相容 T015-T018 先紅測試 T014

---

## Notes

- 本 feature **首次動到核心模組**（`allocator.py`、`pipeline.py`、`audit.py`、`errors.py`、`cli.py` 五個）；Web 層完全不動
- audit schema v1.2→v1.3 是非破壞性升版；5 個既有黃金檔重生但邏輯不變
- 黃金檔重生在 T015 一次性完成；T016-T018 同步更新測試對應的 schema 期望值
- 「處理順序」(`processing_order`) 與「逐位選擇」（allocation_trace）是 M1 可重現性的兩個關鍵紀錄
- M2（feature 007）將沿用同一 dispatch 框架擴充

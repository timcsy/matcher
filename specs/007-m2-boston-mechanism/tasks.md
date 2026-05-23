---

description: "Task list for M2 Boston 分配機制"
---

# Tasks: M2 Boston 分配機制（層級填滿）

**Input**: Design documents from `/specs/007-m2-boston-mechanism/`
**Prerequisites**: plan.md ✅、spec.md ✅、research.md ✅、data-model.md ✅、contracts/ ✅、quickstart.md ✅

**Tests**: 包含。Constitution v1.0.0 原則 I（TDD）為不可妥協條款。

**Organization**：依 spec.md 中 P1 / P2 / P3 三條 user story 分組。

## Format: `[ID] [P?] [Story] Description`

- **[P]**：可平行執行（檔案不同、無前置未完成任務）
- **[Story]**：對應的 user story 標籤（US1 / US2 / US3）

---

## Phase 1：Setup

（無任務；本 feature 無新依賴、無新目錄）

---

## Phase 2：Foundational（阻塞所有 user story）

**目的**：錯誤類別重新命名 + alias、CLI 參數擴充、audit 新欄位骨架。

- [x] T001 [P] `tests/unit/test_errors_alias.py`：先紅測試錯誤類別 alias——(a) `from matcher.errors import M1RequiresPreferences, MechanismRequiresPreferences`；(b) `M1RequiresPreferences is MechanismRequiresPreferences` 或同 class；(c) `isinstance(MechanismRequiresPreferences(...), M1RequiresPreferences)` True；(d) 兩者 `exit_code` 皆為 40
- [x] T002 在 `src/matcher/errors.py` 將 `M1RequiresPreferences` 重新命名為 `MechanismRequiresPreferences`；保留 `M1RequiresPreferences = MechanismRequiresPreferences` alias；exit_code 40 不變
- [x] T003 在 `src/matcher/pipeline.py` 將 import 從 `M1RequiresPreferences` 改為 `MechanismRequiresPreferences`；M1 與 M2 拒絕分支共用同一錯誤類別，訊息依 mechanism 動態填寫
- [x] T004 在 `src/matcher/audit.py` 的 `build_audit_record`：M0/M1 路徑的既有 `allocator.py` 已產 trace 條目；本 task 確保 audit 輸出時若 trace 條目缺 `tie_break_random_index` 欄位 → 補上 null（向後相容墊片）；亦可在 allocator 層補欄位

**Checkpoint**：foundational 完成；既有 M1 / M0 路徑仍可跑（黃金檔 diff 暫時失敗，於 T013 重生）。

---

## Phase 3：User Story 1 — M2 端對端跑通（P1）🎯 MVP

**Goal**：M2 Boston 演算法 + CLI --mechanism M2 + 新黃金檔。

**Independent Test**：以 study-group + roster-m1.csv（複用）+ seed 2026 + `--mechanism M2` 跑通；兩次同輸入 bytewise 相同；audit 含 tie_break_random_index。

### 測試（先寫且必須先紅）⚠️

- [x] T005 [P] [US1] `tests/unit/test_allocator_m2.py`：純函式測試 `allocate_m2`——(a) 層級填滿邏輯（無超額情境，每人都拿到第 1 志願）；(b) 同層超額抽籤（4 人爭 2 個名額時 Fisher-Yates 取前 2，落選下層）；(c) tie_break_random_index 對應洗牌結果位置；(d) fallback 抽籤（所有志願都被擠掉、有非志願 target 仍有名額）；(e) 未分配（無資格 target）trace 也有條目（chosen=null）
- [x] T006 [P] [US1] `tests/integration/test_cli_mechanism_m2.py`：(a) `matcher run --template study-group --roster-csv ... --seed 2026 --mechanism M2` 跑通 exit 0；(b) audit 含 `mechanism: "M2"`、`schema_version: "1.3"`；(c) 兩次同輸入 bytewise 相同；(d) `tie_break_random_index` 在某些 trace 條目為非 null（驗證超額抽籤觸發）；(e) 與新黃金檔 `study-group-m2.audit.json` bytewise 相同

### 實作

- [x] T007 [US1] 在 `src/matcher/allocator.py` 新增 `allocate_m2(qualified_set, preferences_map, capacities, rng, role_order) -> tuple[list[str], dict, list[dict]]`：依 research.md R-001 pseudo code 實作；複用 `_normalize_preferences`；層級迴圈 + 同層 target 字母序處理 + Fisher-Yates 洗牌超額競爭者 + fallback 抽籤；未分配者也加入 trace
- [x] T008 [US1] 修改 `src/matcher/allocator.py` 的 `allocate_m0` 與 `allocate_m1`：每筆 trace 條目新增 `"tie_break_random_index": None`（M0/M1 永遠 null）
- [x] T009 [US1] 在 `src/matcher/pipeline.py` 完成 M2 dispatch 分支：mechanism="M2" → 呼叫 `allocate_m2`；mechanism in ("M1", "M2") 且全空 prefs → 拋 `MechanismRequiresPreferences`，訊息依 mechanism 動態填寫「M1 需要...」或「M2 需要...」
- [x] T010 [US1] 修改 `src/matcher/cli.py`：`--mechanism` 規範化大寫後接受 {M0, M1, M2}；不支援值的訊息更新為「支援：M0、M1、M2」；CLI summary 在 M2 路徑顯示「M2 Boston 層級填滿」與處理順序
- [x] T011 [US1] 跑 `matcher run --template study-group --roster-csv examples/study-group/roster-m1.csv --seed 2026 --mechanism M2 --output tests/golden/study-group-m2.audit.json` 產生新黃金檔（依賴 T007–T010）

**Checkpoint**：US1 完成。MVP 可獨立驗證。

---

## Phase 4：User Story 2 — 機制需要志願的拒絕邏輯（P2）

**Goal**：M1 / M2 + 空 prefs 拒絕；訊息依 mechanism 動態填寫；錯誤類別 alias 維持向後相容。

**Independent Test**：M1 + 空 prefs 與 M2 + 空 prefs 皆 exit 40；訊息分別含「M1 需要」與「M2 需要」。

### 測試（先寫且必須先紅）⚠️

- [x] T012 [P] [US2] `tests/integration/test_m2_reject.py`：(a) M2 + study-group/roster.yaml（全空 prefs）→ exit 40 + 訊息含「M2 需要至少一位角色提供志願」；(b) M1 + 全空 prefs 訊息更新為「M1 需要...」（既有 4a `test_m1_reject.py::test_m1_with_empty_preferences_rejected` 仍通過）；(c) `--mechanism M3` → exit 2 + 訊息含「支援：M0、M1、M2」

### 實作

（拒絕邏輯實作已在 T009 完成；本 phase 主要是測試驗證）

**Checkpoint**：US2 完成。SC-003、SC-006 通過。

---

## Phase 5：User Story 3 — 既有 M0 / M1 路徑向後相容（P3）

**Goal**：重生 6 個既有黃金檔（diff 僅新增 `tie_break_random_index: null`）；既有 188 測試 100% 通過。

**Independent Test**：跑全量測試 100% 綠；6 個既有黃金檔 diff 僅 1 行新增。

### 測試（先寫且必須先紅）⚠️

- [x] T013 [P] [US3] `tests/integration/test_m2_backward_compat.py`：(a) M0 路徑跑出的 audit 每筆 trace 含 `tie_break_random_index: null`；(b) M1 路徑跑出的 audit 同樣含 null；(c) audit schema_version 仍為 `"1.3"`

### 實作

- [x] T014 [US3] 重生 6 個既有黃金檔（一次性）：
  - `tests/golden/teacher-class-baseline.audit.json`
  - `tests/golden/teacher-class-template.audit.json`
  - `tests/golden/teacher-class-csv.audit.json`
  - `tests/golden/study-group-template.audit.json`
  - `tests/golden/study-group-xlsx.audit.json`
  - `tests/golden/study-group-m1.audit.json`
- [x] T015 [US3] 確認既有黃金檔比對測試（`test_reproducibility.py`、`test_backward_compatibility.py`、`test_template_export_import.py` 等）皆通過——schema_version 仍 v1.3、無需動測試斷言

**Checkpoint**：US3 完成。SC-004、SC-005 通過。

---

## Phase 6：Polish & Cross-Cutting

- [x] T016 [P] 更新 `README.md` 的「分配機制」段：補上 `--mechanism M2` 用法與 M2 範例（與 M1 對比）
- [x] T017 [P] 跑完整 quickstart.md 第 1-7 節，逐項勾選驗證
- [x] T018 [P] 全量回歸：`uv run pytest` 必須全綠（既有 188 + 階段 4b 新增 ≈ 12 = 200 ±）
- [x] T019 [P] M1 vs M2 對比驗證（quickstart 第 3 節）：執行兩次跑出 audit、比對 `preference_rank` 分布——M2 通常偏低（多人拿到第 1 志願）

---

## Dependencies & Execution Order

### Phase 相依

- **Setup (1)**：空
- **Foundational (2)**：error rename + audit 欄位墊片；阻塞所有 user story
- **US1 (3)**：依賴 Foundational；MVP 核心
- **US2 (4)**：依賴 US1（共用 dispatch 邏輯與訊息）；主要是測試驗證
- **US3 (5)**：依賴 US1（schema 已含 tie_break_random_index null）
- **Polish (6)**：依賴 US1+US2+US3 完成

### Parallel Opportunities

- Foundational T001 / T002 部分平行；T003 / T004 序列
- US1 測試 T005 / T006 [P]
- US2 / US3 可平行進行（不同檔案）
- Polish 全 [P]

---

## Implementation Strategy

### MVP First（只到 US1）

1. Phase 2：Foundational（error rename + alias + audit 墊片）
2. Phase 3：US1（先紅測試 → M2 演算法 → CLI → 新黃金檔）
3. **STOP & VALIDATE**：跑 quickstart 第 1、2、3 節；驗證 SC-001、SC-002、SC-008（M1 vs M2 對比）

### TDD 嚴格度

- 純函式 T007 先紅測試 T005
- CLI 整合 T010 先紅測試 T006
- 錯誤 alias T002 先紅測試 T001
- 拒絕邏輯 T009 先紅測試 T012

---

## Notes

- 本 feature **第二次合法動核心** 5 個模組（allocator/pipeline/audit/errors/cli）——符合教訓 7 判準
- audit schema **不升版本**（仍 v1.3）；僅新增可選欄位 tie_break_random_index
- 6 個既有黃金檔重生：diff 應僅 1 行新增 `"tie_break_random_index": null`
- 錯誤類別 alias 維持向後相容；既有測試 0 改動

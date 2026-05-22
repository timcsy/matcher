---

description: "Task list for 核心媒合引擎（library + CLI）"
---

# Tasks: 核心媒合引擎（library + CLI）

**Input**: Design documents from `/specs/001-core-allocator/`
**Prerequisites**: plan.md ✅、spec.md ✅、research.md ✅、data-model.md ✅、contracts/ ✅、quickstart.md ✅

**Tests**: 包含。Constitution v1.0.0 原則 I（TDD）為不可妥協條款——每個實作任務之前必須先有對應的失敗測試。

**Organization**：依 spec.md 中 P1 / P2 / P3 三條 user story 分組。

## Format: `[ID] [P?] [Story] Description`

- **[P]**：可平行執行（檔案不同、無前置未完成任務）
- **[Story]**：對應的 user story 標籤（US1 / US2 / US3）
- 路徑皆為相對於 repo 根目錄的絕對結構（依 plan.md「Project Structure」）

---

## Phase 1：Setup（共用基礎）

**目的**：專案骨架與工具鏈初始化。

- [x] T001 建立 Python 套件骨架：在 repo 根目錄建立 `pyproject.toml`、`src/matcher/__init__.py`、`tests/{unit,integration,golden,fixtures}/__init__.py`、`examples/teacher-class/`、`README.md` 雛形
- [x] T002 [P] 在 `pyproject.toml` 宣告依賴：`typer`、`pyyaml`、`pytest`；宣告 console script `matcher = "matcher.cli:app"`；指定 `requires-python = ">=3.11"`
- [x] T003 [P] 設定測試與格式化工具：建立 `pytest.ini`（指向 `tests/`）；設定 ruff/black（可在 `pyproject.toml` 中宣告）

---

## Phase 2：Foundational（阻塞所有 user story）

**目的**：所有 user story 共用的底層型別與工具。

**⚠️ CRITICAL**：本階段未完成前，任何 user story 不可開始。

- [x] T004 建立 `src/matcher/errors.py`：定義 8 個明確錯誤類別 `QualifiedSetEmpty`、`CapacityShortage`、`RuleContradiction`、`EmptyRoster`、`DuplicateIdentity`、`UnknownAttribute`、`SeedMissing`、`PreferencesNotSupported`，每個皆繼承自共同基底 `MatcherError`
- [x] T005 [P] 建立 `src/matcher/rules.py` 的資料模型：dataclass `Eq`、`In`、`Ge`、`Le`、`RoleInTargetField`、`And`、`Or`、`Not`、`Rule`、`Ruleset`（**只放結構，求值器在 US1 階段才寫**）
- [x] T006 [P] 建立 `src/matcher/roster.py` 的資料模型：dataclass `Role`、`Target`、`Roster`；含 `capacity ≥ 1` 的型別層級保證
- [x] T007 [P] 建立 `src/matcher/rng.py`：`SeededRandom` 類別包裝 `random.Random(seed)`，僅暴露 `randrange(n)`；提供 `fisher_yates_shuffle(items, rng)` 顯式洗牌函式
- [x] T008 建立 `src/matcher/io_yaml.py`：`load_ruleset(path)` 與 `load_roster(path)`，使用 `yaml.safe_load`；輸入解析期執行 data-model.md「驗證規則」表中的所有檢查（`EmptyRoster`、`DuplicateIdentity`、`UnknownAttribute`），依賴 T004 + T005 + T006

**Checkpoint**：基礎模組就緒，可進入 user story 實作。

---

## Phase 3：User Story 1 — 完成一次可重現的純抽籤媒合（P1）🎯 MVP

**Goal**：給定規則檔、名單檔、seed → 產出資格集合、最終配對、可重現的稽核紀錄。

**Independent Test**：執行 quickstart.md 的「1. 執行基準場景」與「2. 驗證可重現性」兩步，兩次 `audit.json` 逐位元組相同。

### 測試（先寫且必須先紅）⚠️

- [x] T009 [P] [US1] `tests/unit/test_rules.py`：覆蓋 9 種 AST 節點的求值正確性（含 cross-side `role_in_target_field`、邏輯組合）
- [x] T010 [P] [US1] `tests/unit/test_filter.py`：給定小型 ruleset 與 roster，驗證 `filter()` 產出的 `QualifiedSet` 與 `filter_trace` 內容正確
- [x] T011 [P] [US1] `tests/unit/test_allocator.py`：驗證 `allocate_m0()` 輸出的 `assignment` 必定滿足「每個 (role, target) 對皆在 qualified_set 內」、「對象容量不超出」
- [x] T012 [P] [US1] `tests/unit/test_rng.py`：相同 seed 兩次 `fisher_yates_shuffle` 結果相同；不同 seed 結果不同；只使用 `randrange` 不呼叫 `shuffle`/`sample`/`choices`
- [x] T013 [P] [US1] `tests/unit/test_audit.py`：`AuditRecord` 組裝後序列化（`json.dumps(..., ensure_ascii=False, sort_keys=True, indent=2)`）符合 `contracts/audit-schema.json`
- [x] T014 [P] [US1] `tests/integration/test_baseline.py`：以 Typer `CliRunner` 執行基準場景 `matcher run`，驗證 exit code 0、stdout 含「完成」與「稽核紀錄已寫入」、`audit.json` 通過 schema 驗證
- [x] T015 [P] [US1] `tests/integration/test_reproducibility.py`：基準場景連跑兩次 → 兩個 `audit.json` 逐位元組相同（SC-001）；亦對 `tests/golden/teacher-class-baseline.audit.json` 黃金檔比對

### 實作

- [x] T016 [US1] 在 `src/matcher/rules.py` 補上規則求值器：`evaluate(expr, role, target) -> bool`、`matched_rules(ruleset, role, target) -> list[Rule]`（依賴 T005、T009 已紅）
- [x] T017 [US1] 建立 `src/matcher/filter.py`：`filter(ruleset, roster) -> tuple[QualifiedSet, list[FilterTraceEntry]]`；對每個 `(role, target)` 求值，無資格時記錄首條 `failed_rule`；若 `QualifiedSet` 為空 → 拋 `QualifiedSetEmpty`（依賴 T016）
- [x] T018 [P] [US1] 建立 `src/matcher/allocator.py`：`allocate_m0(qualified_set, capacities, rng) -> tuple[Assignment, list[AllocationTraceEntry]]`；以顯式 Fisher–Yates 取 `randrange(len(candidates))`；每步記錄 `step / role_id / candidates / random_index / chosen / remaining_capacity_after`（依賴 T007）
- [x] T019 [US1] 建立 `src/matcher/audit.py`：`build_audit_record(...)` 組裝 `AuditRecord`；`dump_audit_json(record, path)` 以 `ensure_ascii=False, sort_keys=True, indent=2` 寫檔；`generated_at` 固定為 `None`
- [x] T020 [US1] 建立 `src/matcher/pipeline.py`：`run_match(MatcherInput) -> MatcherResult` 串接 validate → filter → capacity check → allocate → audit；本階段 capacity check：若 `len(roles) > sum(target.capacity)` → 拋 `CapacityShortage`（依賴 T017、T018、T019）
- [x] T021 [US1] 建立 `src/matcher/cli.py`：Typer app，實作 `matcher run` 命令；參數依 `contracts/cli.md`；成功時印出繁中可讀摘要；尚未做完整錯誤映射（US2 才補完）（依賴 T020）
- [x] T022 [P] [US1] 建立 `examples/teacher-class/rules.yaml`：10 條左右規則覆蓋 `role_in_target_field`、`ge`、`in`、邏輯組合；每條附繁中 `description`
- [x] T023 [P] [US1] 建立 `examples/teacher-class/roster.yaml`：10 位老師、5 個班級、每班 capacity 2（對應 SC-002 場景）
- [x] T024 [US1] 跑一次基準場景產生 `audit.json` → 人工審視內容正確後另存為 `tests/golden/teacher-class-baseline.audit.json`；同時複製到 `examples/teacher-class/expected.audit.json`（依賴 T021、T022、T023）

**Checkpoint**：US1 完成。MVP 可獨立驗證——quickstart.md 第 1、2 節皆通過。

---

## Phase 4：User Story 2 — 邊界情境的明確錯誤回應（P2）

**Goal**：七種異常輸入皆產生明確繁中錯誤訊息與對應 exit code，不靜默通過。

**Independent Test**：執行 `tests/integration/test_edge_cases.py`，七種情境各自得到預期 exit code 與訊息。

### 測試（先寫且必須先紅）⚠️

- [x] T025 [P] [US2] `tests/integration/test_edge_cases.py`：覆蓋全部七種邊界情境（資格集合為空、容量不足、規則互斥、名單為空、名單有重複身分、規則引用未定義屬性、seed 未提供）；每案斷言 exit code 與訊息中關鍵字
- [x] T026 [P] [US2] `tests/fixtures/edge_cases/` 下建立七份 YAML fixture：`empty_qualified.{rules,roster}.yaml`、`capacity_shortage.{rules,roster}.yaml`、`rule_contradiction.rules.yaml`、`empty_roster.yaml`、`duplicate_identity.roster.yaml`、`unknown_attribute.rules.yaml`、（seed 缺漏為 CLI 行為，不需 fixture）

### 實作

- [x] T027 [US2] 在 `src/matcher/rules.py` 補上規則互斥偵測：對每條規則的 AST 做局部不可滿足檢查（如同一 `And` 中同時含 `Eq(f,v)` 與 `Not(Eq(f,v))`）→ 載入期即拋 `RuleContradiction`（依賴 T016）
- [x] T028 [US2] 在 `src/matcher/pipeline.py` 補上 `CapacityShortage` 預檢：在 `allocate_m0` 之前比對「角色數」與「資格集合內可達容量總和」（依賴 T020）
- [x] T029 [US2] 在 `src/matcher/cli.py` 完成全部 8 種 Exception → exit code 映射（依 `contracts/cli.md` 表格）；每種錯誤輸出**錯誤行 + 細節行 + 建議行**三段繁中訊息（依賴 T021、T004）

**Checkpoint**：US2 完成。SC-003、SC-004 皆通過。

---

## Phase 5：User Story 3 — 為未來機制保留介面（P3）

**Goal**：介面接受 preferences；非空 preferences 在 M0 機制下被明確拒絕。

**Independent Test**：執行 `tests/integration/test_preferences_rejection.py`，提供非空 preferences 時得到 exit code 17 與對應提示。

### 測試（先寫且必須先紅）⚠️

- [x] T030 [P] [US3] `tests/integration/test_preferences_rejection.py`：(a) 提供非空 preferences → exit 17 + 訊息含「M0 純抽籤」「不接受志願輸入」「階段 4」；(b) 提供空 preferences 檔（空 dict） → 正常通過；(c) 不提供 `--preferences` → 正常通過

### 實作

- [x] T031 [US3] 在 `src/matcher/pipeline.py` 加入 preferences 檢查：當 `preferences` 為非 None 且非空時拋 `PreferencesNotSupported`（依賴 T020）
- [x] T032 [US3] 在 `src/matcher/cli.py` 加入 `--preferences <path>` 參數與其 YAML 載入；空 dict / None 對應正確；`PreferencesNotSupported` 對應 exit 17 與「建議：移除 `--preferences` 參數，或等待後續版本」訊息（依賴 T021、T029、T031）

**Checkpoint**：US3 完成。SC-006 通過。

---

## Phase 6：Polish & Cross-Cutting

- [x] T033 [P] 在 `src/matcher/cli.py` 補上 `matcher filter` 子命令（只跑過濾、不需 seed），對應 `contracts/cli.md`「matcher filter」段與 FR-005
- [x] T034 [P] 補 `tests/integration/test_filter_subcommand.py`：覆蓋 `matcher filter` 的成功路徑與相關錯誤 exit codes（10/12/14/15/16）
- [x] T035 [P] 撰寫 `README.md`（repo 根目錄）：含「快速開始」「安裝」「執行基準場景」三節，繁中
- [x] T036 [P] 跑完整 quickstart.md 步驟 1–6，逐項勾選驗證
- [x] T037 [P] 跨版本確定性驗證：在 Python 3.11 與 3.12 下各跑基準場景，`diff` 兩份 `audit.json` 必須為空（對應 SC-001 與 plan.md Constraints）
- [x] T038 [P] 基準場景效能驗證：以 `time` 量測基準場景執行時間 < 5 秒（SC-002）；若超出則於 `experience.md` 記錄落差

---

## Dependencies & Execution Order

### Phase 相依

- **Setup (1)**：無前置，可立即開始
- **Foundational (2)**：依賴 Setup；**阻塞所有 user story**
- **US1 (3)**：依賴 Foundational
- **US2 (4)**：依賴 US1（共用 pipeline / cli 檔案）
- **US3 (5)**：依賴 US1；可與 US2 平行（不同檔案區段）
- **Polish (6)**：依賴 US1（部分項目可在 US2/US3 完成後）

### User Story 相依

- **US1 (P1)**：完成 Foundational 後可開始，無 story 間相依
- **US2 (P2)**：擴充 cli.py 的錯誤映射與 pipeline 的預檢；建議 US1 完成後再啟動
- **US3 (P3)**：在 cli.py 加新參數與 pipeline 加檢查；可與 US2 平行（但同檔案 `cli.py` 需協調順序）

### Within Each User Story

- 測試必須**先寫且先紅**（依 constitution 原則 I）
- AST／資料模型 → 求值器／組裝器 → pipeline → CLI
- 例範（examples/）可平行於核心實作

### Parallel Opportunities

- T002 / T003（Setup）可平行
- T005 / T006 / T007（Foundational 中三個獨立模型/工具）可平行
- US1 內所有測試 T009–T015 皆可平行
- T018（allocator）與 T016（rules 求值器）可平行（不同檔案、不互依）
- T022 / T023（examples）與核心實作平行
- US2 / US3 部分項目可平行

---

## Parallel Example：User Story 1 測試一次啟動

```bash
# 在啟動實作前，一次寫完所有 US1 測試（會全部紅）：
Task: "tests/unit/test_rules.py"
Task: "tests/unit/test_filter.py"
Task: "tests/unit/test_allocator.py"
Task: "tests/unit/test_rng.py"
Task: "tests/unit/test_audit.py"
Task: "tests/integration/test_baseline.py"
Task: "tests/integration/test_reproducibility.py"
```

---

## Implementation Strategy

### MVP First（只到 US1）

1. Phase 1：Setup
2. Phase 2：Foundational
3. Phase 3：US1（含先紅測試 → 實作 → 黃金檔）
4. **STOP & VALIDATE**：跑 quickstart.md 第 1、2 節；驗證 SC-001、SC-002
5. 即可作為 demo 或內部評審

### Incremental Delivery

1. Setup + Foundational → 基底就緒
2. US1 → MVP（可重現純抽籤）
3. US2 → 邊界錯誤的稽核級體驗
4. US3 → 介面契約完整
5. Polish → 跨版本驗證、README、效能驗證

### TDD 嚴格度

- 每個實作任務開工前，對應的測試必須存在且**確認失敗**
- 不允許「先寫實作再補測試」；若發現實作前測試已意外通過，視為測試覆蓋不足，須補強
- bug 修補：必先新增重現該 bug 的失敗測試，再修復（constitution 原則 I）

---

## Notes

- [P] 任務 = 不同檔案、無未完成相依
- [Story] 標籤 = 任務歸屬的 user story
- 每個 user story 自身可獨立完成與測試
- 測試必須**先紅後綠**
- 每完成一個任務或邏輯群組即 commit（commit 主旨英文、說明段繁中）
- 任一 checkpoint 皆可暫停以驗證故事完整性
- 避免：模糊任務、同檔同步衝突、跨 story 的硬相依

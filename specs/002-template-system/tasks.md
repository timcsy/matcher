---

description: "Task list for 模板系統（Template System）"
---

# Tasks: 模板系統（Template System）

**Input**: Design documents from `/specs/002-template-system/`
**Prerequisites**: plan.md ✅、spec.md ✅、research.md ✅、data-model.md ✅、contracts/ ✅、quickstart.md ✅

**Tests**: 包含。Constitution v1.0.0 原則 I（TDD）為不可妥協條款；每個實作任務之前必須先有對應的失敗測試。

**Organization**：依 spec.md 中 P1 / P2 / P3 三條 user story 分組。

## Format: `[ID] [P?] [Story] Description`

- **[P]**：可平行執行（檔案不同、無前置未完成任務）
- **[Story]**：對應的 user story 標籤（US1 / US2 / US3）
- 路徑皆為相對於 repo 根目錄的絕對結構（依 plan.md「Project Structure」）

---

## Phase 1：Setup

**目的**：模板資源目錄與套件設定。

- [x] T001 建立內建模板目錄：`src/matcher/templates/__init__.py`、`src/matcher/templates/builtin/__init__.py`（空檔，作為 importlib.resources 可定位的子套件）

---

## Phase 2：Foundational（阻塞所有 user story）

**目的**：所有 user story 共用的型別、錯誤類別、資料模型擴充。

**⚠️ CRITICAL**：本階段未完成前，任何 user story 不可開始。

- [x] T002 在 `src/matcher/errors.py` 新增 4 個錯誤類別：`TemplateNotFound`（exit 20）、`UnknownSchemaVersion`（exit 21）、`TemplateMissingField`（exit 22）、`TemplateConflict`（exit 23），皆繼承自 `MatcherError`
- [x] T003 [P] 建立 `src/matcher/template.py`：dataclass `Template`、`AttributeSchema`、`AttributeDecl`、`UIFieldDecl`、`ReportFieldDecl`、`PreferencesSchema`（依 data-model.md 欄位）。本檔僅放結構；解析器留給 T006
- [x] T004 [P] 擴充 `src/matcher/roster.py` 的 `Role` dataclass，新增 `preferences: tuple[str, ...] = ()`；`parse_roster` 讀取每位 role 下的選填 `preferences` 欄位（型別需為 list[str]，其他型別 → 既有錯誤路徑）
- [x] T005 [P] 在 `src/matcher/io_yaml.py` 新增 `load_template(path) -> Template`：使用 `yaml.safe_load`，呼叫 T006 的 parse_template

**Checkpoint**：基礎型別與錯誤類別就緒。

- [x] T006 建立 `src/matcher/template_loader.py`：`parse_template(data: dict) -> Template`（含 schema_version 驗證、必填欄位檢查、ui_fields/report_fields/preferences_schema 結構驗證）；`TemplateRegistry` 類別（`list_ids()`、`get(id)`、`has(id)`）透過 `importlib.resources.files("matcher.templates.builtin")` 列舉 `*.yaml`（依賴 T002 + T003）

**Checkpoint**：基礎模組就緒，可進入 user story 實作。

---

## Phase 3：User Story 1 — 使用內建模板執行媒合（P1）🎯 MVP

**Goal**：給定內建模板 id 與名單，能跑出完整媒合與含 `template_snapshot` 的稽核紀錄。

**Independent Test**：`matcher run --template teacher-class --roster examples/teacher-class/roster.yaml --seed 123456` 跑通；稽核紀錄通過 audit-schema-v1.1 驗證；給定相同輸入兩次結果逐位元組相同。

### 測試（先寫且必須先紅）⚠️

- [x] T007 [P] [US1] `tests/unit/test_template.py`：覆蓋 Template / AttributeDecl / UIFieldDecl / ReportFieldDecl / PreferencesSchema 的結構正確性、`parse_template` 對合法 YAML 的解析、必填欄位檢查（測試會驗證 `TemplateMissingField`）
- [x] T008 [P] [US1] `tests/unit/test_template_loader.py`：`TemplateRegistry.list_ids()` 至少回傳 `["teacher-class", "study-group"]`；`get(id)` 載入內建模板回傳 Template；`get("no-such")` 拋 `TemplateNotFound`；未知 schema_version 拋 `UnknownSchemaVersion`
- [x] T009 [P] [US1] `tests/integration/test_template_run.py`：以 `CliRunner` 執行 `matcher run --template teacher-class --roster ... --seed ...`；驗證 exit 0、stdout 含「=== 模板 ===」、audit JSON 通過 v1.1 schema、`template_snapshot.id == "teacher-class"`
- [x] T010 [P] [US1] `tests/integration/test_template_audit_snapshot.py`：使用模板執行兩次相同輸入 → 兩份 audit 逐位元組相同；audit 中 `template_snapshot` 為完整 Template 序列化（含所有欄位）

### 實作

- [x] T011 [US1] 建立 `src/matcher/templates/builtin/teacher-class.yaml`：以階段 1 的 `examples/teacher-class/rules.yaml` 為基礎，補上 `schema_version: "1.0"`、`id`、`name`、`description`、`attributes`（roles/targets 完整 schema 宣告）、`ui_fields`、`report_fields`；保留階段 1 的 R001/R002/R003 規則（依賴 T006）
- [x] T012 [P] [US1] 建立 `src/matcher/templates/builtin/study-group.yaml`：宣告 `preferences_schema: { max_choices: 3, required: false, description: "..." }`；attributes/rules 對應「學生→分組」場景；`ui_fields` 含 grade、preferences 等欄位（依賴 T006）
- [x] T013 [P] [US1] 建立 `examples/study-group/roster.yaml`：≥ 8 位學生、3 個分組（每組 capacity 3）、每位學生 `preferences: []`（空陣列）作為 M0 場景
- [x] T014 [US1] 修改 `src/matcher/audit.py`：`build_audit_record(...)` 新增選填參數 `template: Template | None`；輸出 `schema_version: "1.1"`、新增 `template_snapshot` 欄位（無 template 時為 `null`，有時為完整序列化）
- [x] T015 [US1] 修改 `src/matcher/pipeline.py`：`MatcherInput` 加 `template: Template | None = None`；`run_match` 在有 template 時從 `template.ruleset` 取規則並將 template 傳入 audit；保留無 template 時的原行為（依賴 T014）
- [x] T016 [US1] 修改 `src/matcher/cli.py` 的 `run_cmd`：新增 `--template <id>` 與 `--template-file <path>` 參數；三組參數互斥檢查（template id / template file / rules+roster）；template id 透過 `TemplateRegistry.get` 載入；template file 透過 `load_template` 載入；傳入 `MatcherInput.template`（依賴 T015、T006、T005）
- [x] T017 [US1] 重新生成 `tests/golden/teacher-class-baseline.audit.json`：跑 `matcher run --rules ... --roster ... --seed 123456 --output tests/golden/teacher-class-baseline.audit.json`，新檔含 `schema_version: "1.1"` 與 `template_snapshot: null`（依賴 T014）

**Checkpoint**：US1 完成。MVP 可獨立驗證——quickstart.md 第 1、3 節皆通過。

---

## Phase 4：User Story 2 — 模板可瀏覽、匯出、匯入（P2）

**Goal**：CLI 三個子命令 list / show / export 可運作；export 後重新 import 行為一致（逐位元組相同）。

**Independent Test**：執行 quickstart.md 第 1、2、4 節，list 看到兩個模板、show 顯示完整內容、export 後再 `--template-file` 跑出的 audit 與內建模板路徑跑出的 audit 逐位元組相同。

### 測試（先寫且必須先紅）⚠️

- [x] T018 [P] [US2] `tests/integration/test_template_cli.py`：`matcher template list` 輸出含「teacher-class」「study-group」與繁中名稱／描述；`matcher template show teacher-class` 輸出含 attributes、rules、ui_fields 段；`matcher template show no-such` exit 20 + 列出可用 id；`matcher template export teacher-class --output <path>` 寫出 YAML 檔
- [x] T019 [P] [US2] `tests/integration/test_template_export_import.py`：對 teacher-class 與 study-group 各做一次 export；以 `--template-file` 載入跑同 seed → 與直接 `--template <id>` 跑的 audit 逐位元組相同（SC-003）

### 實作

- [x] T020 [US2] 在 `src/matcher/cli.py` 建立 Typer 子應用 `template_app`，包含 `list` / `show` / `export` 三子命令；於主 `app` 以 `app.add_typer(template_app, name="template")` 註冊；`show` 支援 `--format text|yaml|json`（依賴 T006）
- [x] T021 [US2] 在 `src/matcher/template_loader.py` 新增 `dump_template_yaml(template, path)`：以 `yaml.safe_dump(..., allow_unicode=True, sort_keys=False)` 寫出，保持頂層欄位順序（schema_version → id → name → description → attributes → rules → ui_fields → report_fields → preferences_schema）以確保匯出/匯入冪等

**Checkpoint**：US2 完成。SC-001、SC-003 通過。

---

## Phase 5：User Story 3 — 預留 preferences schema 並於 M0 拒絕（P3）

**Goal**：使用 study-group 模板搭配「含 preferences 的名單」時，M0 機制下系統拒絕且訊息明確。

**Independent Test**：執行 `matcher run --template study-group --roster examples/study-group/roster-with-preferences.yaml --seed 1` → exit 17。

### 測試（先寫且必須先紅）⚠️

- [x] T022 [P] [US3] `tests/integration/test_template_preferences_reject.py`：(a) `roster-with-preferences.yaml`（部分學生 preferences 非空）+ study-group 模板 → exit 17、訊息含「M0 純抽籤」「階段 4」；(b) `roster.yaml`（所有人 preferences 為空陣列）+ study-group → exit 0、正常跑通

### 實作

- [x] T023 [US3] 在 `src/matcher/pipeline.py` 加入 preferences 檢查：若 mechanism=M0 且 roster 中**任一位**角色的 `role.preferences` 非空 → 拋 `PreferencesNotSupported`（沿用既有訊息）；先於 `--preferences` 旗標的檢查（避免兩條路徑訊息差異）
- [x] T024 [P] [US3] 建立 `examples/study-group/roster-with-preferences.yaml`：在 T013 的 roster 基礎上，為 ≥ 3 位學生填上 `preferences: [G1, G2, G3]`（其餘留空陣列）

**Checkpoint**：US3 完成。SC-006 通過。

---

## Phase 6：Polish & Cross-Cutting

- [x] T025 [P] `tests/integration/test_backward_compatibility.py`：以階段 1 既有的 `examples/teacher-class/rules.yaml + roster.yaml` 路徑跑 `matcher run`；驗證 exit 0、audit `schema_version: "1.1"`、`template_snapshot: null`；確認 stdout 與階段 1 一致（容許僅版本欄位差異）
- [x] T026 [P] `tests/integration/test_mutex_args.py`：覆蓋三組參數互斥的所有違反組合（同時 --template + --rules；同時 --template + --template-file；同時三組）→ 各自 exit 2 並提示「請擇一」
- [x] T027 [P] 建立 `tests/golden/teacher-class-template.audit.json` 與 `tests/golden/study-group-template.audit.json`：分別以 `--template teacher-class` 與 `--template study-group` 跑出後保存；對應整合測試做黃金檔比對（依賴 T011、T012、T013）
- [x] T028 [P] 更新 `README.md`：新增「模板系統」段，含 `matcher template list/show/export` 範例與 `--template`、`--template-file` 用法
- [x] T029 [P] 跑完整 quickstart.md 七節，逐項勾選驗證
- [x] T030 [P] 階段 1 自動化測試回歸驗證：`uv run pytest tests/unit tests/integration` 全部通過（含階段 1 既有 48 + 階段 2 新增 ≈ 25 個測試）

---

## Dependencies & Execution Order

### Phase 相依

- **Setup (1)**：無前置
- **Foundational (2)**：依賴 Setup；阻塞所有 user story
- **US1 (3)**：依賴 Foundational；MVP 核心
- **US2 (4)**：依賴 US1（共用 Template / TemplateRegistry / cli.py）
- **US3 (5)**：依賴 US1；可與 US2 平行（不同檔案區段）
- **Polish (6)**：依賴 US1（部分項目可在 US2/US3 完成後）

### User Story 相依

- **US1 (P1)**：完成 Foundational 後立即可開始
- **US2 (P2)**：依賴 US1 完成 Template/Registry/cli.py 的基礎注入
- **US3 (P3)**：依賴 US1（pipeline.py + roster.py 已擴充）；可與 US2 平行

### Within Each User Story

- 測試必須**先寫且先紅**（依 constitution 原則 I）
- 資料模型 → 載入器 → pipeline → cli → 黃金檔

### Parallel Opportunities

- T003 / T004（不同檔案的型別擴充）可平行
- US1 內所有測試 T007–T010 可平行
- T012 / T013（不同檔案的範例與內建模板）可平行
- US2 / US3 主體可平行（不同檔案區段）
- Polish 階段大多可平行

---

## Parallel Example：User Story 1 測試一次啟動

```bash
# 在啟動實作前，一次寫完所有 US1 測試（會全部紅）：
Task: "tests/unit/test_template.py"
Task: "tests/unit/test_template_loader.py"
Task: "tests/integration/test_template_run.py"
Task: "tests/integration/test_template_audit_snapshot.py"
```

---

## Implementation Strategy

### MVP First（只到 US1）

1. Phase 1：Setup
2. Phase 2：Foundational
3. Phase 3：US1（先紅測試 → 實作 → 黃金檔重生成 → 既有 48 測試仍通過）
4. **STOP & VALIDATE**：跑 quickstart.md 第 1、3 節；驗證 SC-002、SC-004、SC-007

### Incremental Delivery

1. Setup + Foundational → 基底就緒
2. US1 → MVP（使用內建模板執行媒合 + audit_snapshot）
3. US2 → 模板瀏覽/匯出/匯入完整體驗
4. US3 → preferences 預留拒絕的契約穩定性
5. Polish → backward-compat、mutex、quickstart 驗證、效能

### TDD 嚴格度

- 每個實作任務開工前，對應的測試必須存在且**確認失敗**
- 修補 bug 必先新增重現該 bug 的失敗測試
- audit schema 升級（v1.0 → v1.1）會破壞階段 1 黃金檔——T017 與測試更新必須同步進行

---

## Notes

- [P] 任務 = 不同檔案、無未完成相依
- [Story] 標籤 = 任務歸屬的 user story
- 每個 user story 自身可獨立完成與測試
- 測試必須**先紅後綠**
- 每完成一個任務或邏輯群組即 commit（commit 主旨英文、說明段繁中）
- 任一 checkpoint 皆可暫停以驗證故事完整性
- 避免：跨 story 的硬相依、無聲修改既有黃金檔、引入新第三方依賴（簡潔優先）

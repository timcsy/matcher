# Feature Specification: 移除 default_targets 概念

**Feature Branch**: `013-remove-default-targets`
**Created**: 2026-05-25
**Status**: Draft
**Input**: 使用者明確要求「我不要有預設對象清單」——範本不應內嵌對象資料；對象一律在配對時提供。

## Background / 動機

目前 `Template` dataclass 允許範本內嵌 `default_targets`（如 teacher-class 內建 5 個班級）。這設計有兩個問題：

1. **黑箱**：使用者在 UI 填名單頁看不到對象，不知道會被分到哪些班、總共幾個位置。違反專案核心原則「公平公開」。
2. **混淆模板與資料**：模板應該定義「規則與欄位結構」，對象資料屬於「這一次配對的素材」。把對象綁在模板上讓「換對象」變成「改範本」（要新版本、要審核），降低靈活度。

Feature 011 已從「範本創作 UI」移除了 default_targets 編輯介面（基於同樣理由），本 feature 把概念從 data model 與內建範本也徹底移除。

## User Scenarios & Testing

### User Story 1 - 配對時看見對象（Priority: P1）

身為配對執行者，我用任何範本配對時都能在 UI 看到對象清單（不論是現場填，還是從旁檔載入），不會有「對象從哪冒出來的」疑惑。

**Why this priority**：這是使用者直接表達的訴求，也是「公平公開」原則的具體展現。沒有這個 P1 等於本 feature 沒做。

**Independent Test**：以內建 teacher-class 範本進入 `/match/new/fill`，預期看到「② 對象清單」段，且至少有空白列可填；填完 5 老師 + 3 班級 → M0 跑通 → audit 含這 3 班。

**Acceptance Scenarios**：

1. **Given** 任何內建範本，**When** 進入 `/match/new/fill?template_id=<id>`，**Then** 一定看到對象清單段
2. **Given** UI 填了 5 老師 + 3 班級 + seed 2026 + M0，**When** 提交 `/match/run-from-form`，**Then** 跑通且 `audit.roster_snapshot.targets` 含這 3 班
3. **Given** CLI 路徑 `matcher run --template teacher-class --roster-csv roster.csv`，**When** 同目錄沒有 `roster.targets.yaml`，**Then** 顯示明確錯誤訊息（不再 fallback 到內建對象）

---

### User Story 2 - CLI 旁檔機制保持可用（Priority: P1）

身為 CLI 使用者，我提供 `roster.csv` 加 `roster.targets.yaml` 旁檔仍可跑配對，不受本次重構影響。

**Why this priority**：CLI 是另一條主要使用路徑，重構不能單方面斷掉。

**Independent Test**：用 `examples/teacher-class/roster.csv` + 新建的 `examples/teacher-class/roster.targets.yaml`，`matcher run` 跑通且 audit 與 feature 012 之前的版本（含 default_targets fallback）內容等價（modulo template_snapshot.default_targets 欄位移除）。

**Acceptance Scenarios**：

1. **Given** roster.csv + roster.targets.yaml 同目錄，**When** `matcher run --template teacher-class --roster-csv roster.csv --seed 2026`，**Then** 成功；assignment、qualified_set 與舊版（含 fallback）等價
2. **Given** roster.csv 但缺 .targets.yaml，**When** 同上命令，**Then** 退出碼非零；錯誤訊息明確指出「缺少 .targets.yaml」並建議建立旁檔

---

### User Story 3 - audit schema 升版相容（Priority: P2）

身為下游審查者，我載入升版後的 audit JSON 仍能解析「這次跑用了哪些對象」（從 `roster_snapshot.targets` 讀，而不是從 `template_snapshot.default_targets` 讀）。

**Why this priority**：audit 是公開審計憑證，schema 變動需要明確標記版本以利長期保存的紀錄可被識別。

**Independent Test**：執行配對 → audit JSON 的 `schema_version` 為 `"1.4"`；`template_snapshot` 區段不含 `default_targets` 鍵；`roster_snapshot.targets` 完整列出本次對象。

**Acceptance Scenarios**：

1. **Given** 任何成功的配對紀錄，**When** 讀取 `audit.schema_version`，**Then** 值為 `"1.4"`
2. **Given** 任何 audit JSON，**When** 掃描 `template_snapshot` 鍵，**Then** 不含 `default_targets` 子鍵
3. **Given** 任何 audit JSON，**When** 讀取 `roster_snapshot.targets`，**Then** 為本次配對的對象列表（id、capacity、attributes）

---

### Edge Cases

- **內建範本仍包含 default_targets 欄位**（升版前留下）→ template_loader 解析時忽略（不報錯），但發 warning（或在發布前已從 yaml 移除）
- **舊 audit JSON（v1.3）** → 不主動轉換；只承諾新跑的配對寫 v1.4。舊紀錄 viewer 仍能讀（template_snapshot.default_targets 若存在會被忽略）
- **CLI 缺旁檔錯誤訊息**：必須明確、可操作（含建議檔名）
- **Web 上傳 CSV 但沒附 .targets.yaml**：HTTP 400 並提示「請改用『直接填名單』或附旁檔」
- **examples/ 目錄** 必須提供新 `.targets.yaml`，否則 README 範例斷掉

## Requirements

### Functional Requirements

- **FR-001**：`Template` dataclass MUST 不含 `default_targets` 欄位
- **FR-002**：`template_loader.parse_template` MUST 不再產生 `default_targets`；若 YAML 內仍有此鍵，安靜忽略（不報錯，便於漸進遷移）
- **FR-003**：`template_loader.dump_template` MUST 不再輸出 `default_targets` 鍵
- **FR-004**：`data_import._load_targets` MUST 一律要求 sidecar `<stem>.targets.yaml`；缺則丟 `RosterColumnMismatch` 或新錯誤類別，訊息明確指引使用者
- **FR-005**：內建範本 teacher-class.yaml / study-group.yaml MUST 移除 `default_targets` 區段
- **FR-006**：examples/teacher-class/ 與 examples/study-group/ MUST 包含對應的 `roster.targets.yaml` 旁檔
- **FR-007**：audit schema_version MUST 升至 `"1.4"`；`build_audit` MUST 不再寫 `template_snapshot.default_targets`
- **FR-008**：Web `/match/new/fill` 頁面 MUST 永遠顯示對象清單段（移除 `requires_targets` 條件分支）
- **FR-009**：Web `/match/run`（CSV 上傳路徑）收到沒附 .targets.yaml 的 CSV MUST 回 400 並提示
- **FR-010**：所有既有測試 MUST 通過（必要時補 sidecar fixture）

### Key Entities

- **Template**：拿掉 `default_targets` 欄位，其餘不變
- **audit.template_snapshot**：拿掉 `default_targets` 子鍵
- **examples/<name>/roster.targets.yaml**：新增的旁檔範例

## Success Criteria

### Measurable Outcomes

- **SC-001**：全測試套件（含現有 342 + 新增）100% 綠
- **SC-002**：teacher-class / study-group 範本 yaml 不含 `default_targets:` 字串
- **SC-003**：任何 v1.4 audit JSON 的 `template_snapshot` 鍵集不含 `default_targets`
- **SC-004**：UI `/match/new/fill?template_id=teacher-class` HTML 含「對象清單」段（非條件性隱藏）
- **SC-005**：CLI `matcher run --template teacher-class --roster-csv x.csv` 不附旁檔時退出碼非零且訊息含「targets.yaml」

## Assumptions

- 舊 v1.3 audit JSON 不需要遷移工具（read-only viewer 仍可讀；新跑的才寫 v1.4）
- examples/*/roster.csv 維持原樣（只是補上旁檔，不動 CSV）
- 範本創作 UI 已不允許輸入 default_targets（feature 011 已完成），所以保存層只需確認不寫此鍵
- 移除過程中 `template.default_targets` 屬性讀取會中斷舊代碼 — 必須一次性把所有 `tpl.default_targets` 引用點清掉

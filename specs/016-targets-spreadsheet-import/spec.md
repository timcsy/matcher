# Feature Specification: 對象名單也用試算表匯入

**Feature Branch**: `016-targets-spreadsheet-import`
**Created**: 2026-05-26
**Status**: Draft
**Input**: 使用者：「角色跟對象各是一個試算表，我是說匯入的部分。」目前上傳只收角色名單（CSV/Excel），對象要靠 `.targets.yaml` 旁檔——但一般行政不會寫 YAML。希望能上傳兩個獨立試算表（一個角色、一個對象）。

## Background / 動機

feature 013 移除 default_targets 後，對象一律在配對時提供。Web 上傳路徑目前：
- 角色名單：CSV/Excel（友善）
- 對象：`.targets.yaml` 旁檔（**YAML，一般主任不會寫**）

這讓「我有兩份 Excel（老師一份、班級一份）」這個最自然的情況做不到——使用者得手動把班級轉成 YAML。「直接填名單」可繞過，但人多時還是想用既有的 Excel。

本 feature 讓**對象名單也能用 CSV/Excel 試算表匯入**：上傳兩個獨立檔，一個角色、一個對象，完全不必碰 YAML。

## User Scenarios & Testing

### User Story 1 - 上傳兩個試算表完成配對（Priority: P1）

身為學校行政，我手上有兩份試算表——一份老師、一份班級——我各自上傳，系統就能配對，不必把任何一份轉成 YAML。

**Why this priority**：這是本 feature 的核心；少了它，非技術使用者仍被 YAML 卡住。

**Independent Test**：teacher-class，上傳 roster.csv（老師）+ targets.csv（班級，欄位含 id/capacity/班級名稱/需要科目/特色）→ 配對成功，audit.roster_snapshot.targets 含上傳的班級。

**Acceptance Scenarios**：

1. **Given** 角色 CSV + 對象 CSV，**When** 兩個都上傳並執行，**Then** 配對成功，對象來自上傳的對象檔
2. **Given** 角色 Excel + 對象 Excel，**When** 上傳，**Then** 同樣成功（兩種格式皆可，且可混搭）
3. **Given** 對象檔的欄位用中文表頭（如「班級名稱」「需要科目」），**When** 上傳，**Then** 依範本對象屬性的顯示名稱自動對齊（同角色匯入的別名機制）
4. **Given** 對象檔的「容量」欄，**When** 解析，**Then** 正確讀為整數；多筆欄位（如需要科目）用分號/頓號分隔

---

### User Story 2 - 依範本動態產生的範例試算表（Priority: P1）

身為使用者（用內建或自己建的範本），我能下載「依這個範本動態產生的範例試算表」——表頭就是這個範本要填的欄位（中文），我照著填我的資料即可，不用猜格式。

**Why this priority**：沒有範例，使用者不知道試算表的欄位長怎樣（呼應先前「範本好像沒有對象」的困惑）。動態產生比靜態檔更好：**任何範本（含自訂）都有對應範例，且永遠與範本欄位同步、不會走鐘**。與 US1 同等重要。

**定位（重要）**：動態範例的目的是「**告訴你這個範本要填哪些欄、什麼格式**」，**不保證**「原樣上傳就配對成功」（任意自訂範本的規則無法自動湊出合格示範值）。範例提供正確表頭 + 一列型別/格式提示。

**Independent Test**：對 teacher-class 與某自訂範本，各下載「角色範例」「對象範例」→ 表頭欄位 == 該範本宣告的屬性（中文顯示名稱）+ 編號/容量；對象範例含「型別提示」列（如數字欄標示、多筆欄標示分隔符）。

**Acceptance Scenarios**：

1. **Given** 任一範本（內建或自訂），**When** 下載其角色/對象範例，**Then** 表頭為該範本對應屬性的中文顯示名稱（角色含編號；對象含編號、容量）
2. **Given** 範例檔，**When** 打開，**Then** 有一列「提示列」說明每欄格式（數字／文字／多筆用分號隔開）
3. **Given** 上傳頁，**When** 檢視，**Then** 角色與對象各有 CSV / Excel 範例下載連結，且連結對應「目前選的範本」
4. **Given** 自訂範本新增了一個對象屬性，**When** 重新下載對象範例，**Then** 範例表頭自動含新欄（與範本同步）

---

### User Story 3 - 對象檔編號可省略、自動產生（Priority: P2）

身為使用者，對象試算表若沒有「編號」欄，系統自動編號（T001…），與 UI 填名單一致。

**Why this priority**：降低門檻，但非核心；列 P2。

**Independent Test**：對象 CSV 無 id 欄 → 載入後對象自動取得 id；audit 可見。

**Acceptance Scenarios**：

1. **Given** 對象檔無 id 欄，**When** 匯入，**Then** 自動產生唯一 id
2. **Given** 對象檔有 id 欄，**When** 匯入，**Then** 使用該 id

---

### Edge Cases

- **只上傳角色、沒上傳對象**：維持現狀錯誤訊息「請提供對象」（且提示可用對象試算表或直接填）
- **對象檔缺「容量」欄**：明確錯誤訊息指出缺容量
- **同時提供對象試算表與 .targets.yaml 旁檔**：以上傳的對象試算表為準（或明確擇一；plan 決定）
- **CLI 路徑**：本 feature 聚焦 Web 上傳；CLI 既有 `.targets.yaml` 旁檔機制維持不變（向後相容）
- **編碼**：對象 CSV 沿用角色 CSV 的編碼偵測（UTF-8 / BOM / CP950）

## Requirements

### Functional Requirements

- **FR-001**：系統 MUST 能從 CSV 載入對象名單（id 選填、capacity、+ 範本宣告的對象屬性欄）
- **FR-002**：系統 MUST 能從 Excel（.xlsx）載入對象名單
- **FR-003**：對象檔表頭 MUST 支援中文顯示名稱對齊（沿用角色匯入的別名/description 機制）
- **FR-004**：對象檔型別 MUST 正確轉換（capacity→int、list_str 多筆分隔、str 原樣）
- **FR-005**：對象檔 id 欄 MUST 可省略，省略時自動產生唯一 id
- **FR-006**：Web 上傳頁 MUST 提供兩個檔案欄位：角色名單、對象名單（皆 CSV/Excel）
- **FR-007**：兩檔皆提供時 MUST 完成配對；缺對象時 MUST 給友善錯誤（提示可上傳對象試算表或改用直接填名單）
- **FR-008**：CLI 既有 `.targets.yaml` 旁檔路徑 MUST 維持可用（向後相容）
- **FR-009**：對象試算表匯入的結果 MUST 與「同資料用 .targets.yaml 提供」產生等價的 audit（對象內容一致）
- **FR-010**：MUST 能依「任一範本（內建或自訂）」動態產生角色與對象的範例試算表（CSV 與 Excel），表頭為該範本對應屬性的中文顯示名稱（角色含編號；對象含編號、容量）
- **FR-011**：範例 MUST 含一列「格式提示」，依屬性型別標示（數字／文字／多筆用分號隔開）
- **FR-012**：Web 上傳頁 MUST 提供「角色範例」「對象範例」下載連結（CSV / Excel），且對應目前選定的範本
- **FR-013**：範例由 app 端點動態產生（不依賴外部 repo 的靜態檔）；範本欄位變更後範例自動同步

### Key Entities

- **對象試算表（CSV/Excel）**：表頭含 id（選填）、容量、對象屬性各欄；每列一個對象
- **對象載入器**：解析對象試算表 → targets tuple（與 `_load_targets` 從 YAML 得到的結構一致）

## Success Criteria

### Measurable Outcomes

- **SC-001**：上傳「角色 CSV + 對象 CSV」可配對成功，不需任何 YAML
- **SC-002**：對象 Excel 亦可；CSV/Excel 可混搭
- **SC-003**：對象檔中文表頭自動對齊範本對象屬性
- **SC-004**：對象檔無 id 欄 → 自動編號
- **SC-005**：對象試算表匯入 vs 同資料 YAML 旁檔 → audit 對象等價
- **SC-006**：CLI `.targets.yaml` 旁檔路徑仍正常（既有測試綠）
- **SC-007**：全測試（現有 395 + 新增）綠
- **SC-008**：對任一範本（含自訂）可下載角色/對象範例；表頭 == 該範本屬性的中文顯示名稱（+ 編號/容量）
- **SC-009**：範例含格式提示列；自訂範本加欄後重新下載，範例表頭同步含新欄

## Assumptions

- 本 feature 聚焦 Web 上傳「兩個獨立檔」；CLI 暫不加 `--targets-csv`（可後續延伸，核心函式預留）
- 對象載入器屬「資料匯入」核心職責的擴充（教訓 7）；放在 `src/matcher/data_import.py`
- 「容量」為對象必要欄（一個對象要有容量才有意義）；缺容量該列報錯或忽略，由 plan 決定
- 對象試算表與 .targets.yaml 同時出現時的優先序，由 plan 釐清（傾向：上傳試算表優先）
- audit schema 不變（對象載入後結構與既有相同）
- 範例**動態產生**（不放靜態檔）：app 端點依範本 schema 即時組出 CSV/Excel；好處是涵蓋自訂範本、永遠與範本同步
- 動態範例**只保證欄位/格式正確**，不保證「原樣上傳即成功」（規則合格值無法對任意範本自動產生）；要「能跑的完整示範資料」仍可另用既有 `examples/` 內建範本資料
- 既有上傳頁的角色範例連結（指向 GitHub raw 的 examples）可一併改為動態端點，統一來源

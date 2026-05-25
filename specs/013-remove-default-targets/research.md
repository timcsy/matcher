# Research — 移除 default_targets

Spec 已無 NEEDS CLARIFICATION，本檔記錄重要技術決策。

## D1：parse_template 對舊 YAML 的相容策略

**Decision**：parse 時若 YAML 含 `default_targets:` 鍵 → **靜默忽略**（不警告、不報錯）。

**Rationale**：
- 使用者本機可能還有舊版自訂範本 YAML（含 default_targets）
- 報錯會讓他們所有舊範本一夜無法載入；發 warning 又會污染 CLI/log
- 默默忽略最低摩擦；反正 dump 時不會再寫出來 → 自然衰減

**Alternatives**：
- ❌ 報錯：摩擦太大，違反「使用者本地檔案不該因升版而失效」
- ❌ Warning：除非寫入 log 系統否則使用者也看不到，徒增噪音

## D2：sidecar 缺檔的錯誤類別

**Decision**：沿用既有 `RosterColumnMismatch` 例外，**不新增類別**。訊息文字升級：

```
找不到對象（targets）來源：旁檔 {sidecar.name} 不存在。
細節：CSV/Excel 路徑下，targets 須由旁檔提供（同目錄、檔名 <stem>.targets.yaml）。
建議：建立 {sidecar.name}，或改用 Web UI 的「直接填名單」功能。
```

**Rationale**：
- YAGNI：新類別會迫使所有 except 處增加分支
- `RosterColumnMismatch` 語意涵蓋「roster 結構不完整」，targets 缺也算其中
- CLI 與 Web 的錯誤處理都已能顯示其 message，足夠

**Alternatives**：
- ❌ 新增 `TargetsSidecarMissing`：違反 YAGNI；無人會單獨 catch 它
- ❌ 把訊息塞進 generic Exception：失去結構化的好處

## D3：audit schema_version 從 v1.3 升 v1.4

**Decision**：本 feature 升版 `"1.3"` → `"1.4"`，**單一變動**：移除 `template_snapshot.default_targets`。

**Rationale**：
- 公開審計憑證的契約變動必須以版本明示
- 採 minor 版號（不是 v2.0）— 移除「現在已無實質用途」的選用欄位，read-only viewer 不受影響
- 沒有遷移工具（Assumption：舊 v1.3 紀錄 read-only viewer 仍可讀，因 viewer 不要求該欄存在）

**Alternatives**：
- ❌ 不升版（仍 v1.3）：違反契約透明原則，下游無法區分
- ❌ 升 v2.0：暗示破壞性變動 — 但 reader 不會壞（只是該欄消失），實際是 minor

## D4：examples/*/roster.targets.yaml 內容來源

**Decision**：把現行 `teacher-class.yaml` 的 `default_targets:` 區段抽出，原樣寫到 `examples/teacher-class/roster.targets.yaml`；`study-group.yaml` 同理。

**Rationale**：
- 內容已存在且測過；不需重寫
- 讓既有 CLI 使用者執行 `matcher run --template teacher-class --roster-csv examples/teacher-class/roster.csv` 行為與升版前完全一致（因為自動載入 sidecar）
- README 範例不破壞

**Format**：

```yaml
# examples/teacher-class/roster.targets.yaml
targets:
  - id: C01
    capacity: 2
    attributes:
      name: "三年甲班"
      required_subjects: ["國文", "數學"]
      feature: "bilingual"
  # ... (其餘 4 班同理)
```

## D5：UI fill 頁面條件分支處理

**Decision**：移除 `requires_targets` 樣板變數與 `{% if requires_targets %}` 條件，對象段永遠顯示。

**Rationale**：
- 既然 default_targets 概念消失，「無對象需求」的場景也消失
- 樣板少一個分支 → 認知負擔降低
- routes/match.py 中 `requires_targets=not tpl.default_targets` 計算可刪

**注意**：roster_form.py::assemble_targets_yaml_bytes 不再需要 `if template.default_targets: return None` 分支；改為「未填任何對象 → 回 None」（呼叫方依此判斷 400）

## D6：feature 012 既有測試的回歸風險

**Decision**：feature 012 的 `test_web_roster_fill_targets.py` 中
`test_fill_page_hides_targets_section_when_default_targets_exists` 將反過來——對象段不再會隱藏。

**Rationale**：
- 這個測試本來就是 default_targets 機制存在的副產物
- 應改寫為 `test_fill_page_always_shows_targets_section`，斷言對象段永遠顯示
- 不刪測試 — 改名後仍是 UI 契約守門員

**Alternatives**：
- ❌ 直接刪測試：失去 UI 契約守護
- ❌ 維持 default_targets 但隱藏 UI：偽裝沒拔，混淆未來讀者

## D7：所有 builtin/custom 範本是否需要對應 examples sidecar？

**Decision**：只為 `teacher-class` 與 `study-group` 補 examples sidecar（兩個內建範本對應的 examples 目錄）。自訂範本由使用者自理。

**Rationale**：
- 內建範本對應 examples 是專案的「開箱即用」承諾
- 自訂範本本來就要使用者自己準備對象資料；不額外提供範例

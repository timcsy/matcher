# Tasks: role → participant 全面更名

## Phase 1：核心 python（US1）
- [ ] T001 roster.py：`Role→Participant`、`Roster.roles→.participants`、相關訊息
- [ ] T002 rules.py：DSL 前綴 `role.→participant.`、`role_field`、`role_in_target_field`、錯誤訊息
- [ ] T003 filter.py / allocator.py / pipeline.py：trace 欄位 `role_id→participant_id`、`role_attrs`、`role_order` 等
- [ ] T004 audit.py：`roster_snapshot.roles→participants`、`role_id→participant_id`；`schema_version 1.4→1.5`
- [ ] T005 data_import.py / template.py / template_loader.py：屬性 `roles→participants`、id 生成、規則前綴
- [ ] T006 errors.py / cli.py / cli_report.py：訊息與參數

## Phase 2：範本 / fixtures / docs（US2）
- [ ] T007 內建 teacher-class、study-group：`attributes.roles→participants`、規則 `role.→participant.`
- [ ] T008 tests/fixtures/**：`role.→participant.`、`roles→participants`
- [ ] T009 docs/template-authoring-guide.md：DSL 與範例同步

## Phase 3：web 層 + URL（US1+US3）
- [ ] T010 routes/match*.py、pages.py：識別碼、URL `/role/→/participant/`、token helper 名
- [ ] T011 individual / humanize / pdf / roster_form / template_form / example_gen：識別碼、example 檔名 `roles→participants`
- [ ] T012 樣板 *.html：表單欄位 `role_*→participant_*`、`/role/` 連結、Jinja 變數
- [ ] T013 static/template_form.js：`roleAttrs`、`role_attr_` 欄位名、`addRoleAttr`

## Phase 4：測試
- [ ] T014 tests/**：識別碼與斷言雙替換；schema 版本 `1.4→1.5`
- [ ] T015 backward-compat 測試逐一檢視（無向後相容 → 調整/移除讀舊版案例）

## Phase 5：golden + 驗證
- [ ] T016 重生全部 7 個 golden（依各測試產生路徑）
- [ ] T017 全套件綠；同 seed bytewise 可重現；server smoke；grep 確認 src 無殘留 subject 側 role

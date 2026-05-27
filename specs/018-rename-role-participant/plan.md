# Implementation Plan: role → participant 全面更名

**Branch**: `018-rename-role-participant` | **Spec**: ./spec.md

## 技術脈絡

- 沿用既有技術棧（Python 3.11、FastAPI、Jinja2、Alpine/CDN、pytest、uv）；**無新增依賴**。
- 變更性質：資料模型／schema 演進 + 全層識別碼更名（教訓 9 → 獨立 feature）。
- 安全替換前提（已驗證）：`role` 與 `roster` 無共用子字串；樣板無 ARIA `role=`；
  python 無 `control`/`parole` 類假陽性。故可用**大小寫感知雙替換** `Role→Participant`、`role→participant`。

## 替換邊界

| 改 | 不改 |
|---|---|
| `Role`→`Participant`、`role*`→`participant*`（識別碼、欄位、參數） | `Roster`/`roster` 容器與 `load_roster_*` 函式名（只改其 `.roles`→`.participants` 欄位） |
| audit 鍵 `roster_snapshot.roles→participants`、`allocation_trace[].role_id→participant_id`；schema `1.4→1.5` | `roster_snapshot` 這個鍵本身（含 roster 非 role） |
| 範本 DSL `role.`→`participant.`（parser + 內建範本 + docs + fixtures） | 對象側 `target`、`target.`（不動） |
| URL `/match/{id}/role/{role_id}`→`/participant/{participant_id}` | `/r/{token}`（路徑無 role 字樣，不變） |
| 表單欄位 `role_attr_*`/`role_*`→`participant_*`（樣板＋JS＋python 解析三方同步） | specs/** 歷史 |

## 階段

1. **核心 python**：roster / rules（DSL）/ filter / allocator / pipeline / audit / data_import / template / template_loader / errors / cli / cli_report — 雙替換 + audit schema 升 1.5。
2. **內建範本 YAML + fixtures + docs**：`attributes.roles→participants`、`role.→participant.`。
3. **web 層**：routes（含 URL）、individual / humanize / pdf / roster_form / template_form / example_gen、樣板、template_form.js — 雙替換（URL 與表單欄位三方一致）。
4. **測試**：雙替換識別碼與斷言；schema 版本斷言 `1.4→1.5`；重新評估 backward-compat 測試（無向後相容 → 調整/移除）。
5. **重生 7 個 golden**：依各測試的產生路徑跑出新輸出覆蓋。
6. **驗證**：全套件綠、同 seed bytewise 可重現、server smoke、grep 確認 src 無殘留 subject 側 `role`。

## 風險與對策

- **backward-compat 測試**（test_*_backward_compat、test_backward_compatibility）：原本驗「舊版 audit 仍可讀／升版保核心欄位」。無向後相容後，改為驗「新 schema 1.5 內部自洽」或移除「讀舊版」案例。逐一檢視。
- **golden 比對風格不一**（部分 segment、部分全檔）：一律以新鮮輸出覆蓋整檔（對兩種比對皆安全）。
- **可重現性**（原則 2）：rename 不影響決定性；重生後同 seed 兩跑須 bytewise 相同（保留既有 repro 測試）。

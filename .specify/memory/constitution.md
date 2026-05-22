<!--
Sync Impact Report
==================
Version change: (template) → 1.0.0
Modified principles: 初次制定，無前版
Added sections:
  - Core Principles (I. 測試先行 TDD、II. 規格優先、III. 繁體中文文件、IV. 簡潔優先、V. 可觀測性)
  - 額外約束 (Additional Constraints)
  - 開發流程 (Development Workflow)
  - Governance
Removed sections: 無
Templates requiring updates:
  - ✅ .specify/templates/plan-template.md（既有 Constitution Check 區塊保持通用，無需修改）
  - ✅ .specify/templates/spec-template.md（未引用具名原則，無需修改）
  - ✅ .specify/templates/tasks-template.md（未引用具名原則，無需修改）
Follow-up TODOs:
  - TODO(RATIFICATION_DATE): 採用建立日 2026-05-22 作為批准日；若實際團隊批准日不同請更新。
-->

# Matcher Constitution

## Core Principles

### I. 測試先行（TDD）— 不可妥協

所有實作 MUST 遵循 TDD 紅綠重構循環：先撰寫會失敗的測試 → 由使用者或審查者確認測試正確反映需求 →
執行測試確認其失敗（Red）→ 撰寫最少程式碼使測試通過（Green）→ 在保持測試通過下重構（Refactor）。
任何 PR 中若有新增或修改的行為，MUST 附帶對應的新測試或更新測試；先寫實作再補測試的提交方式
NOT permitted。修補既有 bug 時，MUST 先新增一個重現該 bug 的失敗測試，再進行修復。

理由：本專案以 matcher 的正確性為核心，行為錯誤的代價遠高於開發速度；TDD 強制將需求外顯為可執行
規格，避免回歸並讓重構安全。

### II. 規格優先（Spec-First）

任何新功能 MUST 先透過 spec-kit 流程產出規格（spec）→ 計畫（plan）→ 任務（tasks），再進入實作。
規格描述「為什麼」與「做什麼」，不描述「怎麼做」；實作細節歸 plan/tasks。未經規格化的功能
NOT permitted 合併到主幹，除非屬於純粹的修補（typo、文件、相依性升級）。

理由：規格是團隊與未來自己的契約，避免實作偏離意圖，亦讓 TDD 的測試有明確依據。

### III. 繁體中文文件

所有規格文件（spec、plan、tasks、constitution、設計筆記、PR 說明、commit 訊息中之說明段）
MUST 使用繁體中文撰寫。技術術語、程式碼識別字、API 名稱、檔名與指令保留原文。註解若用於說明
「為什麼」時 SHOULD 使用繁體中文；註解內容不得替代規格。回答使用者亦 MUST 使用繁體中文。

理由：團隊主要使用語言為繁體中文；統一文件語言可降低理解成本並避免機器翻譯誤差。

### IV. 簡潔優先（YAGNI）

從最簡單可行的設計開始；NOT permitted 為了「未來可能需要」而加入抽象層、設定項或功能旗標。
重複三次以上的明確模式才考慮抽象化。任何超過單一檔案/單一模組的新抽象 MUST 在 plan 中明確說明
其必要性與替代方案。

理由：matcher 的領域邏輯多變，過早抽象會比重複本身造成更高的修改成本。

### V. 可觀測性（Observability）

對外行為與關鍵內部決策路徑 MUST 產出可被測試或人工檢視的輸出：
- 函式介面 SHOULD 為純函式或具明確輸入/輸出；副作用集中於邊界。
- 錯誤 MUST 以結構化方式回報（明確的錯誤型別或訊息），不得以靜默回傳預設值掩蓋。
- 重要決策路徑（例如：選用了哪一條匹配規則）SHOULD 可透過日誌或回傳值追溯。

理由：matcher 行為對輸入細節敏感，無觀測能力的失敗極難重現與修復。

## 額外約束（Additional Constraints）

- 程式碼識別字、檔名、commit 主旨第一行使用英文；說明段、PR body 使用繁體中文。
- 不得為了通過 hook 或檢查而使用 `--no-verify`、`--amend` 等繞過機制；應修復根本問題。
- 第三方相依性新增 MUST 在 plan 中說明理由與替代方案評估。

## 開發流程（Development Workflow）

1. `/speckit.specify` 產出規格 → 與使用者確認需求邊界。
2. `/speckit.clarify`（如需要）→ 解決規格中的模糊處。
3. `/speckit.plan` 產出技術計畫，並完成 Constitution Check（見 plan-template）。
4. `/speckit.tasks` 將計畫拆解為可逐步交付的任務。
5. 對每個任務：先寫測試（Red）→ 實作（Green）→ 重構 → 提交。
6. PR 審查 MUST 驗證：(a) 是否附帶測試、(b) 是否符合本 constitution、(c) 文件是否為繁體中文。

## Governance

本 constitution 為本專案所有開發實踐之最高準則；與其他文件衝突時以本文件為準。

修訂程序：
- 任何修訂 MUST 透過 PR 進行，並在 PR 描述中說明動機與影響範圍。
- 版本依語意化版本（Semantic Versioning）：
  - MAJOR：原則的移除、向後不相容的治理變更。
  - MINOR：新增原則或實質擴充指引。
  - PATCH：用字、錯字、非語意性釐清。
- 修訂合併後，MUST 同步更新 `.specify/templates/` 下受影響的範本，並於本檔頂部更新 Sync Impact Report。

合規檢查：
- 每個 plan MUST 完成 Constitution Check；違反原則者 MUST 在 Complexity Tracking 段落以理由與替代方案紀錄。
- PR 審查者 MUST 拒絕未通過 Constitution Check 或缺少測試的變更。

**Version**: 1.0.0 | **Ratified**: 2026-05-22 | **Last Amended**: 2026-05-22

<!-- Knowie: Project Knowledge -->
## Project Knowledge

This project maintains structured knowledge in `knowledge/`:

- **Principles** (`knowledge/principles.md`): Core axioms and derived development principles — the project's non-negotiable rules.
- **Vision** (`knowledge/vision.md`): Goals, current state, architecture decisions, and roadmap.
- **Experience** (`knowledge/experience.md`): Distilled lessons from past development — patterns, pitfalls, and takeaways.

Read these files at the start of any task to understand the project's *why* and constraints.
Additional context may be found in `knowledge/research/`, `knowledge/design/`, and `knowledge/history/`.
<!-- /Knowie -->

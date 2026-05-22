# Specification Quality Checklist: 個別查詢視圖（Individual View）

**Purpose**: 在進入 `/speckit.plan` 之前驗證規格的完整性與品質
**Created**: 2026-05-23
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] 未含實作細節（語言、框架、API）—— FR 全為技術中立描述
- [x] 聚焦於使用者價值與業務需求（原則 5 透明的最強形式）
- [x] 撰寫對象為非技術相關人員亦能理解
- [x] 所有必要章節皆已完成

## Requirement Completeness

- [x] 規格中已無 [NEEDS CLARIFICATION] 標記
- [x] 需求皆可測試且無歧義
- [x] 成功標準皆可量測（SC-001 5 分鐘 / SC-002 0% / SC-005 bytewise）
- [x] 成功標準與技術無關
- [x] 所有 Acceptance Scenarios 已定義（US1 三條、US2 兩條、US3 三條）
- [x] 邊界情境已辨識（5 種）
- [x] 範圍邊界清楚（Assumptions「不處理」明列 7 條）
- [x] 依賴與假設已記錄

## Feature Readiness

- [x] 所有 functional requirements 皆有對應的 acceptance criteria
- [x] User scenarios 涵蓋主要流程（P1 老師個別查詢、P2 admin 連結列表、P3 錯誤情境）
- [x] 功能符合 Success Criteria 中定義的可量測產出
- [x] 規格中未滲入實作細節

## Notes

- 第 1 次迭代全部通過——0 次 spec 修正、0 個 [NEEDS CLARIFICATION] 標記。
- 與 constitution 的對齊：TDD（SC-008 強制自動化測試）、繁中（全 FR）、規格優先、簡潔優先（明列「不處理」7 條）。
- 與 principles 的對齊：
  - 原則 5「對使用者透明」→ 整個 feature 的核心動機；FR-001~005 直接落地
  - 原則 4「結果可稽核」→ FR-007（不重算、來自既有 audit）、FR-012（個別 audit 子集下載）
- 與 experience.md 五條教訓對齊：
  - 教訓 5「library + CLI + Web 三入口共用核心」→ FR-009/010/011（不動核心、不改 schema、既有測試持續通過）
  - 教訓 1「黃金檔比對」→ SC-005（同一輸入兩次 bytewise 相同）
  - 教訓 4「資料來源無關性 ID 等價」→ URL 用 role_id（外部可控）而非自動索引
- **重要**：SC-001（5 分鐘真人測試）為人工驗證項目，不可自動化；本 feature 完成後須安排實測。
- **重要**：FR-003 / SC-002 的「技術詞零容忍」是可正規表達式驗證的硬要求，是本 feature 的代表性測試。

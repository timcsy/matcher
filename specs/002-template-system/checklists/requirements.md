# Specification Quality Checklist: 模板系統（Template System）

**Purpose**: 在進入 `/speckit.plan` 之前驗證規格的完整性與品質
**Created**: 2026-05-22
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] 未含實作細節（語言、框架、API）—— Typer 在 Assumptions 中作為 CLI 框架的選擇被引用，但所有 FR 為技術中立描述
- [x] 聚焦於使用者價值與業務需求
- [x] 撰寫對象為非技術相關人員亦能理解
- [x] 所有必要章節皆已完成

## Requirement Completeness

- [x] 規格中已無 [NEEDS CLARIFICATION] 標記
- [x] 需求皆可測試且無歧義
- [x] 成功標準皆可量測
- [x] 成功標準與技術無關（不含實作細節）
- [x] 所有 Acceptance Scenarios 已定義（每個 user story 至少 3 條）
- [x] 邊界情境已辨識（5 種）
- [x] 範圍邊界清楚（Assumptions 段「不處理」明列 6 條）
- [x] 依賴與假設已記錄

## Feature Readiness

- [x] 所有 functional requirements 皆有對應的 acceptance criteria
- [x] User scenarios 涵蓋主要流程（P1 套用、P2 瀏覽/匯出/匯入、P3 preferences 預留拒絕）
- [x] 功能符合 Success Criteria 中定義的可量測產出
- [x] 規格中未滲入實作細節

## Notes

- 標示為未完成的項目需先更新規格再進入 `/speckit.clarify` 或 `/speckit.plan`。
- 本檢核已於第 1 次迭代全部通過——0 次 spec 修正、0 個 [NEEDS CLARIFICATION] 標記。
- 與 constitution 的對齊：TDD（SC-009 強制自動化測試）、繁中（FR-015）、規格優先（本文件即為先於實作的產出）、簡潔優先（明列「不處理」6 條避免 scope creep）。
- 與 principles 的對齊：原則 1（FR-002/003/004/005、SC-005）、原則 2（FR-012、SC-003/004）、原則 4（FR-012）。
- 與 experience.md 的兩條教訓對齊：
  - 「黃金檔比對」→ FR-012（template_snapshot 寫入稽核）、SC-003、SC-004
  - 「介面預留 + 拒絕分支」→ User Story 3、FR-011、SC-006
- 向後相容：FR-014 + SC-007 明確要求階段 1 既有 48 測試 100% 繼續通過。

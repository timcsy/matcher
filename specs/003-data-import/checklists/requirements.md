# Specification Quality Checklist: 資料匯入（CSV / Excel）

**Purpose**: 在進入 `/speckit.plan` 之前驗證規格的完整性與品質
**Created**: 2026-05-22
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] 未含實作細節（語言、框架、API）—— openpyxl 與 chardet 在 Assumptions 中作為技術選擇引用，所有 FR 為技術中立描述
- [x] 聚焦於使用者價值與業務需求
- [x] 撰寫對象為非技術相關人員亦能理解
- [x] 所有必要章節皆已完成

## Requirement Completeness

- [x] 規格中已無 [NEEDS CLARIFICATION] 標記
- [x] 需求皆可測試且無歧義
- [x] 成功標準皆可量測
- [x] 成功標準與技術無關（不含實作細節）
- [x] 所有 Acceptance Scenarios 已定義（US1 五條、US2 四條、US3 四條）
- [x] 邊界情境已辨識（6 種）
- [x] 範圍邊界清楚（Assumptions「不處理」明列 6 條）
- [x] 依賴與假設已記錄

## Feature Readiness

- [x] 所有 functional requirements 皆有對應的 acceptance criteria
- [x] User scenarios 涵蓋主要流程（P1 CSV 教師-班級、P2 Excel 研習分組、P3 錯誤情境）
- [x] 功能符合 Success Criteria 中定義的可量測產出
- [x] 規格中未滲入實作細節

## Notes

- 第 1 次迭代全部通過——0 次 spec 修正、0 個 [NEEDS CLARIFICATION] 標記。
- 與 constitution 的對齊：TDD（SC-009 強制自動化測試）、繁中（FR-017）、規格優先、簡潔優先（明列「不處理」6 條 + 編碼啟發式而非 chardet）。
- 與 principles 的對齊：原則 1（FR-006/007/008/016 模板 aliases + 屬性可解釋）、原則 2（FR-015、SC-001 三路徑等價）、原則 4（FR-014 import_metadata）。
- 與 experience.md 三條教訓對齊：
  - 「黃金檔比對」→ FR-015、SC-001（三路徑等價比對）
  - 「介面預留 + 拒絕分支」→ FR-012、SC-006（preferences 在 M0 仍拒絕）
  - 「audit schema 演進採新增可選欄位 + null」→ FR-014、SC-010（import_metadata 欄位）
- 向後相容：FR-019 + SC-007 明確要求階段 1/2a 既有 82 測試 100% 繼續通過。

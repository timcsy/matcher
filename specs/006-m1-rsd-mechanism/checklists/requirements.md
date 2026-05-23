# Specification Quality Checklist: M1 RSD 分配機制

**Purpose**: 在進入 `/speckit.plan` 之前驗證規格的完整性與品質
**Created**: 2026-05-23
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] 未含實作細節（Python / library / pseudo code 等）——所有 FR 為技術中立描述
- [x] 聚焦於使用者價值與業務需求（兌現階段 1/2a 的志願預留）
- [x] 撰寫對象為非技術相關人員亦能理解
- [x] 所有必要章節皆已完成

## Requirement Completeness

- [x] 規格中已無 [NEEDS CLARIFICATION] 標記
- [x] 需求皆可測試且無歧義（FR-004 的 5 種 case 分明）
- [x] 成功標準皆可量測（SC-001 bytewise、SC-002 preference_rank 合法、SC-005 169 測試）
- [x] 成功標準與技術無關
- [x] 所有 Acceptance Scenarios 已定義（US1 三條、US2 三條、US3 兩條）
- [x] 邊界情境已辨識（7 種）
- [x] 範圍邊界清楚（Assumptions「不處理」明列 6 條）
- [x] 依賴與假設已記錄

## Feature Readiness

- [x] 所有 functional requirements 皆有對應的 acceptance criteria
- [x] User scenarios 涵蓋主要流程（P1 M1 跑通、P2 拒絕邏輯、P3 向後相容）
- [x] 功能符合 Success Criteria 中定義的可量測產出
- [x] 規格中未滲入實作細節

## Notes

- 第 1 次迭代全部通過——0 次 spec 修正、0 個 [NEEDS CLARIFICATION] 標記。
- 與 constitution 的對齊：TDD（SC-009 強制 ≥ 12 個新測試）、繁中（FR-013）、規格優先、簡潔優先（明列「不處理」6 條）。
- 與 principles 的對齊：
  - 原則 2「分配過程必須可驗證且可重現」→ FR-007、SC-001/007
  - 原則 3「不在資格集合外做最佳化」→ FR-004 RSD 嚴格依「資格集合 + 志願」決定，無分數加權
- 與 experience.md 六條教訓對齊：
  - 教訓 2「介面預留 + 拒絕分支」→ 本 feature **兌現** 階段 1 的預留；對偶地 US2「M1 + 空 prefs 拒絕」是介面預留的對偶
  - 教訓 3「audit schema 演進新增可選欄位 + null」→ FR-006、FR-010 schema v1.2→v1.3
  - 教訓 1「黃金檔比對」→ SC-001、SC-007
  - 教訓 5「library + CLI + Web 三入口共用核心」→ 本 feature **首次**動到核心（rules/filter 仍不動、allocator/pipeline/audit 動）；理由是「分配機制就是核心職責」，分層仍純粹（Web 層不動）
- **重要**：本 feature 為**階段 4 拆分**的 4a；M2（4b）與 Web UI 填志願（4c）獨立 feature；本 spec 明文劃清界線（FR-014 + Assumptions 不處理段）。
- **重要**：FR-010 + SC-006 的「5 個既有黃金檔重生 + diff 僅 schema/null 差異」是本 feature 與「教訓 3」綁定的硬要求；自動化測試保證邏輯不變。

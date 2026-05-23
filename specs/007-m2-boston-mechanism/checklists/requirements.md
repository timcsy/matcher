# Specification Quality Checklist: M2 Boston 分配機制

**Purpose**: 在進入 `/speckit.plan` 之前驗證規格的完整性與品質
**Created**: 2026-05-24
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] 未含實作細節
- [x] 聚焦於使用者價值與業務需求（兌現 vision 階段 4 三機制承諾）
- [x] 撰寫對象為非技術相關人員亦能理解
- [x] 所有必要章節皆已完成

## Requirement Completeness

- [x] 規格中已無 [NEEDS CLARIFICATION] 標記
- [x] 需求皆可測試且無歧義（FR-004 五種 case 分明）
- [x] 成功標準皆可量測（SC-001 bytewise、SC-005 黃金檔 diff、SC-009 ≥ 10 測試）
- [x] 成功標準與技術無關
- [x] 所有 Acceptance Scenarios 已定義（US1 三條、US2 三條、US3 兩條）
- [x] 邊界情境已辨識（6 種）
- [x] 範圍邊界清楚（Assumptions「不處理」明列 6 條）
- [x] 依賴與假設已記錄

## Feature Readiness

- [x] 所有 functional requirements 皆有對應的 acceptance criteria
- [x] User scenarios 涵蓋主要流程（P1 M2 跑通、P2 通用拒絕、P3 向後相容）
- [x] 功能符合 Success Criteria 中定義的可量測產出
- [x] 規格中未滲入實作細節

## Notes

- 第 1 次迭代全部通過——0 次 spec 修正、0 個 [NEEDS CLARIFICATION] 標記。
- 與 constitution 的對齊：TDD（SC-009 強制 ≥ 10 個新測試）、繁中（FR-012）、規格優先、簡潔優先（明列「不處理」6 條 + 不升 schema 版本）。
- 與 principles 的對齊：
  - 原則 2「分配過程必須可驗證且可重現」→ FR-006/007、SC-001/007
  - 原則 3「不在資格集合外做最佳化」→ FR-004 嚴格依層級 + 抽籤，無分數加權
- 與 experience.md 七條教訓對齊：
  - 教訓 7「核心職責 vs 周邊整合」→ 本 feature 動 allocator/pipeline/audit/errors/cli 屬「新分配機制 = 核心職責擴充」，**符合教訓 7 判準**
  - 教訓 3「audit schema 演進新增可選欄位 + null」→ FR-006 新增 `tie_break_random_index`，M0/M1 路徑為 null（schema 仍 v1.3，最節制版本）
  - 教訓 2「介面預留 + 拒絕分支」→ FR-003/005 通用化既有拒絕邏輯
  - 教訓 1「黃金檔比對」→ SC-001、SC-005
- **重要**：FR-005「重新命名」是本 feature 唯一輕微破壞性變更；以 alias 保留向後相容（plan 階段細化）；既有測試斷言視情況更新或借助 alias 保留。
- **重要**：SC-008 明文「M1 vs M2 在相同 seed 下可能結果完全不同」——這是兩種公平定義的本質差異，非 bug。

# Specification Quality Checklist: Web UI 主流程

**Purpose**: 在進入 `/speckit.plan` 之前驗證規格的完整性與品質
**Created**: 2026-05-22
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] 未含實作細節（語言、框架、API）—— FastAPI / HTMX / Jinja2 等只在 Assumptions 中提及為「傾向」，所有 FR 為技術中立描述
- [x] 聚焦於使用者價值與業務需求（核心想法 SC-001、原則 5 透明）
- [x] 撰寫對象為非技術相關人員亦能理解
- [x] 所有必要章節皆已完成

## Requirement Completeness

- [x] 規格中已無 [NEEDS CLARIFICATION] 標記
- [x] 需求皆可測試且無歧義
- [x] 成功標準皆可量測（SC-001 30 分鐘 / SC-002 ≤5 秒 / SC-003 100% bytewise / SC-005 ≥50 筆 / 等）
- [x] 成功標準與技術無關（不含實作細節）
- [x] 所有 Acceptance Scenarios 已定義（US1 四條、US2 三條、US3 三條）
- [x] 邊界情境已辨識（7 種）
- [x] 範圍邊界清楚（Assumptions「不處理」明列 7 條）
- [x] 依賴與假設已記錄

## Feature Readiness

- [x] 所有 functional requirements 皆有對應的 acceptance criteria
- [x] User scenarios 涵蓋主要流程（P1 完整媒合、P2 模板瀏覽、P3 媒合紀錄）
- [x] 功能符合 Success Criteria 中定義的可量測產出
- [x] 規格中未滲入實作細節

## Notes

- 第 1 次迭代全部通過——0 次 spec 修正、0 個 [NEEDS CLARIFICATION] 標記。
- 與 constitution 的對齊：TDD（SC-008 強制自動化測試）、繁中（FR-001/019/020）、規格優先、簡潔優先（明列「不處理」7 條）。
- 與 principles 的對齊：
  - 原則 1 → FR-005/006 模板可瀏覽 + 完整 schema 展示
  - 原則 4 → FR-007/008/011/013 結果頁含 audit 下載 + 媒合紀錄可重新查看
  - 原則 5 → FR-019 避免技術術語 + 整個 UI 面向行政與教師
- 與 experience.md 四條教訓對齊：
  - 「黃金檔比對」→ FR-008、SC-003（Web 與 CLI 路徑 audit 五段 bytewise 相同）
  - 「介面預留 + 拒絕分支」→ FR-014/015（機制選擇 UI 顯示但 disabled；preferences 不可填）
  - 「audit schema 演進」→ 媒合紀錄結構自始有 metadata 區塊，未來擴充採新增可選欄位 + null
  - 「資料來源無關性 ID 等價」→ FR-004 重用 data_import.py，不另寫表單→Roster 的轉換
- 向後相容：FR-018 + SC-008 明確要求階段 1/2a/2b 既有 116 測試 100% 繼續通過、CLI 介面不變。
- **重要**：SC-001（30 分鐘 + 真實學校行政測試）為人工驗證項目，不可自動化；本 feature 完成後須安排實測。

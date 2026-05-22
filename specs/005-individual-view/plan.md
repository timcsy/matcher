# Implementation Plan: 個別查詢視圖（Individual View）

**Branch**: `005-individual-view` | **Date**: 2026-05-23 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/005-individual-view/spec.md`

## Summary

在既有 `src/matcher/web/` 加上「個別查詢」端點與樣板：`GET /match/{record_id}/role/{role_id}` 顯示某角色的「我的視圖」；`GET /match/{record_id}/role/{role_id}/audit.json` 下載個別 audit 子集。代名詞替換以純函式 `humanize_rule_description` 實作，於 Jinja2 樣板呼叫。Admin 結果頁新增「個別查詢連結」可摺疊區段。**無新依賴；不動核心模組；不改 audit / match-record schema**。

## Technical Context

**Language/Version**: Python 3.11+（沿用）
**Primary Dependencies**: 沿用（無新增）；本 feature 僅在 `matcher.web` 套件內加程式碼
**Storage**: 無新增（從既有 `data/matches/*.json` 讀）
**Testing**: pytest + fastapi.testclient（沿用）；技術詞零容忍以正規表達式斷言
**Target Platform**: 沿用（跨平台 CLI / Web）
**Project Type**: 沿用（library + CLI + Web App）
**Performance Goals**: 個別查詢頁回應 ≤ 1 秒（純檔案讀 + 樣板渲染）
**Constraints**: 既有 142 測試 100% 通過（SC-007）；audit schema v1.2 不變；match-record/1.0 不變；不動核心模組（FR-009）
**Scale/Scope**: 同階段 3a；單一 record 角色數通常 ≤ 100

## Constitution Check

對齊 constitution v1.0.0 五原則：

| 原則 | 本計畫如何遵守 | 狀態 |
|---|---|---|
| I. 測試先行（TDD） | 每個 FR / SC 對應 ≥ 1 個 pytest；技術詞零容忍以正規表達式測試（SC-002） | ✅ |
| II. 規格優先 | spec.md 無 [NEEDS CLARIFICATION]；本 plan 為技術選型集中點 | ✅ |
| III. 繁體中文文件 | 所有 spec/plan/research/contracts 為繁中；UI 文案、錯誤訊息全繁中（FR-003） | ✅ |
| IV. 簡潔優先 | 無新增依賴；不動核心；單一純函式做代名詞替換；不引入「字典 / 規則引擎」之類抽象 | ✅ |
| V. 可觀測性 | 個別 audit 子集下載端點讓被媒合者亦能稽核；繁中錯誤訊息 | ✅ |

**Gate 評估**：通過，無 Complexity Tracking 條目。

## Project Structure

### Documentation (this feature)

```text
specs/005-individual-view/
├── plan.md
├── spec.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── http-endpoints.md
│   └── individual-audit-schema.json
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Source Code (新增/修改)

```text
src/matcher/web/
├── routes/
│   └── match.py                       # 修：在既有 match.py 內加兩個端點
├── humanize.py                        # 新：humanize_rule_description() 純函式
├── individual.py                      # 新：build_individual_audit_subset() 純函式
├── templates/
│   ├── individual_view.html           # 新：個別查詢頁
│   ├── individual_error.html          # 新：個別查詢專屬 404 頁（用語友善）
│   └── match_result.html              # 修：新增「個別查詢連結」可摺疊區段
└── app.py                             # 修：註冊 humanize Jinja2 filter

tests/
├── unit/
│   ├── test_web_humanize.py           # 新：代名詞替換 + 技術詞濾除
│   └── test_web_individual_subset.py  # 新：build_individual_audit_subset()
├── integration/
│   └── test_web_individual_view.py    # 新：US1+US2+US3 整合測試
└── （既有檔案不變）
```

**Structure Decision**：
- **route 放 `match.py`**：URL 已是 `/match/{record_id}/...` 系列，放同一檔減少匯入跳轉；不另立 `routes/individual.py`（簡潔優先）。
- **humanize 為純函式**：取 audit + template + role 為輸入，輸出 `list[dict]` 給樣板渲染；不在樣板裡寫複雜邏輯。
- **individual subset 也為純函式**：取 audit + role_id 輸出 dict；HTTP 層只負責序列化。
- **不動核心**：所有變更皆於 `src/matcher/web/` 內；核心 8 個既有模組完全不動，沿用教訓 5 的分層純度。

## Complexity Tracking

> Constitution Check 全部通過，本段保留空白。

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| （無）| | |

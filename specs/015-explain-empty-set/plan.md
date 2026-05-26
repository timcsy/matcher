# Implementation Plan: 配對失敗可解釋（資格集合為空）

**Branch**: `015-explain-empty-set` | **Date**: 2026-05-26 | **Spec**: [spec.md](./spec.md)

## Summary

讓最常見的失敗「資格集合為空」變得可解釋。技術手段：

1. **核心（可解釋性擴充）**：`filter_qualified` 在資格集合為空時，把已算好的 filter_trace
   與「每條規則淘汰幾組」的統計**攜帶進 `QualifiedSetEmpty` 例外**（而非丟掉）。
   新增純函式 `rejection_summary(trace, ruleset)` 算出 `{rule_id: 失敗組數}` + 元兇規則。
2. **CLI**：`_die` 對帶診斷的 QualifiedSetEmpty 多印「元兇規則 + 各規則淘汰數」（退出碼仍 10）。
3. **Web**：
   - UI 填名單（`run_from_form`）觸發空集合 → **回填名單頁 + 診斷紅字**（US2 保留輸入），
     沿用 feature 014 的 `_render_fill_form` 機制。
   - CSV 上傳（`run`）→ 失敗 record 的 error 帶診斷，結果頁失敗分支渲染。
4. **範本資料修正**：teacher-class R003 的 `in` 接受值由英文 `bilingual/stem/arts`
   改為與說明一致的 `雙語/stem/藝術`；連同 examples sidecar + golden 一起對齊。

audit「成功紀錄」schema **不變**（診斷只走失敗路徑：例外 / error dict / 回填），守住 FR-007。

## Technical Context

**Language/Version**：Python 3.11+（沿用）
**Primary Dependencies**：**無新增**
**Storage**：沿用檔案系統；失敗 record 的 error dict 內含診斷摘要（既有 JSON，加欄位）
**Testing**：pytest（沿用）
**Project Type**：Web + CLI 混合
**Constraints**：
- 核心變動限「可解釋性」職責：`filter.py`、`errors.py`、`cli.py`（教訓 7）
- 成功配對 audit schema 不變（SC-005）
- 退出碼 10 不變（FR-004）
**Scale/Scope**：核心 3 檔 + web 2 路由/樣板 + 1 內建範本 + examples + golden 重生 + 相關測試

## Constitution Check

| 原則 | 評估 | 備註 |
|---|---|---|
| I. TDD | ✅ | 先寫：空集合帶診斷、rejection_summary 純函式、CLI 輸出、Web 回填 + 診斷 |
| II. 規格優先 | ✅ | spec 已過 checklist |
| III. 繁體中文 | ✅ | 診斷文案面向使用者繁中 |
| IV. 簡潔 | ✅ | 無新依賴、無新抽象；rejection_summary 是單一純函式 |
| V. 可觀測性 | ✅ | **這個 feature 本身就是可觀測性的兌現**——把已算出卻丟棄的 trace 暴露出來 |

**核心變動正當性（教訓 7）**：擴充的是「可解釋性」這個核心職責（principles 原則 1：屬性與規則必須可解釋；原則 5：對使用者透明）。動 `filter/errors/cli` 的理由直接對應核心職責——「失敗也要能解釋為什麼」。非周邊整合可解決（失敗時輸入未持久化，診斷必須在核心算出時帶出）。

**結論**：gate 通過，無 Complexity Tracking 條目（無新依賴、無新抽象層）。

## Project Structure

### Source Code

```text
src/matcher/
├── errors.py            # ← QualifiedSetEmpty 擴充 __init__ 攜帶 trace + rule_stats
├── filter.py            # ← 空集合時算 rejection_summary 並附到例外；新增純函式 rejection_summary
├── cli.py               # ← _die 對 QualifiedSetEmpty 印診斷
├── templates/builtin/
│   └── teacher-class.yaml   # ← R003 in set 英文→中文（雙語/stem/藝術）
└── web/
    ├── routes/match.py      # ← run_from_form 空集合回填名單頁 + 診斷；run 失敗 record 帶診斷
    └── templates/
        ├── roster_form_fill.html  # ← 回填時顯示診斷紅字
        └── match_result.html      # ← 失敗分支渲染診斷

examples/teacher-class/
└── roster.targets.yaml      # ← feature 值 英文→中文 對齊 R003

tests/golden/                # ← teacher-class 相關 golden 重生（值對齊）
```

**Structure Decision**：核心改動局限「可解釋性」三檔（filter/errors/cli）；Web 是渲染端（周邊）；範本/examples/golden 是資料對齊。

## Complexity Tracking

無違規、無新依賴，不適用。

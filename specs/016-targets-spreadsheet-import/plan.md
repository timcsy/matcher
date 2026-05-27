# Implementation Plan: 對象名單也用試算表匯入

**Branch**: `016-targets-spreadsheet-import` | **Date**: 2026-05-26 | **Spec**: [spec.md](./spec.md)

## Summary

讓對象名單也能用 CSV/Excel 試算表匯入（上傳兩個獨立檔：角色一個、對象一個），不必寫
`.targets.yaml`。另提供「依範本動態產生」的角色/對象範例試算表下載。

技術手段：
1. **核心（資料匯入職責擴充，教訓 7）**：在 `data_import.py` 新增
   `load_targets_csv/xlsx(path, template) → tuple[Target,...]`（重用既有 `detect_csv_encoding`、
   `resolve_header`、`coerce_value`；對 `template.attributes.targets` 對齊表頭；id 欄可省略→自動編號）；
   `load_roster_csv/xlsx` 加可選參數 `targets=None`（給定則用之、否則沿用 `.targets.yaml` 旁檔）。
   向後相容：CLI 旁檔路徑不受影響。
2. **Web 上傳**：`/match/run` 第二個檔案欄位接受對象試算表（CSV/Excel/或既有 YAML，依副檔名分派）；
   解析後以 `targets=` 注入 `load_roster_csv`。
3. **動態範例（純 web，無核心）**：端點 `/templates/{id}/example/{roles|targets}.{csv|xlsx}`
   依範本 schema 即時組出表頭（中文顯示名稱 + 編號/容量）+ 一列格式提示；上傳頁連結指向之。

audit schema **不變**（對象載入後結構與 YAML 旁檔一致 → SC-005 等價）。無新依賴（openpyxl、csv 已有）。

## Technical Context

**Language/Version**：Python 3.11+（沿用）
**Primary Dependencies**：**無新增**（openpyxl 既有、csv 標準庫）
**Storage**：沿用檔案系統；上傳檔走 tmp，不新增持久化型別
**Testing**：pytest（沿用）
**Project Type**：Web + CLI 混合
**Constraints**：
- 核心變動限「資料匯入」職責：`data_import.py`（教訓 7）
- CLI `.targets.yaml` 旁檔向後相容（FR-008）
- audit schema 不變；對象試算表 vs YAML 旁檔 audit 等價（SC-005）
- 動態範例只保證欄位/格式，不保證「下載原樣可跑」（spec US2 已界定）
**Scale/Scope**：核心 data_import +2~3 函式 + 1 參數；web 上傳頁雙檔 + 範例端點 + 樣板

## Constitution Check

| 原則 | 評估 | 備註 |
|---|---|---|
| I. TDD | ✅ | 先寫：targets CSV/Excel 載入、中文表頭對齊、auto-id、targets= 注入、範例端點表頭、SC-005 等價 |
| II. 規格優先 | ✅ | spec 過 checklist |
| III. 繁體中文 | ✅ | 範例表頭中文、錯誤訊息繁中 |
| IV. 簡潔 | ✅ | 無新依賴；重用 data_import 既有 helper；動態範例避免維護靜態檔 |
| V. 可觀測性 | ✅ | 對象檔缺容量/欄位不符 → 明確錯誤；沿用既有 RosterColumnMismatch 風格 |

**核心變動正當性（教訓 7）**：`load_targets_csv/xlsx` 是「資料匯入」核心職責的擴充
——與既有 roster 匯入同類工作（編碼、表頭對齊、型別轉換），放 data_import 供 CLI/Web 共用最自然。
`load_roster_csv(targets=)` 是小幅、向後相容的參數新增。

**結論**：gate 通過，無新依賴、無 Complexity Tracking 條目。

## Project Structure

```text
src/matcher/
├── data_import.py                # ← 新增 load_targets_csv/xlsx + _resolve_target_headers
│                                 #    + load_roster_csv/xlsx 加 targets=None 參數
└── web/
    ├── routes/match.py           # ← /match/run 第二檔（對象試算表）解析 + targets= 注入
    ├── example_gen.py            # ★ 新增：依範本 schema 產生範例 CSV/Excel bytes（純函式）
    ├── routes/pages.py           # ← 新增 /templates/{id}/example/{roles|targets}.{csv|xlsx} 端點
    └── templates/new_match.html  # ← 上傳區：角色檔 + 對象檔兩欄 + 角色/對象範例下載連結

tests/
├── unit/test_targets_import.py            # 對象 CSV/Excel 載入 + auto-id + 中文表頭
├── unit/test_example_gen.py               # 範例產生表頭 == 範本屬性 + 格式提示列
└── integration/test_web_two_file_import.py # 上傳兩檔配對 + 範例端點 + SC-005 等價
```

**Structure Decision**：核心擴充限 data_import（資料匯入）；動態範例與雙檔上傳屬 web 周邊。

## Complexity Tracking

無違規、無新依賴，不適用。

# Implementation Plan: 模板創作工具 UI

**Branch**: `011-template-author-ui` | **Date**: 2026-05-25 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/011-template-author-ui/spec.md`

## Summary

新增 `/templates/new`（簡單 + 進階模式）與 `/templates/<id>/edit` 兩條路徑、3 個後端端點（`POST /templates/validate`、`POST /templates/save`、`GET /templates/<id>/versions/<v>`）。`TemplateRegistry` 加 `_scan_custom_dir()` 載入 `data/templates/<id>/v<N>.yaml`；內建模板 read-only、id 衝突在儲存階段拒絕。媒合紀錄頁加「以此版本再執行」按鈕（從既有 audit.template_snapshot 還原）。**動核心 `template_loader.py`——是教訓 7 第 3 種合法情境**（核心職責擴充：模板管理本就是核心責任）。

## Technical Context

**Language/Version**: Python 3.11+（沿用）
**Primary Dependencies**: 沿用（fastapi、uvicorn[standard]、jinja2、python-multipart、PyYAML、openpyxl、Typer、pytest、httpx[dev]、weasyprint）——**無新增**
**Storage**: 沿用 `data/matches/` + 新增 `data/templates/<id>/v<N>.yaml`（同檔案系統風格，無 DB）
**Testing**: pytest + FastAPI TestClient；新增「模擬重啟」測試（重新建立 TemplateRegistry 確認自訂模板仍可載入）
**Target Platform**: Linux server / macOS（uvicorn）；瀏覽器端純 HTML + 少量 vanilla JS（clipboard API + 動態增減行）
**Project Type**: Library + CLI + Web service 三入口
**Performance Goals**: 模板儲存 ≤ 200ms；TemplateRegistry 啟動掃描 + 100 個自訂模板 ≤ 500ms
**Constraints**:
- **動核心**：限定於 `src/matcher/template_loader.py` 內**新增** `_scan_custom_dir()` 等方法；既有 `parse_template`、`TemplateRegistry.get/has/list_ids` 既有方法簽名不變（SC-010）
- 其他核心模組 `{rules,filter,allocator,pipeline,audit,errors,data_import,rng,roster}` 完全不動
- 繁中文案；技術詞零容忍延伸至「自動生成 description」
**Scale/Scope**: ~12 個檔案變動；估 ~700 LOC

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 原則 | 狀態 | 說明 |
|---|---|---|
| I. TDD 不可妥協 | ✅ | 每 US 先寫整合測試（建立 / 驗證 / 編輯 / 版本歷史 / fork / 重啟）；TDD 紅→綠 |
| II. 規格優先 | ✅ | spec → plan → tasks → implement |
| III. 繁體中文文件 | ✅ | 所有 spec/plan/tasks/PR/commit/UI/自動生成 description 皆繁中 |
| IV. 簡潔優先 (YAGNI) | ✅ | 無新依賴；無 SQLite；版本控制純檔案；不做 diff 視覺化 / 草稿 / 鎖定 / diff highlight；JS 限 clipboard + 動態行 |
| V. 可觀測性 | ✅ | 驗證錯誤明確繁中訊息；儲存成功/失敗 status 清楚；TemplateRegistry 掃描錯誤不靜默 |

### 動核心合法性審視（教訓 7）

> 「動核心的理由必須是『核心職責的擴充』」

模板管理是 matcher 的核心職責——`teacher-class` / `study-group` 等內建模板本身就被 `TemplateRegistry` 統一管理。本 feature 擴充 `TemplateRegistry` 載入「使用者建立的自訂模板」，本質與「載入內建模板」**完全同性質**——只是來源從套件資源換成檔案系統。**這屬於核心職責的合法擴充**（與階段 4a/4b 加 `allocate_m1`/`allocate_m2` 同等性質）。

**邊界保守設計**：
- 不動 `parse_template`、`Template` dataclass 等既有結構（既有測試 0 影響）
- 新增 `_scan_custom_dir()` 為獨立方法；既有 `_scan()` 不動
- 內建 vs 自訂衝突解決邏輯獨立成方法 `_resolve_id_conflict()`

**Gate 通過。** Complexity Tracking 段不需填寫。

## Project Structure

### Documentation (this feature)

```text
specs/011-template-author-ui/
├── plan.md              # 本檔
├── spec.md              # 規格（已完成）
├── research.md          # Phase 0 — 6 項決策
├── data-model.md        # Phase 1 — 模板儲存與表單 view model
├── quickstart.md        # Phase 1 — 10 步驟端到端驗收
├── contracts/
│   ├── web-routes.md    # 5 個 HTTP 端點契約
│   └── persistence.md   # data/templates/ 檔案佈局 + TemplateRegistry 掃描契約
├── checklists/
│   └── requirements.md  # ✓ PASS
└── tasks.md             # Phase 2
```

### Source Code (repository root)

```text
src/matcher/
├── template_loader.py                            # ← 修改（核心職責擴充）：加 _scan_custom_dir() + save_custom() + list_versions() + get_version()
└── web/
    ├── routes/
    │   ├── templates.py                          # ← 修改：加 5 個新端點 (GET /templates/new, GET /templates/<id>/edit, POST /templates/validate, POST /templates/save, GET /templates/<id>/versions/<v>)
    │   └── match.py                              # ← 修改（極小）：結果頁加「以此版本再執行」連結；/match/new 接受 ?template_snapshot=<rid>
    ├── template_form.py                          # ← 新檔：簡單模式表單 → YAML dict 組裝 + 規則 description 自動生成
    ├── templates/
    │   ├── template_authoring.html              # ← 新檔：新增模板頁
    │   ├── template_edit.html                    # ← 新檔：編輯模板頁
    │   ├── template_detail.html                  # ← 修改：自訂模板「編輯」/內建模板「Fork」；版本歷史段
    │   ├── templates_list.html                   # ← 修改：callout 改「新增模板」按鈕
    │   ├── match_result.html                     # ← 修改：加「以此模板版本再執行」按鈕
    │   └── new_match.html                        # ← 修改（小）：?template_snapshot=<rid> 提示
    └── static/
        └── template_form.js                      # ← 新檔：clipboard + 動態增刪行

data/templates/                                   # 執行時建立；.gitkeep
└── .gitkeep

tests/integration/
├── test_template_authoring_simple.py             # US1
├── test_template_authoring_advanced.py           # US2
├── test_template_editing_versions.py             # US3
├── test_template_validation_endpoint.py          # 通用
└── test_match_rerun_from_snapshot.py             # US4

tests/unit/
├── test_template_form_assembly.py                # template_form.py 純函式
└── test_template_registry_custom_scan.py         # TemplateRegistry._scan_custom_dir() 各情境
```

**核心改動限定**：僅 `src/matcher/template_loader.py`；其他 9 個核心模組 0 改動。FR-020 + SC-010 由 git diff 守住。

**Structure Decision**：沿用既有 single-project 結構；新增 `data/templates/` 持久化目錄、`web/template_form.py` 與 `static/template_form.js`。

## Complexity Tracking

> 無違反項。動核心已在 Constitution Check 段論證為「核心職責擴充」（教訓 7 第 3 種合法情境）。

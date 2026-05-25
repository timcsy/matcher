# Phase 0 — Research：稽核報告 PDF 匯出

無 NEEDS CLARIFICATION（4 個方向問題已在 brief 階段確認）。本檔記錄 6 項技術決策。

## D1：PDF 函式庫選擇

**Decision**：**WeasyPrint ≥ 60.0**

**Rationale**：
- 可重用既有 jinja2 樣板（HTML/CSS → PDF）——工程量比 reportlab 程式式組裝小一個量級
- CSS3 支援完整，含 `@page`、分頁、頁碼、可變字體
- 字體嵌入支援好；中文搜尋友善（非 outline glyph）
- 與本專案「無 JS、server-rendered HTML」的 jinja2 風格一致

**Alternatives**：
- (a) reportlab — 純 Python 無系統依賴，但需重寫整個版面邏輯；工程量 3-5×
- (b) xhtml2pdf — CSS 支援差；中文字體支援不穩
- (c) chromium headless（playwright/puppeteer）— 依賴極重；引入瀏覽器引擎不符 YAGNI

## D2：系統依賴 graceful degrade 策略

**Decision**：模組 import 時 lazy 嘗試 import weasyprint；失敗則 `_WEASYPRINT_AVAILABLE = False`，PDF 端點 / CLI 子指令拋友善訊息（Web 回 503 + 中文訊息、CLI exit 50 + 安裝指引）。**Web 服務本身仍可啟動**——既有 256 測試不受影響。

**Rationale**：
- spec FR-012：「PDF 端點 graceful degrade 為 503；不阻斷其他流程」
- 開發者 / CI 機器若未裝 Pango，仍能跑既有測試與 Web；只有 PDF 相關測試會 skip
- 嚴格捕獲 `ImportError` 與 `OSError`（後者為 Pango 載入失敗）

**Alternatives**：
- (a) 應用啟動即 fail-fast — 阻斷未裝系統依賴的部署
- (b) 把 weasyprint 標為 optional dependency group — 套件結構複雜化

## D3：字體嵌入策略

**Decision**：將 **Noto Sans CJK TC Regular + Bold** 兩個 `.otf` 檔放 `src/matcher/web/static/fonts/`；PDF 樣板 CSS 用 `@font-face` 指向絕對檔案路徑（透過 jinja2 context 注入或 weasyprint `url_fetcher`）。OFL.txt 一併放置以符授權。

**Rationale**：
- 跨環境一致性：不依賴系統字體；docker / K8s 環境直接可用
- 中文可搜尋（非 outline glyph）—— WeasyPrint 預設嵌入 subset 而非 outline
- OFL（SIL Open Font License）允許嵌入、再散布
- 兩個字重（Regular + Bold）足以表達標題 / 內文層級；省 binary 大小

**Alternatives**：
- (a) 依賴系統字體 — macOS / Linux fallback 不一致；某機器中文變問號
- (b) 嵌入完整 5 字重 Noto Sans CJK family — binary 太大（~50MB），不必要
- (c) 在 build / install 時下載 — 開發體驗差；CI 機器要連網

**Risk**：repo 加 ~10MB binary（兩個 OTF 各約 5MB；可能更小若用 subset 工具如 fonttools 預先 subset 至常用 5000 漢字 ~2MB）—— **plan 階段先用完整 OTF**；若 repo size 成問題再考慮 subset。

## D4：PDF render 純函式介面

**Decision**：

```python
# src/matcher/web/pdf.py
def render_match_report_pdf(
    audit: dict,
    *,
    record_meta: dict,            # {"id": ..., "created_at": ..., "input_file": ...}
    role_id: str | None = None,   # None → admin 版；str → individual 版
    template: Optional[Template] = None,  # 給 humanize 用；無則跳過代名詞替換
) -> bytes:
    ...
```

**Rationale**：
- 純函式介面方便單元測試與 CLI 共用（library 設計、教訓 5）
- audit + record_meta 分離：CLI 跑時可從 JSON 檔直接讀 audit；Web 跑時從 MatchRecord 取
- role_id 為 None / str 二分清楚
- template 為可選——CLI 路徑若使用者沒提供，可不做代名詞替換；Web 路徑可從 TemplateRegistry 查

**Alternatives**：
- (a) 強制傳 MatchRecord — CLI 端要重組 dataclass；不必要
- (b) admin 與 individual 分兩個函式 — 重複大量邏輯；不如一個函式 + role_id 二分

## D5：PDF 樣板的版面決策

**Decision**：新增 `src/matcher/web/templates/pdf/match_report.html` 與 `pdf/individual_report.html`——**不重用** `match_result.html` / `individual_view.html`。

**Rationale**：
- A4 列印版面需 `@page` 設定（紙張尺寸、margin、頁首頁尾）；螢幕版不需
- 螢幕版含 `<form>`、`<details>`、`<button>` 等元素；PDF 版要清乾淨
- 兩者文案/翻譯可能相同——可用 jinja2 `include` 共用內部片段（如分配表 partial）
- 改動隔離：螢幕樣板未來變更不必擔心影響 PDF 版

**Alternatives**：
- (a) 重用既有樣板 + print CSS media query — WeasyPrint 對 print media 支援好，但會把 `<form>` 也 render 進 PDF；要 hide 一大堆元素
- (b) 完全分離兩套樣板 — 文案維護兩處；用 `include` 共用核心 partial 是中庸方案

## D6：CLI 子指令位置

**Decision**：新增 `src/matcher/cli_report.py` 含 typer sub-app；`cli.py` **僅一行** `app.add_typer(report_app, name="report")` 引入。

**Rationale**：
- 保守保護 `cli.py`：feature 010 對 cli.py 的 diff 僅一行 + 一個 import；不動既有 run / template / serve 等
- `cli_report.py` 是新檔，未來 PDF 報告子指令的擴充（如 `report --batch`）皆在此檔
- 符合 spec FR-011 + Constitution Check「不動核心」精神的延伸

**Alternatives**：
- (a) 在 `cli.py` 直接加 `@app.command()` — 動到 cli.py 結構；違反「最小 diff」精神
- (b) 把 PDF 邏輯也放 `cli_report.py` — 違反 D4「PDF 純函式集中於 pdf.py」

## 沿用既有依賴

- jinja2（既有）：PDF 樣板渲染
- pytest + TestClient + CliRunner（既有）
- **dev 新增 pypdf**？——本來打算用 pypdf 解 PDF 文字驗證；但 pypdf 已是常見 pytest 工具；視 SC-004 測試難度決定。**plan 暫不引入**；先在 tasks 階段試「直接搜 PDF bytes 看中文是否出現」這種輕量方式，必要時再加 pypdf 至 dev dependencies。

**結論**：所有未知已解，可進 Phase 1。

# Research: Web UI 主流程技術選型

**Branch**: `004-web-ui-main` | **Date**: 2026-05-22

每項決策以「決策 / 理由 / 替代方案」三段式記錄。

---

## R-001 後端框架：FastAPI

- **Decision**：FastAPI ≥ 0.110。
- **Rationale**：
  - Python 生態事實標準；與既有 library 完美整合（純 Python 函式呼叫即可）。
  - 自動產生 OpenAPI（雖然本 feature 未公開 REST API，但有助開發期測試）。
  - 內建 type hint 驗證、檔案上傳支援、`TestClient` 測試體驗極佳。
  - 同步 / 非同步均可——本專案媒合 < 1 秒、可全部同步寫，後續若需 async 也好擴。
- **Alternatives considered**：
  - **Flask**：更輕量但 type hints / 檔案上傳 / 測試體驗較舊。
  - **Starlette**（FastAPI 底層）：能更低階控制但本階段不需要。
  - **Django**：太厚重；本專案無需 ORM、admin。

---

## R-002 前端策略：HTMX + Jinja2（server-rendered）

- **Decision**：HTMX 1.9+（透過 CDN 載入）+ Jinja2 ≥ 3.1（FastAPI 內建支援）。
- **Rationale**：
  - **無 Node toolchain**——與專案「簡潔優先」一致；不需 npm / vite / webpack。
  - HTMX 的「server returns HTML fragment, swap into DOM」模型對「新建媒合 4 步驟向導」極合適。
  - 漸進增強：JS 失效時仍可基本運作（全頁 reload）；對學校情境的舊筆電 / 殘留 IE 更穩。
  - 樣板繼承（base.html）讓繁中文案集中管理。
- **Alternatives considered**：
  - **React / Vue + Vite**：富 UX 但引入 Node toolchain；本階段 UI 複雜度遠不到需要的程度。
  - **Alpine.js**：與 HTMX 對等但更輕量；保留作為未來「輕度互動」備案。
  - **純表單 POST + redirect**：最簡但「失敗時保留輸入」較難；HTMX 解決此痛點。

---

## R-003 ASGI server：uvicorn[standard]

- **Decision**：uvicorn ≥ 0.27，安裝 `[standard]` extras（含 httptools、uvloop、watchfiles）。
- **Rationale**：
  - FastAPI 標配；單一指令 `uvicorn matcher.web.app:app` 即啟動。
  - `--reload` 對開發期友好。
  - 純 Python 後備（無 Rust binary 依賴問題）。
- **Alternatives considered**：
  - **hypercorn**：HTTP/2 支援更好但本階段不需要。
  - **gunicorn + uvicorn worker**：production-grade 但 v1 單機 / LAN 無需。

---

## R-004 檔案上傳：python-multipart

- **Decision**：python-multipart ≥ 0.0.9（FastAPI 上傳檔案的必要依賴）。
- **Rationale**：FastAPI 處理 `multipart/form-data` 的標配；無替代。
- **Alternatives considered**：（無，這是 FastAPI 上傳必須）

---

## R-005 媒合紀錄儲存：純檔案系統

- **Decision**：每筆媒合一個 JSON 檔，路徑為 `data/matches/<YYYY-MM-DDTHH-MM-SS>-<uuid8>.json`；
  檔名同時提供「依時間排序」與「唯一性」。
  目錄不存在時自動建立。`.gitignore` 加 `data/` 排除版本控制。
- **Rationale**：
  - 與 vision 架構決策「檔案系統為主，避免外部資料庫依賴」一致。
  - 列表時讀目錄 + 依檔名排序（O(N log N) 但 N ≤ 10000，瞬間完成）。
  - 單檔 atomic write（先寫 .tmp 再 rename）避免半寫狀態。
- **Alternatives considered**：
  - **SQLite**：查詢更彈性但需引入額外依賴與 schema 演進管理（vision 排除）。
  - **單一 JSON Lines**：append-only 但「重新查看單筆」要重讀整檔；不適合長期。
  - **目錄 + index file**：避免每次掃目錄，但 N 小時無收益。

---

## R-006 媒合紀錄檔結構

- **Decision**：每筆紀錄為單一 JSON，頂層欄位：
  ```json
  {
    "schema_version": "match-record/1.0",
    "id": "<timestamp>-<uuid8>",
    "created_at": "<ISO 8601>",
    "template_id": "teacher-class",
    "seed": 123456,
    "input_file": "roster.csv",
    "mechanism": "M0",
    "status": "success" | "failed",
    "audit": <完整 audit dict>,             // status=success 時
    "error": {                              // status=failed 時
      "type": "RosterColumnMismatch",
      "exit_code": 31,
      "message": "..."
    }
  }
  ```
- **Rationale**：
  - 自含——光看一個檔案能完整重現該次媒合的所有 metadata 與結果。
  - `audit` 內部已含 template_snapshot、import_metadata，無需重複。
  - status / error 兩段讓失敗紀錄也有結構化資料供分析。
- **Alternatives considered**：
  - **只記成功**：失去稽核「為何失敗」的能力；違反原則 4 精神。

---

## R-007 `matcher serve` CLI 子命令

- **Decision**：CLI 新增 `matcher serve [--host 127.0.0.1] [--port 8000] [--reload]`，
  內部呼叫 `uvicorn.run("matcher.web.app:app", ...)`。預設綁定 127.0.0.1（不對外）。
- **Rationale**：
  - 沿用 Typer 子命令風格（與 `matcher template` 平行）。
  - `--host 127.0.0.1` 預設安全（vision 無 auth 假設「LAN 信任」，但預設不應暴露）。
  - 使用者需自行改 `--host 0.0.0.0` 才能讓 LAN 內其他電腦連線——這是顯式的安全選擇。
- **Alternatives considered**：
  - **獨立 `matcher-server` 可執行檔**：增加 entry point 複雜度，無收益。

---

## R-008 4 步驟新建媒合流程的 UI 實作

- **Decision**：採**單頁 + HTMX swap** 實作向導：
  - 同一 URL `/match/new`，state 由 server 端記錄於暫存（cookie 或 query string）。
  - HTMX 觸發 partial swap：step1 結束 → POST /match/new/step2 → 回傳 step2 樣板 → swap 進 #wizard-content。
  - 最終一步 POST /match/run → 重定向到結果頁 `/match/{record_id}`。
- **Rationale**：
  - 失敗時容易保留前面填的內容（HTMX 收到錯誤訊息只 swap 出錯區段）。
  - URL 簡潔；無需 query string state machine。
- **Alternatives considered**：
  - **4 個獨立 URL**：較傳統但「上一步」按鈕需自行管理 state。
  - **單頁 SPA**：違反「無 Node toolchain」原則。

---

## R-009 audit 與 record id 的對應

- **Decision**：
  - `data/matches/<record_id>.json` 內含 `audit` 區段。
  - 「下載稽核紀錄」端點 `GET /api/audit/{record_id}` 直接從紀錄檔提取 `audit` 並輸出為 JSON（與 CLI `--output` 寫出的格式完全相同，沿用 `dump_audit_json` 序列化）。
- **Rationale**：保證 SC-003 的「Web/CLI audit 五段 bytewise 相同」。
- **Alternatives considered**：
  - **重新跑一次媒合**：浪費資源、且若 seed 相同會浪費 RNG。

---

## R-010 上傳檔處理

- **Decision**：
  - FastAPI 的 `UploadFile` 直接讀入記憶體 bytes（≤ 5 MB 限制下安全）。
  - 寫到 `tempfile.NamedTemporaryFile` 後傳給 `load_roster_csv` / `load_roster_xlsx`（既有介面要 `Path`）。
  - 處理結束後 `tmp.unlink()`；不保留原始檔。
  - 同時讀取對應的 `<stem>.targets.yaml`——本階段使用者必須**同步上傳 targets 旁檔**或選擇內建模板（targets 內嵌於 template）。
- **Rationale**：
  - 5 MB 上限讓記憶體載入安全；對 ≤ 1000 列名單綽綽有餘。
  - 重用既有匯入路徑保證資料來源無關性（教訓 4）。
- **Alternatives considered**：
  - **stream 處理**：本階段檔案小，串流增加複雜度無收益。

---

## R-011 targets 來源處理

- **Decision**：本 feature **暫不**透過 Web UI 上傳 targets 旁檔；使用者只能在「**已含內建 targets 的模板**」下使用。
  教師-班級與研習分組兩個內建模板**將擴充為自含 targets**（template schema 新增選填 `default_targets` 欄位），讓 Web UI 完整可用而無需另上傳旁檔。
- **Rationale**：
  - 「targets 旁檔」設計適合 CLI 的批次自動化情境，但對 Web UI 行政手動操作流程過繁。
  - 加入 `default_targets` 是 template schema 的小擴充（與既有「新增可選欄位 + null」教訓一致）；無 default_targets 的模板仍可走 CLI + 旁檔。
- **Alternatives considered**：
  - **Web UI 也要求上傳 targets 旁檔**：行政摩擦過大；與「30 分鐘完成」目標衝突。
  - **內建一份 targets 寫死在 web/store.py**：違反「模板為一級概念」原則。

---

## R-012 內建模板擴充：default_targets

- **Decision**：模板 schema 新增**選填**頂層欄位 `default_targets: list[dict]`，結構與 roster.yaml 中的 targets 段相同。
  教師-班級與研習分組兩個內建模板補上常用的對象資料（5 個班 / 3 個分組）。
- **Rationale**：
  - 模板既已涵蓋「屬性 schema + 規則 + UI 欄位 + 報告格式」四層，再加「預設對象資料」一層是自然延伸。
  - Web UI 路徑下：選模板 → 系統自動採用 `default_targets` → 使用者只需上傳 roles 端名單。
  - CLI 路徑下：使用者仍可 `--roster <yaml>` 提供自訂 targets（覆蓋 default_targets）。
- **Alternatives considered**：
  - **要求 Web 上傳 targets 旁檔**：見 R-011 已駁回。
  - **schema 升級為「targets 必填」**：破壞向後相容。

**注意**：此擴充意味階段 2a 的兩個內建模板需要更新；既有黃金檔 `teacher-class-template.audit.json` 與 `study-group-template.audit.json` 需重生（template_snapshot 改變）。`teacher-class-csv.audit.json` 與 `study-group-xlsx.audit.json` 也需重生（template_snapshot 改變、但 assignment 不變）。

---

## R-013 audit schema 不升版本

- **Decision**：本 feature 不升 audit schema（保持 v1.2）。
  「media record」是新概念（媒合紀錄 = audit + metadata 包裝），自有 schema_version `"match-record/1.0"` 與 audit schema 分離。
- **Rationale**：
  - audit schema 是「一次媒合的純結果」；media record schema 是「Web app 對該次執行的脈絡紀錄」。
  - 兩者語意不同、演進步調可能不一致，分離較乾淨。
- **Alternatives considered**：
  - **把 metadata 塞進 audit 中**：違反 audit「核心媒合結果」的純粹性。

---

## R-014 靜態資源策略

- **Decision**：
  - HTMX：CDN（`https://unpkg.com/htmx.org@1.9.10`）；學校網路通常可達。
  - 自寫 CSS：單一 `src/matcher/web/static/style.css`，極簡（< 200 行）、無框架。
  - FastAPI 以 `StaticFiles` mount 於 `/static`。
- **Rationale**：
  - 無 Node toolchain（簡潔優先）。
  - CDN 失敗時 HTMX 不可用——退化為純表單 reload；接受此風險。
- **Alternatives considered**：
  - **本地化 HTMX 檔**：避免 CDN 依賴但需要 vendor 一份 JS；本階段 YAGNI。
  - **Tailwind / Bootstrap**：對極簡 UI 過重。

---

## R-015 測試策略

- **Decision**：
  - 用 `fastapi.testclient.TestClient`（同步 wrapper of httpx）寫 HTTP 整合測試。
  - 不引入 Playwright / Selenium（YAGNI、繁中介面以「response body 含某字串」斷言足矣）。
  - 黃金檔不新增；「Web 路徑 audit 與 CLI 五段 bytewise 相同」改以程式比對（同 SC-003）。
- **Rationale**：
  - 單元 + HTTP 整合涵蓋率對 server-rendered 應用足夠。
  - 端對端瀏覽器測試（Selenium）成本與本階段不成比例。
- **Alternatives considered**：
  - **Playwright**：對未來複雜互動有價值；本階段不需要。

---

## 已解決的 NEEDS CLARIFICATION 列表

本 plan 中無 NEEDS CLARIFICATION 標記；spec.md Assumptions 中標為「由 plan 決定」的項目皆於 R-001 ~ R-015 解決。

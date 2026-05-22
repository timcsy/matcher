# Research: 個別查詢視圖技術選型

**Branch**: `005-individual-view` | **Date**: 2026-05-23

每項決策以「決策 / 理由 / 替代方案」三段式記錄。

---

## R-001 代名詞替換實作：純 Python 函式

- **Decision**：建立 `src/matcher/web/humanize.py`，內含 `humanize_rule_description(description: str, template: Template) -> str`。
  以正規表達式 `r"role\.(\w+)"` 與 `r"target\.(\w+)"` 掃描描述字串，
  將每個匹配替換為「您的 <attribute 顯示名>」與「該對象的 <attribute 顯示名>」。
  顯示名查找順序：`AttributeDecl.description` → `AttributeDecl.key`（fallback）。
- **Rationale**：
  - 純函式、無 IO，極易測試。
  - 不引入 Jinja2 filter 之外的自訂機制；filter 是 thin wrapper。
- **Alternatives considered**：
  - **在樣板裡 inline 正規表達式**：可讀性差、難測。
  - **預處理 template 載入時就替換**：違反「audit 不可變」原則（教訓 3：稽核紀錄是凍結快照，不應動）。

---

## R-002 個別 audit 子集結構

- **Decision**：`build_individual_audit_subset(audit: dict, role_id: str) -> dict`，回傳：
  ```json
  {
    "record_id": "<id>",
    "role_id": "T01",
    "role_attributes": {"name": "王老師", ...},
    "assignment": {"target_id": "C04", "target_attributes": {"name": "三年丁班", ...}} | null,
    "filter_trace_subset": [
      {"target_id": "C01", "qualified": true, "matched_rules": ["R001","R002"]},
      ...
    ],
    "allocation_step": {"step": 1, "candidates": [...], "chosen": "C04"} | null
  }
  ```
- **Rationale**：
  - **完整**：FR-002 要求顯示「基本資訊 + 分配結果 + 過程說明」，本結構涵蓋三項。
  - **不洩漏其他角色**：filter_trace_subset 只含該 role 的條目；allocation_step 只含該 role 的步驟（依 audit.allocation_trace 過濾）。
  - **可下載**：FR-012 要求個別 audit 子集 JSON 下載；本結構可序列化直接吐出。
- **Alternatives considered**：
  - **直接給完整 audit**：洩漏其他人資料，違反原則 5「對使用者透明」中「自己」的範圍。
  - **省略 `role_attributes`**：違反「我的視圖」第一條 FR-002(a)。

---

## R-003 技術詞零容忍的測試手法

- **Decision**：建立常數 `FORBIDDEN_TOKENS = ("filter_trace", "allocation_trace", "qualified_set", "random_index", "exit_code")`
  與正則 `r"\brole\.\w+"` / `r"\btarget\.\w+"`；
  整合測試以 `assert NOT (token in response.text)` + `assert NOT re.search(...)` 驗證。
- **Rationale**：
  - 自動化的硬要求，比人工檢查 UI 文案可靠。
  - 將「禁用詞」集中於一處，未來擴充明確。
- **Alternatives considered**：
  - **白名單**（只允許某些詞）：太嚴格、難維護。
  - **人工 UX 審查**：不可重現，不適合自動化測試。

---

## R-004 路由放在既有 `match.py` 而非新增 `individual.py`

- **Decision**：兩個新端點 `GET /match/{record_id}/role/{role_id}` 與
  `GET /match/{record_id}/role/{role_id}/audit.json` 加在既有 `src/matcher/web/routes/match.py`。
- **Rationale**：
  - URL 前綴 `/match/` 已歸 match.py 管；同一前綴的端點放同一檔案匯入跳轉最少。
  - 本 feature 只加兩個端點，不到「另立路由檔」的門檻。
- **Alternatives considered**：
  - **新立 `routes/individual.py`**：對未來擴充更開放但本階段 YAGNI；若 3b 後續再加多個端點再切。

---

## R-005 admin 結果頁的「個別查詢連結」呈現

- **Decision**：在 `match_result.html` 成功模式下，於現有「下載稽核紀錄」按鈕之後，
  加一個 `<details>` 可摺疊區段；展開後顯示表格（姓名 / role_id / 連結）。
  不用 HTMX、不用 JS——`<details>/<summary>` 是原生 HTML 元素。
- **Rationale**：
  - `<details>` 無需 JS、語意清晰、瀏覽器原生支援。
  - 預設摺疊避免 admin 視圖被一長串連結佔據。
- **Alternatives considered**：
  - **HTMX hx-get partial swap**：複雜化無收益（資料已在 audit，無需 lazy load）。
  - **預設展開**：admin 已有分配表，連結列表二級重要，預設摺疊較佳。

---

## R-006 個別查詢頁的「未分配」原因解釋

- **Decision**：頁面分四種顯示：
  1. **被分配且資格集合內有抽中紀錄**：「您被分到 X」+ 抽籤步驟說明。
  2. **資格集合內有 target 但未被抽中（容量耗盡）**：「您原本有資格分到 Y、Z，但容量已被分配給其他人」。
  3. **資格集合為空**：「依規則判定，您不符合任何對象的條件」+ 列出每個對象 + failed_rule。
  4. **edge case**：assignment[role_id] 為 null 但資格集合非空——極少發生，列出原因為「資格集合非空但未進入分配步驟」（這實際上不會發生，allocate_m0 一律會嘗試，留作保險）。
- **Rationale**：
  - 對「為什麼沒分到」的不同情境給不同解釋——一刀切會誤導。
  - 解釋依資料推導，不需新計算。
- **Alternatives considered**：
  - **只說「未分配」不解釋**：違反 FR-002(c)「媒合過程說明」。

---

## R-007 個別查詢頁的可重現性（SC-005 bytewise）

- **Decision**：
  - 樣板渲染時**不**注入時間戳、當前 URL、session token 等非確定性內容。
  - 所有顯示資料皆從 audit（已凍結）取出。
  - 同一 record + role_id 兩次訪問必須 bytewise 相同。
- **Rationale**：與教訓 1「黃金檔比對是可重現性的最強驗證手段」一致。
- **Alternatives considered**：
  - **頁底加「上次更新時間」**：注入時間戳破壞可重現性，無收益。

---

## R-008 個別查詢專屬錯誤頁

- **Decision**：新增 `templates/individual_error.html`——用語比 `error_page.html` 更友善：
  「找不到該次媒合的紀錄」「您不在這次媒合的名單中」「該次媒合執行失敗，無個別查詢資料」，
  皆附「請聯絡發送連結的行政人員」建議；不顯示技術錯誤類別。
- **Rationale**：
  - error_page.html 顯示 `error.type` 與技術細節（給 admin），不適合一般教師。
  - FR-006 要求「明確繁中訊息」+ FR-003 技術詞零容忍。
- **Alternatives considered**：
  - **重用 error_page.html**：洩漏技術細節，違反 FR-003。

---

## R-009 個別 audit 子集下載格式

- **Decision**：
  - URL：`GET /match/{record_id}/role/{role_id}/audit.json`
  - Content-Type：`application/json; charset=utf-8`
  - Content-Disposition：`attachment; filename="<record_id>-<role_id>.individual.json"`
  - 序列化：`ensure_ascii=False, sort_keys=True, indent=2`（沿用 audit 風格）
- **Rationale**：與 admin 路徑的 audit 下載風格一致；可選 `sort_keys=True` 保證可重現性。
- **Alternatives considered**：
  - **YAML 格式**：人類可讀性高但 JSON 更通用。

---

## R-010 audit / match-record schema 不變

- **Decision**：本 feature 不引入任何 schema 升版；audit v1.2 與 match-record/1.0 保持不變。
  所有新功能皆從既有資料推導。
- **Rationale**：feature 為 read-only 視圖，無新資料需持久化；schema 不變是分層純度的證據。
- **Alternatives considered**：
  - **audit schema 加 `individual_view_metadata`**：YAGNI；個別查詢是「呈現視圖」而非「資料」。

---

## 已解決的 NEEDS CLARIFICATION 列表

本 plan 中無 NEEDS CLARIFICATION 標記；spec.md Assumptions 中標為「由 plan 決定」的項目皆於 R-001 ~ R-010 解決。

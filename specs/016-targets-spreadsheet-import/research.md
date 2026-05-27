# Research — 對象名單試算表匯入

## D1：對象載入器放哪 → 核心 data_import（重用既有 helper）

**Decision**：在 `data_import.py` 新增 `load_targets_csv(path, template)` 與
`load_targets_xlsx(path, template, sheet=None)`，回 `tuple[Target,...]`。
重用既有 `detect_csv_encoding`、`coerce_value`，新增小工具 `_resolve_target_headers`
（拿 spreadsheet 表頭對齊 `template.attributes.targets`，沿用 `resolve_header` 的別名/顯示名稱比對）。

**Rationale**：與 roster 匯入完全同類（編碼、表頭對齊、型別轉換），放 data_import 可被 CLI/Web 共用、
不重造解析輪子。屬「資料匯入」核心職責擴充（教訓 7）。

**Alternatives**：
- ❌ 在 web 層解析：會複製 data_import 的編碼/對齊/轉型邏輯，易漂移
- ❌ web 解析後轉成 YAML 再走旁檔：雙重轉換（CSV→Target→YAML→Target），醜

## D2：怎麼把「對象來自另一個檔」接進既有 roster 載入 → load_roster_csv 加 targets=

**Decision**：`load_roster_csv(path, template, targets=None)` /
`load_roster_xlsx(..., targets=None)`：targets 給定 → 直接用（跳過 `_load_targets` 旁檔）；
None → 沿用旁檔（現狀）。Web 雙檔路徑：
`load_roster_csv(roles_file, tpl, targets=load_targets_csv(targets_file, tpl))`。

**Rationale**：最小、向後相容的參數新增；CLI 與既有測試完全不受影響（預設 None = 旁檔）。
角色由角色檔載、對象由對象檔載，直接組 Roster，無雙重轉換。

## D3：對象檔 id 省略 → 自動編號（US3）

**Decision**：對象檔無 id 欄（或某列 id 空）→ 自動產生唯一 id `T001…`（避開檔內已有 id）。
與 UI 填名單的 `assemble_targets_yaml_bytes` 自動編號規則一致。

**Rationale**：一致體驗；對象 id 多半無語意，強迫填徒增門檻。

## D4：對象檔「容量」處理

**Decision**：容量為對象必要欄。缺容量欄 → `RosterColumnMismatch`（明確訊息：對象檔需要「容量」欄）。
某列容量空白 → 該列視為未填、略過（與 UI 填一致）。容量 < 1 → 沿用既有 ValueError。

**Rationale**：對象沒有容量無意義；錯誤要可操作。

## D5：對象試算表 vs .targets.yaml 旁檔同時出現 → 上傳檔優先

**Decision**：Web 路徑只看「上傳的對象檔」；不再用旁檔（web 本來也沒有真旁檔，是 feature 014 用 tmp 寫的）。
CLI 路徑維持旁檔。兩者不會在同一次請求衝突。

**Rationale**：Web 與 CLI 是兩條獨立路徑；各自單一來源，無歧義。

## D6：第二個上傳欄位接受哪些格式 → 依副檔名分派 CSV/Excel/YAML

**Decision**：`/match/run` 第二檔（對象）依副檔名：`.csv`→load_targets_csv、`.xlsx`→load_targets_xlsx、
`.yaml/.yml`→既有 YAML 解析（沿用 feature 014 寫 tmp 旁檔的相容路徑）。

**Rationale**：對使用者就是「對象名單檔」，CSV/Excel 為主、YAML 仍可（進階）；副檔名分派簡單可靠。

## D7：動態範例怎麼產生 → web 純函式 + 端點，依 schema 即時組

**Decision**：`src/matcher/web/example_gen.py` 提供
`role_example_bytes(tpl, fmt)` / `target_example_bytes(tpl, fmt)`（fmt: csv|xlsx）：
- 表頭 = 屬性的中文顯示名稱（角色：編號 + 各角色屬性；對象：編號 + 容量 + 各對象屬性）
- 一列「格式提示」：int→「（數字）」、list_str→「（多筆用分號隔開）」、str→「（文字）」
端點 `/templates/{id}/example/roles.csv` 等（需登入、套可見性檢查）。

**Rationale**：動態 = 涵蓋自訂範本、永遠與範本同步、免維護靜態檔。CSV 用 csv 標準庫、xlsx 用 openpyxl（既有）。
不保證「下載原樣可跑」（規則合格值無法對任意範本自動產生）——範例定位是「教格式」，spec US2 已界定。

## D8：上傳頁連結

**Decision**：上傳區改成兩個檔案欄位（角色名單、對象名單），各自旁邊放
「下載範例（CSV / Excel）」連結指向 D7 端點（帶目前選定的 template_id，用 Alpine 綁）。
移除舊的 GitHub raw 範例連結，統一改為動態端點。

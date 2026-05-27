# Contract — 對象匯入 + 動態範例

## 核心 load_targets_csv / load_targets_xlsx
- 輸入：對象試算表路徑 + template
- 輸出：`tuple[Target,...]`，結構同 `_load_targets`（YAML）
- 錯誤：缺容量欄→RosterColumnMismatch；重複 id→DuplicateIdentity；容量<1→ValueError
- id 欄缺 → 自動 T001…（避開已有）

## 核心 load_roster_csv/xlsx（簽名擴充）
- 新增 `targets=None`；給定 tuple 則用之、跳過旁檔；None 維持旁檔（向後相容）
- 既有呼叫端（CLI、測試）行為不變

## POST /match/run（Web）
- 第二檔 `targets_file`（選填，CSV/Excel/YAML）：
  - .csv → load_targets_csv；.xlsx → load_targets_xlsx；.yaml/.yml → 既有 YAML（寫 tmp 旁檔）
  - 提供 → 以 targets= 注入 load_roster_csv
- 未提供對象來源 → 友善錯誤（提示上傳對象試算表或改用直接填名單）

## 範例端點（Web，登入 + 可見性）
- `GET /templates/{id}/example/roles.csv|.xlsx`
- `GET /templates/{id}/example/targets.csv|.xlsx`
- 回 attachment；表頭=屬性中文顯示名（角色:編號+屬性；對象:編號+容量+屬性）+ 一列格式提示
- 內建/公開/自己的範本可下載；他人私有 → 403

## 不變
- CLI `.targets.yaml` 旁檔；audit schema；Target/Roster 結構

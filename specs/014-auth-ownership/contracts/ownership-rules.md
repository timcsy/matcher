# Contract — 擁有者過濾 / 存取規則

## 寫入時綁擁有者
- `POST /match/run`、`/match/run-from-form`、`/match/preferences` 成功建立 record → `record.owner = current_user`
- `POST /templates/save` → 範本版本 `owner = current_user`，`visibility = private`（除非表單指定 public）

## 讀取時守門
- `GET /match/{id}` 及其子資源（audit、pdf、舊個別路徑）：
  - 未登入 → 302 `/login`
  - 登入但 `record.owner != current_user` → 403「無權查看這筆配對」
- `GET /matches`：`MatchStore.list(owner=current_user)` 只回自己的

## 範本可見性
- 列表 `GET /templates`：顯示 `owner==me` ∪ `visibility==public` ∪ 內建
- `GET /templates/{id}`：
  - 內建 / public / 自己的 → 可看
  - 別人的 private → 403
- `GET /templates/{id}/edit`、`POST /templates/save`（既有 id）：
  - 僅 owner 可編輯；非 owner（含看得到的 public）→ 403，但可「複製為自訂版本」（fork，新 owner=me）
- 內建範本：不可編輯（既有行為），可複製

## 切換可見性
- 範本詳細頁（owner）提供「設為公開 / 設為私有」切換 → 需登入 + owner + CSRF

## 403 呈現
- 友善繁中訊息（「這筆資料不屬於你」之類），非技術碼；不洩漏資源是否存在的細節以外的資訊

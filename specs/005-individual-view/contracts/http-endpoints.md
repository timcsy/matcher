# HTTP Endpoints Contract — 個別查詢視圖

**Branch**: `005-individual-view` | **Date**: 2026-05-23

新增 2 個端點；修改 1 個既有頁面。

---

## 新增：`GET /match/{record_id}/role/{role_id}`

個別查詢頁——某角色在某次媒合中的「我的視圖」。

- **路徑參數**：
  - `record_id`：媒合紀錄 id
  - `role_id`：角色 id（依名單中宣告，不分大小寫）

### 行為

1. `MatchStore.get(record_id)` 取出紀錄
2. 若 `record.status == "failed"` → 404 + `individual_error.html`「該次媒合執行失敗」
3. 若 `role_id` 不在 `record.audit.roster_snapshot.roles` → 404 + `individual_error.html`「您不在這次媒合的名單中」
4. 否則 → 200 + `individual_view.html` 渲染：
   - 「您的基本資訊」
   - 「您的分配結果」（或「未分配」+ 原因）
   - 「媒合過程說明」（規則判定 + 抽籤步驟）
   - 連結：「下載我的稽核紀錄」

### 退出碼

| HTTP | 情境 |
|---|---|
| 200 | 成功 |
| 404 | record 不存在 / role_id 不在名單 / status=failed |

### 訊息範例（404）

```text
找不到該次媒合的紀錄。
建議：請確認連結是否正確、或聯絡發送連結的行政人員。
```

```text
您不在這次媒合的名單中。
建議：請確認連結是否正確、或聯絡發送連結的行政人員。
```

```text
該次媒合執行失敗，無個別查詢資料。
建議：請聯絡發送連結的行政人員了解詳情。
```

---

## 新增：`GET /match/{record_id}/role/{role_id}/audit.json`

下載個別 audit 子集（JSON）。

### 行為

1. 同上 1-3
2. `subset = build_individual_audit_subset(record.audit, role_id)`
3. 回應 200 + JSON content + attachment headers

### 回應 Headers

```text
Content-Type: application/json; charset=utf-8
Content-Disposition: attachment; filename="<record_id>-<role_id>.individual.json"
```

### 回應 Body 結構

見 `individual-audit-schema.json`。

### 退出碼

| HTTP | 情境 |
|---|---|
| 200 | 成功（含正確 attachment headers） |
| 404 | 同上三種情境 |

---

## 修改：`GET /match/{record_id}`（admin 結果頁）

### 變更

- 成功模式下，現有「下載稽核紀錄」按鈕之後新增可摺疊區段 `<details>`：
  ```html
  <details>
    <summary>個別查詢連結（共 N 位）</summary>
    <table>
      <thead><tr><th>姓名</th><th>角色 id</th><th>個別查詢</th></tr></thead>
      <tbody>
        <!-- 每位 role 一列 -->
      </tbody>
    </table>
  </details>
  ```
- 失敗模式下**不顯示**此區段。

### 不變式

- 失敗紀錄的結果頁不含「個別查詢連結」字串
- 成功紀錄的結果頁含 N 個 `/match/<id>/role/<rid>` 連結，N = 該記錄的角色數

---

## 不變式（契約測試會驗證）

- **技術詞零容忍（SC-002）**：個別查詢頁的 HTML response 不含 FORBIDDEN_TECHNICAL_TOKENS 任一字串、不匹配 `role.\w+` / `target.\w+` 之任一模式。
- **可重現性（SC-005）**：同 record + role_id 訪問兩次，response.text 完全相同。
- **個別 subset 完整性（SC-006）**：`filter_trace_subset` 條目數 = audit.filter_trace 中該 role 的條目數。
- **既有 admin 視圖不變（FR-011）**：新增的 `<details>` 區段不破壞既有 142 測試（其中 admin 結果頁測試應為「含某字串」斷言，與新增區段共存）。

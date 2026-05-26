# Contract — 空集合診斷

## 核心：rejection_summary

```
rejection_summary(trace: list[dict], ruleset: Ruleset) -> dict
```
- 輸入：filter_trace（每組含 role_id/target_id/matched_rules）+ ruleset
- 輸出：`{total_pairs, rule_stats: {rule_id: 失敗組數}, culprit: rule_id|None}`
- 純函式、無副作用；rule_stats 涵蓋每條規則（即使 0）

## 核心：QualifiedSetEmpty 攜帶診斷
- raise 前 `filter_qualified` 設好 `err.trace / err.rule_stats / err.culprit / err.total_pairs`
- `exit_code` 維持 10
- 既有 `str(err)` 訊息不變（向後相容）

## CLI：matcher run 空集合
- 退出碼 10（不變）
- stderr 多印：`最可能原因：<元兇規則描述>（卡住 N/總 M 組）` + 各規則計數行
- 無技術 token

## Web：POST /match/run-from-form（UI 填）空集合
- 不存失敗 record；改回填名單頁（HTTP 200，沿用 _render_fill_form）
- 頁面含：使用者剛填內容（prefill）+ 診斷紅字（元兇規則描述 + 卡住組數）

## Web：POST /match/run（CSV 上傳）空集合
- 存失敗 record，error.diagnostic 帶 {total_pairs, rule_stats, culprit, rules}
- 結果頁失敗分支渲染診斷（人類可讀、無技術 token）

## 不變契約
- 成功配對 audit schema：完全不變
- 「部分角色有資格」：不 raise，行為不變
- 退出碼表：10 不變

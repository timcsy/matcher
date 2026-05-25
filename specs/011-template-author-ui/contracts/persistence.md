# Persistence Contract — feature 011

自訂模板的檔案系統佈局與 TemplateRegistry 掃描契約。

## 檔案佈局

```
data/templates/
├── .gitkeep                          # 保留目錄入 git
├── <template-id>/                    # 每個自訂模板一個目錄
│   ├── v1.yaml                       # 第一版（POST /templates/save 首次）
│   ├── v2.yaml                       # 第二版（編輯後）
│   └── v<N>.yaml                     # 第 N 版
└── ...
```

**檔案規則**：
- 目錄名為 template id；限定 regex `^[a-z0-9-]+$`
- 檔名嚴格匹配 `v\d+\.yaml`（不接受 `v01.yaml`、`v1.yml` 等）
- 檔內為合法 YAML（可被 `parse_template` 接受）
- 檔內的 `id` 欄位 MUST 與目錄名一致；不一致 → 載入時拒絕（明確錯誤）

## TemplateRegistry 行為

**啟動掃描**：
1. 掃 builtin（既有 `_scan`）—— `matcher.templates.builtin` 套件資源
2. 掃 custom（新 `_scan_custom_dir`）—— `data/templates/<id>/v<N>.yaml`
   - 對每個 id，取 max(N) 版本進主 cache（提供給 `get(id)`）
   - 所有版本進 `_custom_versions[id][N]`（提供給 `get_version(id, n)`）

**id 衝突解決**（執行時）：
- builtin id == custom id：**不應發生**（save 階段已拒絕）；萬一發生（手動放檔），優先 builtin + log warning

**儲存契約**：
- `save_custom(tpl_dict) -> (id, version)`：
  1. 驗證 tpl_dict 為合法 `parse_template` 輸入；失敗 raise ValueError
  2. 檢查 id 不在 builtin；失敗 raise ValueError "模板 id 已存在於內建模板..."
  3. 計算 next_version = max(現有 v\d+.yaml) + 1，或 1（首次）
  4. 寫 `data/templates/<id>/v<N>.yaml`；目錄不存在自動建立
  5. 呼叫 `invalidate()` 重新掃描
  6. 返回 (id, version)

**Invalidate**：
- 清 `_cache` 與 `_custom_versions`，重執行 `_scan()` + `_scan_custom_dir()`
- 啟動 + 每次 POST /templates/save 後 + 測試手動觸發

## 不變的契約

- 既有 `TemplateRegistry.list_ids()`, `get()`, `has()` 簽名與行為不變（cache 內容變多，但介面同）
- 既有 `parse_template`, `Template`, `parse_template_yaml`：完全不動

## 跨進程考量

- 多進程 uvicorn 部署：每個 worker 各自一份 TemplateRegistry instance；某 worker 寫入後其他 worker 不會立即看見 → 需重啟或下次掃描才生效
- **本 feature 範圍**：單進程 reload mode 開發場景；多 worker 部署為階段 5 K8s 範疇，不在此 feature 處理

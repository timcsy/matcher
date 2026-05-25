# Contract — Audit Schema v1.4

## 版本標示

| 欄位 | 值 |
|---|---|
| `schema_version` | `"1.4"`（從 `"1.3"` 升） |

## 與 v1.3 的差異

唯一差異：`template_snapshot` 物件**移除** `default_targets` 鍵。

### v1.3（舊）

```jsonc
"template_snapshot": {
  "schema_version": "1.0",
  "id": "teacher-class",
  ...
  "default_targets": [             // ← 在 v1.4 移除
    {"id": "C01", "capacity": 2, "attributes": {...}},
    ...
  ],
  ...
}
```

### v1.4（新）

```jsonc
"template_snapshot": {
  "schema_version": "1.0",
  "id": "teacher-class",
  ...
  // default_targets 不再出現
  ...
}
```

## 不變部分

- `roster_snapshot.targets`：本次配對使用的對象資料，**仍包含完整 id/capacity/attributes**（從旁檔或 UI 載入）
- 所有 trace（filter_trace、allocation_trace）：不變
- `import_metadata`：不變
- 其餘鍵：不變

## Compatibility

| 讀取方 | v1.4 audit | v1.3 audit |
|---|---|---|
| 本專案 viewer / 個別查詢頁 | ✅ 正常（不存取 default_targets） | ✅ 正常 |
| PDF 報告（feature 010）| ✅ 從 roster_snapshot.targets 取資料 | ✅ |
| 第三方讀者讀 `template_snapshot.default_targets` | ❌ KeyError；應改讀 `roster_snapshot.targets` | ✅ |

## 升版時機

- `audit.py::build_audit` 寫出時固定 `schema_version="1.4"`
- 不主動轉換舊紀錄；舊 v1.3 紀錄保留原 schema_version 字串

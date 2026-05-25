# CLI Report Contract — feature 010

新增子指令 `matcher report`；既有指令（run / template / serve）不變。

## 用法

```bash
matcher report --audit <FILE> --output <PDF> [--role-id <ID>] [--record-id <ID>] [--created-at <ISO>]
```

## 旗標

| 旗標 | 必填 | 預設 | 說明 |
|---|---|---|---|
| `--audit` | ✓ | — | audit JSON 檔路徑 |
| `--output` | ✓ | — | PDF 輸出檔路徑 |
| `--role-id` | – | None | 缺省 → admin 版；有值 → individual 版 |
| `--record-id` | – | （從 audit 推導）| 顯示用 |
| `--created-at` | – | （audit.generated_at or 當下）| ISO-8601 字串 |

## Exit codes

| Code | 意義 |
|---|---|
| 0 | 成功 |
| 2 | Typer 預設 — 旗標缺失或型別錯誤 |
| 50 | WeasyPrint / 字體不可用（友善訊息含安裝指引） |
| 51 | audit JSON 解析失敗 / 缺核心欄位（含「missing key」訊息） |
| 52 | --role-id 不在 audit.roster_snapshot.roles |

## 輸出

- 成功 stdout：「PDF 已寫入 <path>」
- 失敗 stderr：明確繁中錯誤；exit code 對應上表

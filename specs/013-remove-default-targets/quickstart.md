# Quickstart — 驗證 feature 013

實作完成後，依序執行以下情境驗證所有 SC 達標。

## SC-001 全測試綠

```bash
uv run pytest -q
```

預期：所有測試 pass（包含 feature 013 新增的 audit schema 斷言、UI 對象段必顯測試、CLI 缺旁檔報錯測試）。

## SC-002 範本 YAML 不含 default_targets

```bash
! grep -q "^default_targets:" src/matcher/templates/builtin/teacher-class.yaml
! grep -q "^default_targets:" src/matcher/templates/builtin/study-group.yaml
```

預期：兩個 grep 都找不到 → 兩個 `!` 反轉成 0（成功）。

## SC-003 audit v1.4 不含 default_targets

```bash
uv run matcher run \
  --template teacher-class \
  --roster-csv examples/teacher-class/roster.csv \
  --seed 2026 \
  --output /tmp/audit.json

# 驗證
python -c "
import json
a = json.load(open('/tmp/audit.json'))
assert a['schema_version'] == '1.4', a['schema_version']
assert 'default_targets' not in a['template_snapshot'], 'should not exist'
assert len(a['roster_snapshot']['targets']) == 5
print('SC-003 ✅')
"
```

## SC-004 UI 對象段永遠顯示

```bash
uv run uvicorn matcher.web.app:create_app --factory --port 8765 &
sleep 1
curl -s http://127.0.0.1:8765/match/new/fill?template_id=teacher-class | grep -q "對象清單"
echo "SC-004 ✅"
kill %1
```

## SC-005 CLI 缺旁檔報錯

```bash
# 用一個沒有對應 .targets.yaml 的 CSV
cp examples/teacher-class/roster.csv /tmp/no-sidecar.csv
uv run matcher run --template teacher-class --roster-csv /tmp/no-sidecar.csv --seed 2026
# 預期：退出碼非零；stderr 含 "targets.yaml"
echo "exit code: $?"
```

## E2E 瀏覽器（手動）

1. `uv run uvicorn matcher.web.app:create_app --factory --port 8765`
2. 訪問 `http://127.0.0.1:8765/match/new`
3. 選 teacher-class → 點「✏️ 直接填名單」→ 應看到「② 對象清單」段（新行為，feature 012 時是隱藏）
4. 填 3 老師 + 3 班級 + seed → 提交
5. 跳結果頁，audit.json 下載驗證 `schema_version: "1.4"`

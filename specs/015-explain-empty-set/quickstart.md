# Quickstart — 驗證 feature 015

## SC-001 空集合指出元兇（teacher-class 填中文以外的特色）

用 teacher-class，班級 feature 填一個不在 {雙語,stem,藝術} 的值（如「雙語班」），跑 M0：
- Web 失敗頁 / 回填頁應顯示「最可能原因：R003 班級特色…（卡住 N/N 組）」
- 不含技術 token

## SC-002 無技術 token

掃失敗頁與 CLI 輸出，不得出現 filter_trace / qualified_set / role. / target. 等。

## SC-003 UI 失敗保留輸入

UI 填名單觸發空集合 → 回到填名單頁、剛填的角色/對象都還在 + 診斷紅字。

## SC-004 照修正後說明填得過

teacher-class 班級 feature 填「雙語」→ R003 通過；配上符合 R001/R002 的老師 → 配對成功。

```bash
uv run matcher run --template teacher-class \
  --roster-csv examples/teacher-class/roster.csv --seed 2026 --output /tmp/a.json
# 預期 exit 0、成功（examples 已對齊中文 feature）
```

## SC-004b CLI 空集合診斷

```bash
# 造一個 feature 全填錯的 CSV + sidecar → 跑 → 退出碼 10 + stderr 含「R003」與描述
uv run matcher run --template teacher-class --roster-csv /tmp/bad.csv --seed 1; echo "exit=$?"
```

## SC-005 全測試綠 + 成功 audit 不變

```bash
uv run pytest -q
# 核心可解釋性擴充守門：filter/errors/cli 之外不應動其他核心
git diff main --name-only -- 'src/matcher' ':!src/matcher/web' ':!src/matcher/templates' \
  | grep -v -E 'filter|errors|cli' || echo "核心僅動 filter/errors/cli ✅"
```

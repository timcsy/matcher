# Quickstart：核心媒合引擎

**Branch**: `001-core-allocator` | **Date**: 2026-05-22

最小可跑示範：以 `examples/teacher-class/` 內附的範例執行一次媒合，並驗證稽核紀錄逐位元組相同。

---

## 前置條件

- Python 3.11 或 3.12
- 已安裝本套件（開發中以 `pip install -e .` 安裝）

---

## 1. 執行基準場景

```bash
matcher run \
  --rules    examples/teacher-class/rules.yaml \
  --roster   examples/teacher-class/roster.yaml \
  --seed     123456 \
  --output   /tmp/audit.json
```

預期 stdout 末段：

```text
=== 完成 ===
稽核紀錄已寫入：/tmp/audit.json
```

預期 exit code：`0`。

---

## 2. 驗證可重現性

連跑兩次並比對：

```bash
matcher run --rules examples/teacher-class/rules.yaml \
            --roster examples/teacher-class/roster.yaml \
            --seed 123456 --output /tmp/a.json

matcher run --rules examples/teacher-class/rules.yaml \
            --roster examples/teacher-class/roster.yaml \
            --seed 123456 --output /tmp/b.json

diff /tmp/a.json /tmp/b.json && echo "✅ 完全相同"
```

預期：`diff` 無輸出、印出 `✅ 完全相同`。對應 SC-001。

---

## 3. 驗證錯誤路徑（邊界情境）

### 缺少 seed

```bash
matcher run --rules ... --roster ...
# 退出碼 13；訊息含「seed 未提供」與「建議：以 --seed 提供整數種子」
```

### 提供 preferences

```bash
matcher run --rules ... --roster ... --seed 123456 \
            --preferences examples/teacher-class/preferences.yaml
# 退出碼 17；訊息含「此機制（M0 純抽籤）不接受志願輸入」與
#                  「志願序機制（M1 / M2）將於階段 4 加入」
```

---

## 4. 只執行過濾階段

```bash
matcher filter \
  --rules  examples/teacher-class/rules.yaml \
  --roster examples/teacher-class/roster.yaml \
  --output /tmp/qualified.json
```

對應 FR-005「外部呼叫者可只執行過濾」。輸出僅含 `qualified_set` 與 `filter_trace`，無 `allocation_trace` 與 `assignment`。

---

## 5. 跑測試

```bash
pytest                      # 全部測試
pytest tests/unit           # 單元
pytest tests/integration    # 整合（含 CLI 端對端）
pytest tests/integration/test_reproducibility.py -v
```

預期：全部通過。`test_reproducibility.py` 包含 SC-001 的黃金檔比對。

---

## 6. Library 用法（不透過 CLI）

```python
from matcher import run_match, MatcherInput, load_ruleset_yaml, load_roster_yaml

result = run_match(MatcherInput(
    ruleset=load_ruleset_yaml("examples/teacher-class/rules.yaml"),
    roster=load_roster_yaml("examples/teacher-class/roster.yaml"),
    seed=123456,
    preferences=None,
    mechanism="M0",
))

print(result.assignment)       # role_id → target_id
print(result.qualified_set)    # role_id → [target_id, ...]
# result.audit 為完整 AuditRecord（dataclass）
```

---

## 對應 spec.md 章節

| Quickstart 步驟 | 對應 Acceptance / SC |
|---|---|
| 1. 執行基準場景 | US1 Acceptance #1、SC-002 |
| 2. 驗證可重現性 | US1 Acceptance #2、SC-001 |
| 3. 缺 seed | Edge Cases、SC-004 |
| 3. 提供 preferences | US3 Acceptance #1、SC-006 |
| 4. 只執行過濾 | FR-005 |
| 5. 跑測試 | SC-007 |
| 6. Library 用法 | FR-005、Project Type（library + CLI） |

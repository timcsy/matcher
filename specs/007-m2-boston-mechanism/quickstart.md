# Quickstart：M2 Boston 分配機制

**Branch**: `007-m2-boston-mechanism` | **Date**: 2026-05-24

---

## 前置條件

- Python 3.11+ 與 uv
- 已安裝本套件（無新依賴）

---

## 1. 用 M2 跑通研習分組

```bash
uv run matcher run \
  --template     study-group \
  --roster-csv   examples/study-group/roster-m1.csv \
  --seed         2026 \
  --mechanism    M2 \
  --output       /tmp/audit-m2.json
```

預期：

- exit 0
- stdout 含「=== 分配階段（M2 Boston 層級填滿）===」
- audit JSON 含 `mechanism: "M2"`、`schema_version: "1.3"`、`processing_order` 為角色 id 序列
- 每筆 `allocation_trace` 條目含 `tie_break_random_index`（M2 + 超額時為非 null）

---

## 2. 可重現性

```bash
uv run matcher run --template study-group --roster-csv examples/study-group/roster-m1.csv \
                   --seed 2026 --mechanism M2 --output /tmp/a.json
uv run matcher run --template study-group --roster-csv examples/study-group/roster-m1.csv \
                   --seed 2026 --mechanism M2 --output /tmp/b.json
diff /tmp/a.json /tmp/b.json && echo "✅ 完全相同"
```

---

## 3. M2 vs M1 對比

```bash
# 同 roster + 同 seed，跑 M1 與 M2
uv run matcher run --template study-group --roster-csv examples/study-group/roster-m1.csv \
                   --seed 2026 --mechanism M1 --output /tmp/m1.json
uv run matcher run --template study-group --roster-csv examples/study-group/roster-m1.csv \
                   --seed 2026 --mechanism M2 --output /tmp/m2.json

# 比對 assignment 與 preference_rank 分布
uv run python -c "
import json
m1 = json.load(open('/tmp/m1.json'))
m2 = json.load(open('/tmp/m2.json'))
print('M1 assignment:', m1['assignment'])
print('M2 assignment:', m2['assignment'])
print()
print('M1 preference_rank 分布:', [t.get('preference_rank') for t in m1['allocation_trace']])
print('M2 preference_rank 分布:', [t.get('preference_rank') for t in m2['allocation_trace']])
"
```

預期：M1 與 M2 的 assignment 可能不同；`preference_rank` 在 M2 通常偏低（多人拿到第 1 志願），M1 視處理順序而定。

---

## 4. M2 + 空 prefs → 拒絕

```bash
uv run matcher run --template study-group --roster examples/study-group/roster.yaml \
                   --seed 1 --mechanism M2
# 預期 exit 40
# 訊息含「M2 需要至少一位角色提供志願」
```

---

## 5. 不支援的機制

```bash
uv run matcher run --template study-group --roster-csv examples/study-group/roster-m1.csv \
                   --seed 1 --mechanism M3
# 預期 exit 2
# 訊息含「不支援的機制 `M3`」「支援：M0、M1、M2」
```

---

## 6. 向後相容驗證

```bash
# M0 既有路徑
uv run matcher run --rules examples/teacher-class/rules.yaml \
                   --roster examples/teacher-class/roster.yaml \
                   --seed 123456 --output /tmp/m0.json

# 檢查 tie_break_random_index 在 M0 路徑為 null
uv run python -c "
import json
d = json.load(open('/tmp/m0.json'))
assert d['schema_version'] == '1.3'
assert all(t.get('tie_break_random_index') is None for t in d['allocation_trace'])
print('✅ M0 路徑向後相容')
"
```

---

## 7. 跑測試

```bash
uv run pytest                                      # 全部（既有 188 + 新增 ≈ 12 = 200）
uv run pytest tests/unit/test_allocator_m2.py
uv run pytest tests/integration/test_cli_mechanism_m2.py
uv run pytest tests/integration/test_m2_reject.py
```

---

## 對應 spec.md 章節

| Quickstart 步驟 | 對應 Acceptance / SC |
|---|---|
| 1. M2 跑通 | US1、SC-002 |
| 2. 可重現性 | SC-001、SC-007 |
| 3. M1 vs M2 對比 | SC-008 |
| 4. M2 + 空 prefs 拒絕 | US2、SC-003 |
| 5. 不支援機制 | SC-006 |
| 6. M0 向後相容 | US3、SC-004、SC-005 |
| 7. 跑測試 | SC-009 |

# Quickstart：M1 RSD 分配機制

**Branch**: `006-m1-rsd-mechanism` | **Date**: 2026-05-23

---

## 前置條件

- Python 3.11+ 與 uv
- 已安裝本套件（`uv pip install -e ".[dev]"`，無新依賴）

---

## 1. 用 M1 跑通研習分組

```bash
uv run matcher run \
  --template     study-group \
  --roster-csv   examples/study-group/roster-m1.csv \
  --seed         2026 \
  --mechanism    M1 \
  --output       /tmp/audit-m1.json
```

預期：

- exit 0
- stdout 含「=== 分配階段（M1 RSD 隨機輪流挑）===」+「處理順序：S03 → S01 → ...」
- audit JSON 含 `mechanism: "M1"`、`schema_version: "1.3"`、`processing_order: [...]`
- 每筆 `allocation_trace` 條目含 `preference_rank`（整數或 null）

---

## 2. 驗證可重現性（SC-001）

```bash
uv run matcher run --template study-group --roster-csv examples/study-group/roster-m1.csv \
                   --seed 2026 --mechanism M1 --output /tmp/a.json

uv run matcher run --template study-group --roster-csv examples/study-group/roster-m1.csv \
                   --seed 2026 --mechanism M1 --output /tmp/b.json

diff /tmp/a.json /tmp/b.json && echo "✅ 完全相同"
```

預期：`diff` 無輸出。

---

## 3. 拒絕路徑（SC-003）：M1 + 全空 preferences

```bash
# 用既有 study-group/roster.yaml（所有 preferences 為空）
uv run matcher run --template study-group --roster examples/study-group/roster.yaml \
                   --seed 1 --mechanism M1
# 預期 exit 40
# 訊息含「M1 需要至少一位角色提供志願」「請至少為一位角色填入志願，或改用 --mechanism M0」
```

---

## 4. 向後相容（SC-005、SC-006）：M0 路徑完全不變

```bash
# 既有教師-班級命令（無 --mechanism，預設 M0）
uv run matcher run --rules examples/teacher-class/rules.yaml \
                   --roster examples/teacher-class/roster.yaml \
                   --seed 123456 --output /tmp/m0.json

# audit 中 processing_order 應為 null，preference_rank 在每筆 trace 應為 null
uv run python -c "
import json
d = json.load(open('/tmp/m0.json'))
assert d['schema_version'] == '1.3'
assert d['processing_order'] is None
assert all(t.get('preference_rank') is None for t in d['allocation_trace'])
print('✅ M0 路徑向後相容')
"
```

---

## 5. 不支援的機制值（SC-010）

```bash
uv run matcher run --template study-group --roster-csv examples/study-group/roster-m1.csv \
                   --seed 1 --mechanism M5
# 預期 exit 2
# 訊息含「不支援的機制 `M5`」「支援：M0、M1」
```

---

## 6. preferences 規範化（SC-008）

```bash
# 構造一份 preferences 含「重複 + 資格外」項目的 CSV
uv run python -c "
with open('/tmp/dirty.csv','w',encoding='utf-8') as f:
    f.write('id,姓名,年級,志願組別\n')
    f.write('S01,小明,5,G2;G2;G99;G1\n')  # G2 重複、G99 不在資格集合
    f.write('S02,小華,4,\n')
"
# 配合 roster-m1.targets.yaml（同既有 study-group targets）
cp examples/study-group/roster-m1.targets.yaml /tmp/dirty.targets.yaml

uv run matcher run --template study-group --roster-csv /tmp/dirty.csv \
                   --seed 1 --mechanism M1 --output /tmp/dirty.json

# 檢查 S01 的 preferred_order 應為 ["G2","G1"]（去重 + 移除 G99）
uv run python -c "
import json
d = json.load(open('/tmp/dirty.json'))
for t in d['allocation_trace']:
    if t['role_id'] == 'S01':
        print('S01 preferred_order:', t.get('preferred_order'))
        assert t.get('preferred_order') == ['G2', 'G1']
print('✅ 規範化通過')
"
```

---

## 7. 跑測試

```bash
uv run pytest                                       # 全部測試（既有 169 + 新增 ≈ 13 = 182）
uv run pytest tests/unit/test_allocator_m1.py
uv run pytest tests/unit/test_pipeline_dispatch.py
uv run pytest tests/integration/test_cli_mechanism_m1.py
uv run pytest tests/integration/test_m0_backward_compat.py
```

---

## 對應 spec.md 章節

| Quickstart 步驟 | 對應 Acceptance / SC |
|---|---|
| 1. M1 跑通 | US1、SC-002 |
| 2. 可重現性 | SC-001、SC-007 |
| 3. 拒絕路徑 | US2、SC-003 |
| 4. M0 向後相容 | US3、SC-005、SC-006 |
| 5. 不支援機制值 | SC-010 |
| 6. preferences 規範化 | SC-008 |
| 7. 跑測試 | SC-009 |

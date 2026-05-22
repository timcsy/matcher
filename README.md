# matcher

依角色屬性媒合對象的工具——以可解釋規則篩出資格集合、以可驗證隨機程序在集合內公平分配，並產出可重現的稽核紀錄。

## 快速開始

### 安裝

需要 Python 3.11+ 與 [uv](https://github.com/astral-sh/uv)：

```bash
uv venv --python 3.11
uv pip install -e ".[dev]"
```

### 執行基準場景（教師-班級配對）

```bash
uv run matcher run \
  --rules  examples/teacher-class/rules.yaml \
  --roster examples/teacher-class/roster.yaml \
  --seed   123456 \
  --output audit.json
```

預期輸出：規則摘要、資格集合大小、最終配對、稽核檔已寫入。

### 驗證可重現性

同樣輸入跑兩次，稽核紀錄應逐位元組相同：

```bash
uv run matcher run --rules examples/teacher-class/rules.yaml \
                   --roster examples/teacher-class/roster.yaml \
                   --seed 123456 --output /tmp/a.json
uv run matcher run --rules examples/teacher-class/rules.yaml \
                   --roster examples/teacher-class/roster.yaml \
                   --seed 123456 --output /tmp/b.json
diff /tmp/a.json /tmp/b.json && echo "✅ 完全相同"
```

### 只跑過濾階段

```bash
uv run matcher filter \
  --rules  examples/teacher-class/rules.yaml \
  --roster examples/teacher-class/roster.yaml \
  --output qualified.json
```

### 跑測試

```bash
uv run pytest
```

## 概念

- **角色（Role）**：待媒合的個體（如老師）。
- **對象（Target）**：被分配的容器，具屬性與容量上限（如班級）。
- **規則（Rule）**：定義「哪些角色屬性 vs. 對象屬性符合資格」，附自然語言說明。
- **資格集合（Qualified Set）**：規則篩選後的合法配對候選。
- **分配機制**：本階段支援 M0 純抽籤；M1（RSD）/ M2（Boston）將於階段 4 加入。
- **稽核紀錄**：包含規則快照、名單快照、資格集合、seed、每步隨機決策、最終配對。

## 文件

- 規格：`specs/001-core-allocator/spec.md`
- 計畫：`specs/001-core-allocator/plan.md`
- 任務清單：`specs/001-core-allocator/tasks.md`
- 知識文件：`knowledge/{principles,vision,experience}.md`
- Constitution：`.specify/memory/constitution.md`

## 範圍邊界

matcher 不是 scheduler、不是 voter、也不是動態調整器。多輪排程、投票選舉、事後重新洗牌請開立獨立專案；詳見 `knowledge/vision.md`「範圍邊界」段。

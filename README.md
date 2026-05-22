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

### 使用內建模板

```bash
# 列出所有內建模板
uv run matcher template list

# 檢視單一模板
uv run matcher template show teacher-class

# 用內建模板執行媒合
uv run matcher run --template teacher-class \
                   --roster examples/teacher-class/roster.yaml \
                   --seed 123456 --output audit.json

# 匯出模板為檔案以分享
uv run matcher template export teacher-class --output tc.yaml

# 用匯出的檔案執行（取代內建 id）
uv run matcher run --template-file tc.yaml \
                   --roster examples/teacher-class/roster.yaml \
                   --seed 123456 --output audit.json
```

「研習分組」模板含 `preferences_schema`，但本階段 M0 機制下，若名單帶有非空 preferences → 拒絕並提示等待階段 4。

### Web UI

啟動本地 server：

```bash
uv run matcher serve
# 預設綁定 127.0.0.1:8000（不對外）
# 開發模式：uv run matcher serve --reload
# 對外（LAN）：uv run matcher serve --host 0.0.0.0
```

開啟瀏覽器訪問 <http://127.0.0.1:8000/>，可：

- **新建媒合**：4 步驟向導（選模板 → 上傳 CSV/Excel → 設定種子 → 執行）
- **模板瀏覽**：查看內建模板的完整規則與屬性 schema
- **過去媒合**：查看歷次媒合紀錄、重新下載 audit

媒合紀錄持久化於 `data/matches/<id>.json`（已加入 `.gitignore`）。

### 從 CSV / Excel 匯入名單

支援 CSV（UTF-8 / UTF-8-BOM / CP950 三種編碼自動偵測）與 Excel（.xlsx）：

```bash
# CSV 匯入（中文表頭、自動對齊到模板的 aliases）
uv run matcher run --template teacher-class \
                   --roster-csv examples/teacher-class/roster.csv \
                   --seed 123456 --output audit.json

# Excel 匯入（單一工作表自動使用）
uv run matcher run --template study-group \
                   --roster-xlsx examples/study-group/roster.xlsx \
                   --seed 2026 --output audit.json

# Excel 多工作表 → 須指定 --sheet
uv run matcher run --template study-group \
                   --roster-xlsx examples/study-group/roster-multi.xlsx \
                   --sheet "報名表" \
                   --seed 2026 --output audit.json
```

格式要求：

- 第一列為表頭；模板宣告的 `aliases` 自動對齊中文表頭（例「姓名」→ `name`）。
- 可選 `id`／`編號` 欄位指定角色 id；否則自動生成 `R001`、`R002`...
- list 型別欄位以分號 `;` 分隔（例：`G1;G2;G3`）。
- targets 由旁檔 `<basename>.targets.yaml` 提供。

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

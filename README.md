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

### 撰寫自訂模板（含 AI 助手 prompt）

需要做新場景的模板？可參考 [`docs/template-authoring-guide.md`](docs/template-authoring-guide.md)——一份完整的 YAML schema 規格 + 6 個 expr 算子說明 + 2 個 worked example + Self-check checklist。

**最省力的做法**：把整份指南複製貼給 Claude / ChatGPT，描述你的場景（角色、對象、規則），AI 會依規格產出 YAML。指南最後 §13 附有現成的 prompt 填空模板。

產出的 YAML 可用 `--template-file my.yaml` 跑 CLI，或放到 `src/matcher/templates/builtin/` 後重啟讓 Web UI 也看得到。

### Web UI

啟動本地 server：

```bash
uv run matcher serve
# 預設綁定 127.0.0.1:8000（不對外）
# 開發模式：uv run matcher serve --reload
# 對外（LAN）：uv run matcher serve --host 0.0.0.0
```

開啟瀏覽器訪問 <http://127.0.0.1:8000/>，可：

- **新建媒合**：4 步驟向導（選模板 → 上傳 CSV/Excel → 設定種子 → 選分配機制 M0/M1/M2 → 執行）；若模板含志願 schema 且名單未填志願，自動跳到「填志願表單」中介頁——每位角色 N 個下拉、無需手工準備 CSV preferences 欄；M1/M2 結果頁顯示處理順序與每位的志願排名，個別查詢頁顯示「您被分到第 N 志願」或「由公平抽籤分到」
- **模板瀏覽**：查看內建模板的完整規則與屬性 schema
- **過去媒合**：查看歷次媒合紀錄、重新下載 audit

媒合紀錄持久化於 `data/matches/<id>.json`（已加入 `.gitignore`）。

#### PDF 報告匯出

結果頁與個別查詢頁皆提供「下載 PDF 報告」按鈕；CLI 亦可用 `matcher report --audit <file> --output <pdf> [--role-id <id>]` 從 audit JSON 產出。

需安裝 WeasyPrint 系統依賴：
- macOS：`brew install pango glib`（並設 `export DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib`）
- Debian/Ubuntu：`apt install libpango-1.0-0 libcairo2 libgobject-2.0-0 libharfbuzz0b`

未安裝時 Web PDF 端點回 503、CLI report 指令 exit 50；既有功能（媒合、結果頁、audit JSON 下載）不受影響。

#### 個別查詢視圖

媒合完成後，admin 結果頁底部「個別查詢連結」區段列出每位被媒合者的專屬 URL（`/match/<record_id>/role/<role_id>`）。行政可將這些連結個別發送給對應的當事人；當事人開啟後可獨立查看：

- 自己的基本資訊
- 是否被分配（被分到哪個對象 / 或為什麼未分配）
- 依模板規則的判定說明（用語面向一般教師，避免技術名詞）
- 下載個人稽核紀錄 JSON（`/match/<record_id>/role/<role_id>/audit.json`）

頁面為純讀取——同一 URL 多次訪問結果完全一致。

### 分配機制

```bash
# M0 純抽籤（預設；無偏好）
uv run matcher run --template teacher-class \
                   --roster examples/teacher-class/roster.yaml \
                   --seed 123456 --output audit.json

# M1 RSD 隨機輪流挑（含志願；先隨機洗牌處理順序、再逐位選最高未滿志願）
uv run matcher run --template study-group \
                   --roster-csv examples/study-group/roster-m1.csv \
                   --seed 2026 --mechanism M1 --output audit-m1.json
```

「研習分組」範例 `roster-m1.csv` 含每位學生的志願組別（分號分隔），可用 M1 跑出含「處理順序 + 每人志願滿足度」的稽核紀錄。

```bash
# M2 Boston 層級填滿（先全塞第 1 志願超額抽籤、剩餘退到第 2 志願以此類推）
uv run matcher run --template study-group \
                   --roster-csv examples/study-group/roster-m1.csv \
                   --seed 2026 --mechanism M2 --output audit-m2.json
```

- 規則：M0 不接受任何 preferences；M1 / M2 至少需一位提供 preferences。
- M1 / M2 + 全空 preferences → 拒絕（exit 40）；建議改用 M0。
- M1 vs M2：兩者皆為「公平的志願序」但定義不同——M1 強調「處理順序公平」，M2 強調「同層級內滿足度最大化」。同 roster + 同 seed 下兩者結果可能不同。

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
- **分配機制**：支援 M0 純抽籤、M1 RSD（隨機輪流挑）、M2 Boston（層級填滿）；CLI 與 Web 三入口皆可選。
- **稽核紀錄**：包含規則快照、名單快照、資格集合、seed、每步隨機決策、最終配對。

## 文件

- 規格：`specs/001-core-allocator/spec.md`
- 計畫：`specs/001-core-allocator/plan.md`
- 任務清單：`specs/001-core-allocator/tasks.md`
- 知識文件：`knowledge/{principles,vision,experience}.md`
- Constitution：`.specify/memory/constitution.md`

## 範圍邊界

matcher 不是 scheduler、不是 voter、也不是動態調整器。多輪排程、投票選舉、事後重新洗牌請開立獨立專案；詳見 `knowledge/vision.md`「範圍邊界」段。

# matcher 模板撰寫指南（給 AI 助手用）

> **使用方式**：把整份文件複製貼給 Claude / ChatGPT / Gemini 等 AI，附上你的需求（如「請幫我做一個社團報名的模板，3 個社團依年級與興趣分配」），AI 就會依此規格生成或修改 YAML。

---

## 0. 給 AI 的參與者設定

你是 matcher 模板 YAML 的作者助手。matcher 是一個校務媒合工具，把「參與者」（如老師、學生）依規則篩出資格集合後，以公平程序（純抽籤 / 隨機輪流挑 / 層級填滿）分配到「對象」（如班級、研習組別）。模板是一份 YAML 檔，定義屬性 schema、規則、（可選）志願結構與預設對象清單。

請依本文件的 schema 嚴格生成 / 修改 YAML：不要發明新欄位、不要新增不在 §3 的 expr 運算子、所有 description 用繁體中文。產出後跑 §10 的 self-check。

---

## 1. 模板檔案頂層結構

```yaml
schema_version: "1.0"            # 固定字串，必填
id: my-template                   # 必填，kebab-case，全域唯一（不可與內建 teacher-class / study-group 衝突）
name: "我的媒合場景"              # 必填，UI 上顯示用
description: "一句話說明這個模板做什麼"  # 必填

attributes:                       # 必填，宣告參與者與對象有哪些屬性欄位
  participants: [...]                    # see §2
  targets: [...]                  # see §2

rules: [...]                      # 必填，至少 1 條規則；see §3

preferences_schema:               # 可選；只有要支援 M1/M2 志願序機制時才需要
  max_choices: 3
  required: false
  description: "..."

default_targets: [...]            # 可選但強烈建議；省掉使用者每次上傳對象旁檔；see §4

ui_fields: [...]                  # 可選；目前 Web UI 未使用此欄，但仍可宣告以供未來使用
report_fields: [...]              # 可選；目前 PDF 未使用此欄
```

**重要**：
- `id` 必須是合法檔案名片段（純小寫英數 + 連字號），不可含中文 / 空白 / 底線
- `schema_version` 目前只支援 `"1.0"`；未來升版本會在這裡聲明
- 所有頂層欄位的層級不可錯置（如把 `default_targets` 放進 `attributes` 內會解析失敗）

---

## 2. attributes 段：宣告屬性 schema

每個屬性宣告是一個 dict，含以下欄位：

```yaml
- key: speciality                # 必填，英文蛇形（snake_case），程式碼用的「正式名」
  type: str                      # 必填；可選 "str" | "int" | "list_str"
  required: true                 # 必填；true → CSV 對應欄位不可空白
  description: "老師專業科目"     # 必填，繁中；UI / PDF / 規則描述替換時用此名顯示
  aliases: ["專業科目", "專業"]   # 可選；CSV / Excel 表頭可寫的「人類友善名」（通常中文）
```

**型別說明**：
- `str`：任意字串（中文、英文、數字均可）
- `int`：整數；CSV 中 "5" 會自動轉 int
- `list_str`：字串列表；在 CSV 中以分號 `;` 分隔（如 `國文;數學`）

**規則**：
- `key` 必須與 `attributes.{participants,targets}[i].key` 集合內唯一（同段 participants 內 key 不可重複；不同段如 participants vs targets 可同名）
- `aliases` 不需含 `key` 本身（系統會自動接受 `key`）
- `aliases` 建議放最常用的中文表頭（學校行政會看的那些）

**完整範例**：

```yaml
attributes:
  participants:
    - key: name
      type: str
      required: true
      description: "學生姓名"
      aliases: ["姓名"]
    - key: grade
      type: int
      required: true
      description: "年級"
      aliases: ["年級"]
    - key: interests
      type: list_str
      required: false
      description: "興趣清單"
      aliases: ["興趣", "個人興趣"]
  targets:
    - key: name
      type: str
      required: true
      description: "社團名稱"
      aliases: ["社團名稱", "社團"]
    - key: required_interest
      type: str
      required: true
      description: "社團主題（必須與學生興趣之一相符）"
      aliases: ["主題", "社團主題"]
    - key: min_grade
      type: int
      required: true
      description: "最低年級限制"
      aliases: ["最低年級"]
```

---

## 3. rules 段：寫媒合規則

每條規則是一個 dict：

```yaml
- id: R001                                  # 必填，建議 R001 / R002 ... 編號
  description: "老師的專業必須在班級需要科目中"  # 必填，繁中；可含 participant.X / target.X token（UI 會替換為「您的 X」「該對象的 X」）
  expr: <expression>                         # 必填，see below
```

`expr` 是一個 AST（抽象語法樹），可遞迴組合。**只支援以下 6 個葉節點 + 3 個邏輯節點**——不可發明其他算子。

### 3.1 葉節點（比較算子）

#### `eq`：屬性等於某值

```yaml
expr:
  eq:
    field: participant.speciality      # 必填，必須 participant.X 或 target.X 前綴
    value: "數學"                # 必填，要等於的值（str / int 皆可）
```

#### `in`：屬性屬於某集合

```yaml
expr:
  in:
    field: target.feature
    set: ["bilingual", "stem", "arts"]   # 必填，list
```

#### `ge`：屬性 ≥ 某數值（只用於 int）

```yaml
expr:
  ge:
    field: participant.seniority
    value: 3                              # 必填，int
```

#### `le`：屬性 ≤ 某數值（只用於 int）

```yaml
expr:
  le:
    field: participant.grade
    value: 6
```

#### `participant_in_target_field`：參與者屬性出現在對象的列表屬性中

最常用的「能不能教這個班」「能不能去這個組」判斷。

```yaml
expr:
  participant_in_target_field:
    participant_field: speciality            # 必填，僅 key 名（不加 participant. 前綴）
    target_field: required_subjects    # 必填，對象的 list_str 欄位的 key 名
```

語義：`participant.speciality 在 target.required_subjects 列表中`。如果 target_field 不是 list（例如是 str），會退化為 `participant.speciality == target.required_subjects`。

### 3.2 邏輯節點

#### `and`：所有子規則皆通過

```yaml
expr:
  and:
    - ge:
        field: participant.grade
        value: 4
    - in:
        field: target.topic
        set: ["program", "science"]
```

#### `or`：任一子規則通過

```yaml
expr:
  or:
    - eq:
        field: participant.is_vip
        value: true
    - ge:
        field: participant.seniority
        value: 10
```

#### `not`：子規則不通過

```yaml
expr:
  not:
    eq:
      field: target.is_full
      value: true
```

### 3.3 規則設計三條鐵律

1. **規則只決定「資格」，不決定「優先序」**。給特定人更高機率被抽中 → 直接違反 matcher 哲學。若需「優先權」，應化為過濾條件（例：「特教老師有 2 倍籤」→「特教老師只可被分到特教班」）。
2. **每條規則都要能用一句中文寫清楚**——`description` 就是這句話。若一條規則的 description 你寫不清楚，就拆成多條。
3. **規則之間是 AND 關係**——所有規則都要通過才有資格。如果你想要「OR」，把它寫進單一規則的 `expr.or` 內。

---

## 4. default_targets 段：預設對象清單（強烈建議）

如果你提供 `default_targets`，使用者上傳名單時就**不需要另外上傳對象旁檔**（Web UI 完全免上傳；CLI 也是）。

```yaml
default_targets:
  - id: C01                       # 必填；唯一；short 字串（如 C01 / G1 / 數字編號皆可）
    capacity: 3                   # 必填；整數 ≥ 1；表示這個對象最多能分到幾個參與者
    attributes:                   # 必填；必須涵蓋 attributes.targets 中所有 required: true 的 key
      name: "三年甲班"
      required_subjects: ["國文", "數學"]
      feature: "bilingual"
```

**規則**：
- 每個 default_target 的 `attributes` 必須涵蓋你在 `attributes.targets` 宣告為 `required: true` 的所有 key
- `id` 在 default_targets 內不可重複
- `capacity` 是上限：媒合過程中該對象最多被分到 capacity 個參與者；超過會被擋下
- 對象屬性的 list_str 欄位用 YAML list 寫（如上面的 `required_subjects: ["國文", "數學"]`）

---

## 5. preferences_schema 段：志願序機制（M1/M2 用）

只有當你的場景**允許/需要當事人填志願**（如學生選研習組、老師選社團指導等）才宣告。M0 純抽籤模式下，宣告 schema 但所有 prefs 為空也可以跑。

```yaml
preferences_schema:
  max_choices: 3              # 必填；每位參與者最多填幾個志願（合理範圍 1..5）
  required: false             # 必填；通常 false（容許部分人不填）
  description: "每位學生可填 1~3 個志願組別"  # 必填
```

當宣告了 schema：
- Web UI 在使用者選 M1/M2 + 上傳「未含志願欄」CSV 時，會自動跳到填志願頁面
- 也可以在 CSV 中加「志願組別」（aliases 由 import 推導）欄，內容以 `;` 分隔 target id：`G1;G2;G3`
- 沒宣告 schema 而選 M1/M2 會直接被拒絕

---

## 6. CSV / Excel 表頭對齊規則

使用者匯入名單時，CSV / Excel 第一列為表頭。matcher 會嘗試把每個表頭欄對齊到 `attributes.participants[i].key` 或 `attributes.participants[i].aliases` 中的任一個。

**強制規則**：
- 第一欄必須是 `id` 欄（aliases 可寫 `id`、`編號`、`學號`、`教師編號` 等）；若沒這欄系統會自動生成 `R001`、`R002`...
- 所有 `required: true` 的 attribute key 都必須有對應的表頭欄（用 key 或任一 alias）
- 表頭可以中英文混用；對齊不分大小寫但會分中英文（「name」≠「姓名」除非有 alias）

**範例**：給定模板的 attributes.participants:
```yaml
- {key: name, aliases: [姓名, 學生姓名]}
- {key: grade, aliases: [年級]}
- {key: interests, aliases: [興趣]}
```

CSV 可以寫：
```
id,姓名,年級,興趣
S01,小明,5,程式;音樂
S02,小華,4,自然
```

或：
```
編號,name,grade,interests
S01,小明,5,程式;音樂
```

兩者等價。

**list_str 在 CSV**：以 `;` 分隔（不是 `,` 也不是 `、`）

---

## 7. ui_fields / report_fields（目前選填，未強制使用）

這兩段目前 matcher 程式碼**尚未實作渲染**——你可以宣告，但 Web UI 不會自動依此渲染表單；PDF 也不會依此產報告欄位。

未來如要實作，schema 大致是：

```yaml
ui_fields:
  - key: name
    label: "姓名"
    type: text                # text / number / select / multiselect
    required: true
    placeholder: "請輸入..."   # 可選
    options: ["國文", "英文"]   # type=select/multiselect 時必填
    help: "提示文字"           # 可選

report_fields:
  - key: student_name
    label: "學生姓名"
    source: "roster_snapshot.participants[].attributes.name"   # JSONPath-ish
```

**現階段建議**：可宣告以利未來擴充，但不要花太多時間設計——目前不影響功能。

---

## 8. 完整範例 1：簡單版（社團報名）

場景：3 個社團（程式社、音樂社、美術社）依年級和興趣分配學生。

```yaml
schema_version: "1.0"
id: club-signup
name: "社團報名"
description: "依年級與興趣分配學生到社團"

attributes:
  participants:
    - key: name
      type: str
      required: true
      description: "學生姓名"
      aliases: ["姓名"]
    - key: grade
      type: int
      required: true
      description: "年級"
      aliases: ["年級"]
    - key: interest
      type: str
      required: true
      description: "興趣（單選）"
      aliases: ["興趣"]
  targets:
    - key: name
      type: str
      required: true
      description: "社團名稱"
      aliases: ["社團名稱"]
    - key: topic
      type: str
      required: true
      description: "社團主題"
      aliases: ["主題"]
    - key: min_grade
      type: int
      required: true
      description: "最低年級"
      aliases: ["最低年級"]

rules:
  - id: R001
    description: "學生年級必須 ≥ 社團最低年級"
    expr:
      ge:
        field: participant.grade
        value: 1     # 注意：這裡只能放固定值；若要 participant.grade ≥ target.min_grade 需要不同寫法（目前 matcher 不支援欄位對欄位比較，請用 §11「現階段限制」中的 workaround）
  - id: R002
    description: "學生興趣必須與社團主題相同"
    expr:
      participant_in_target_field:
        participant_field: interest
        target_field: topic

preferences_schema:
  max_choices: 3
  required: false
  description: "每位學生可填 1~3 個社團志願"

default_targets:
  - id: C1
    capacity: 5
    attributes: {name: "程式社", topic: "program", min_grade: 4}
  - id: C2
    capacity: 5
    attributes: {name: "音樂社", topic: "music", min_grade: 3}
  - id: C3
    capacity: 4
    attributes: {name: "美術社", topic: "art", min_grade: 3}
```

---

## 9. 完整範例 2：進階版（含 and/or/not 與 list_str）

場景：課輔師生媒合，老師需有對應專業 + 年資 ≥ 2 年 + 不是新進老師（is_intern=false）。

```yaml
schema_version: "1.0"
id: tutoring-match
name: "課輔師生媒合"
description: "依專業與年資配對課輔老師到學生需求"

attributes:
  participants:
    - key: name
      type: str
      required: true
      description: "老師姓名"
      aliases: ["姓名"]
    - key: specialities
      type: list_str
      required: true
      description: "可教科目"
      aliases: ["可教科目", "專長科目"]
    - key: seniority
      type: int
      required: true
      description: "年資"
      aliases: ["年資"]
    - key: is_intern
      type: str            # 注意：matcher 目前無 bool 型別；用 str 配 eq: "true"/"false" 取代
      required: true
      description: "是否實習老師"
      aliases: ["實習"]
  targets:
    - key: name
      type: str
      required: true
      description: "學生姓名"
      aliases: ["學生姓名"]
    - key: subject
      type: str
      required: true
      description: "需要輔導的科目"
      aliases: ["科目"]

rules:
  - id: R001
    description: "老師可教科目必須包含學生所需科目"
    expr:
      participant_in_target_field:
        participant_field: specialities
        target_field: subject
  - id: R002
    description: "老師年資至少 2 年，且不是實習老師"
    expr:
      and:
        - ge:
            field: participant.seniority
            value: 2
        - not:
            eq:
              field: participant.is_intern
              value: "true"
```

注意此例**無 default_targets**：學生名單會由使用者上傳一份「targets 旁檔」（與 roster.csv 同目錄、檔名 `roster.targets.yaml`）。

---

## 10. Self-check checklist（AI 產出後請逐項驗證）

- [ ] `schema_version` 是 `"1.0"`（字串，含引號）
- [ ] `id` 是純小寫英數 + 連字號，全域唯一
- [ ] `attributes.participants` 與 `attributes.targets` 至少各有 1 個 entry
- [ ] 每個 attribute 含 4 個必填欄位：`key`、`type`、`required`、`description`
- [ ] 所有 `description` 為繁體中文
- [ ] `rules` 至少 1 條
- [ ] 每條規則的 `expr` 使用的 field 都正確指向 `participant.X` 或 `target.X`，且 X 已在 `attributes` 宣告
- [ ] `expr` 只使用以下算子：`eq`、`in`、`ge`、`le`、`participant_in_target_field`、`and`、`or`、`not`（不可發明）
- [ ] 若有 `preferences_schema`：`max_choices` 是 1..5 的整數
- [ ] 若有 `default_targets`：每個 entry 的 `attributes` 涵蓋所有 required: true 的 target key
- [ ] 整份 YAML 用 2 空白縮排，無 tab
- [ ] 整份 YAML 可被 `yaml.safe_load` 解析（無語法錯）

---

## 11. 現階段限制與 workaround

matcher 目前 **不支援** 的能力：

| 想做的事 | 為什麼不行 | Workaround |
|---|---|---|
| 欄位對欄位比較（如 `participant.grade >= target.min_grade`）| `ge`/`le` 的 value 必須為常數 | 改用 `participant_in_target_field` + 把 `target.min_grade` 改為 list_str 列出所有允許年級（如 `["4","5","6"]`） |
| bool 型別 | 沒有 bool；只有 str/int/list_str | 用 `str` 存 `"true"/"false"`，用 `eq` 比對字串 |
| 浮點數 / 日期 | 沒有 float / date 型別 | 用 int（如「年資」直接用整數年）|
| 加權抽籤 / 優先序 | 違反 matcher 哲學（見 §3.3） | 改寫為過濾規則 |
| 規則動態生效（依名單變化）| 規則是靜態定義 | 不支援 |

---

## 12. 把模板放入 matcher 系統

兩種方式：

**A. 一次性使用（CLI 路徑）**：
```bash
uv run matcher run --template-file /path/to/my-template.yaml \
  --roster-csv students.csv --seed 1 --output audit.json
```

**B. 永久註冊（Web UI 也用得到）**：
把 YAML 放到 `src/matcher/templates/builtin/<your-id>.yaml`，重啟 server，`/match/new` 的模板下拉就會出現。

---

## 13. 給使用者的 prompt 模板

把以下對話貼給 AI（如 Claude / ChatGPT）：

> 請依附帶的「matcher 模板撰寫指南」幫我做一份模板：
>
> **場景**：______________________
> **參與者**（如老師、學生）：______，需要的屬性：______
> **對象**（如班級、組別、活動）：______，需要的屬性：______
> **預設對象清單**：______（如「3 個社團，各容納 5 人」；如不確定可寫「請建議」）
> **資格規則**：______（用自然語言列）
> **是否需要填志願**：______（是 / 否；若是，最多幾個）
>
> 請產出完整 YAML，並依指南 §10 self-check checklist 自我驗證後，告訴我有沒有需要再確認的地方。

---

**文件版本**：對齊 matcher schema v1.0（截至 2026-05-25，含 feature 010 PDF 匯出能力）
**程式碼來源**：`src/matcher/rules.py`（expr 算子）、`src/matcher/template_loader.py`（YAML 解析）、`src/matcher/templates/builtin/*.yaml`（內建範本）

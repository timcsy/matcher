# Quickstart — feature 011 模板創作工具

10 步驟端到端驗收：簡單模式建立 + 進階模式 AI prompt + 編輯 + 版本歷史 + Fork + 再執行。

## 0. 啟動

```bash
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib \
  uv run uvicorn matcher.web.app:app --port 8417 --reload
```

開 `http://localhost:8417/templates` → 應看到「+ 新增模板」prominent 按鈕。

## 1. 簡單模式建立（US1）

1. 點「+ 新增模板」→ 跳 `/templates/new`，預設簡單模式頁籤
2. 場景樣板下拉選「社團報名」→ 表單預填 3 屬性 + 2 規則 + 3 default_targets
3. 改 id 為 `my-club`、name 為「我的社團報名」
4. 點「驗證」→ 顯示 ✅ summary（3 屬性、2 規則、3 預設對象）
5. 點「儲存」→ 跳 `/templates/my-club`，顯示新模板資訊與版本歷史「v1 - 2026-05-25 ...」

## 2. 用自訂模板跑媒合

1. 訪問 `/match/new` → 模板下拉應出現「我的社團報名（my-club）」
2. 選此模板 + 上傳 `examples/study-group/roster-m1.csv`（或自製名單）+ seed=2026 + 機制 M0
3. 跑通 → 結果頁正常顯示分配表

## 3. 重啟驗證（SC-003）

```bash
pkill -f "uvicorn matcher.web.app"
sleep 1
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib uv run uvicorn matcher.web.app:app --port 8417 --reload &
```

開 `/templates` → `my-club` 仍在列表中 ✓

## 4. 編輯模板（US3）

1. 訪問 `/templates/my-club` → 點「編輯」
2. `/templates/my-club/edit` 載入 v1 內容
3. 改某條規則 description → 點儲存
4. 跳 `/templates/my-club` → 版本歷史段顯示 v1 + v2

## 5. 查看舊版本

1. 點版本歷史中的「v1 查看」連結
2. 顯示 v1 完整 YAML 內容（純文字）；確認與 v2 不同

## 6. 進階模式 + AI prompt（US2）

1. `/templates/new` → 切到「進階模式」頁籤
2. 填空：場景=「老師輪值」、角色=「老師（資歷年數、可值科目）」、對象=「值班時段（科目需求）」、規則=「資歷 ≥ 1 年且科目對得上」、志願=「否」
3. 點「複製完整 Prompt」→ JS 顯示「已複製」
4. 開 ChatGPT / Claude → 貼 → AI 回 YAML
5. 把 YAML 貼回頁面下半文字框
6. 點「驗證」→ ✅
7. 點「儲存」→ 完成

## 7. Fork 內建模板（US3 子場景）

1. 訪問 `/templates/teacher-class`（內建）
2. **無**「編輯」按鈕；有「Fork 為自訂模板」按鈕 ✓
3. 點 Fork → 跳 `/templates/new?fork=teacher-class`
4. 表單預填 teacher-class 全部內容；id 預填為 `teacher-class-fork`
5. 改 id 為 `teacher-class-custom` → 改規則 → 儲存

## 8. 以此版本再執行（US4）

1. 訪問 `/matches` → 點任一過去媒合的 record
2. 結果頁底部應有「以此模板版本再執行」按鈕
3. 點擊 → 跳 `/match/new?template_snapshot=<rid>` → 顯示「已預載 audit 中的模板版本」提示
4. 改 seed → 跑新一次媒合 → 結果使用 audit 中的 template snapshot 而非當前模板

## 9. 內建模板不可覆蓋（SC-005）

1. `/templates/new` 簡單模式 → 改 id 為 `teacher-class`（內建 id）
2. 點儲存 → 收到 409 錯誤「模板 id 已存在於內建模板，不可覆蓋；請改名或選擇 Fork」 ✓

## 10. 自動化測試

```bash
uv run pytest -q
```

預期：既有 281 + 新增 ≥ 15 全綠（預期 ≥ 296）。

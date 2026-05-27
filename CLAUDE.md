# matcher Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-05-27

## Active Technologies
- Python 3.11+（沿用階段 1） + Typer、PyYAML、pytest（沿用，無新增） (002-template-system)
- 內建模板存於套件資源 `src/matcher/templates/builtin/*.yaml`；自訂模板由使用者提供路徑 (002-template-system)
- Python 3.11+（沿用） + Typer、PyYAML、pytest（沿用）+ **openpyxl ≥ 3.1**（新增，用於 .xlsx） (003-data-import)
- 無持久化（沿用） (003-data-import)
- Python 3.11+（沿用） + 沿用（Typer、PyYAML、pytest、openpyxl）+ **新增 fastapi ≥ 0.110、uvicorn[standard] ≥ 0.27、jinja2 ≥ 3.1、python-multipart ≥ 0.0.9** (004-web-ui-main)
- `data/matches/` 下純檔案系統 JSON（每次媒合一檔）；無資料庫 (004-web-ui-main)
- Python 3.11+（沿用） + 沿用（無新增）；本 feature 僅在 `matcher.web` 套件內加程式碼 (005-individual-view)
- 無新增（從既有 `data/matches/*.json` 讀） (005-individual-view)
- Python 3.11+（沿用） + 沿用（fastapi、uvicorn[standard]、jinja2、python-multipart、PyYAML、openpyxl、Typer、pytest、httpx[dev]）——**無新增** (008-web-mechanism-prefs)
- `data/matches/` 純 JSON（沿用）；無資料庫 (008-web-mechanism-prefs)
- Python 3.11+（沿用） + 沿用（fastapi、uvicorn[standard]、jinja2、python-multipart、PyYAML、openpyxl、Typer、pytest、httpx[dev]）——**無新增** (009-web-preferences-form)
- `data/matches/` 純 JSON（沿用）；無資料庫；**填志願頁中介狀態不持久化**（hidden inputs 攜帶） (009-web-preferences-form)
- Python 3.11+（沿用） + 沿用 + **新增 weasyprint ≥ 60.0**（含 cssselect2、tinycss2、Pyphen 等遞移依賴皆純 Python；系統需 libpango-1.0、libcairo、harfbuzz） (010-audit-pdf-export)
- 沿用 `data/matches/` 純 JSON；字體檔靜態於 `src/matcher/web/static/fonts/`（OFL 授權） (010-audit-pdf-export)
- Python 3.11+（沿用） + 沿用（fastapi、uvicorn[standard]、jinja2、python-multipart、PyYAML、openpyxl、Typer、pytest、httpx[dev]、weasyprint）——**無新增** (011-template-author-ui)
- 沿用 `data/matches/` + 新增 `data/templates/<id>/v<N>.yaml`（同檔案系統風格，無 DB） (011-template-author-ui)
- Python 3.11+（沿用） + 沿用（fastapi、uvicorn、jinja2、python-multipart、PyYAML、openpyxl、Typer、pytest、httpx[dev]、weasyprint）+ Tailwind Play CDN + Alpine.js（CDN，無 build）——**無新增** (012-web-roster-form)
- 沿用 `data/matches/` + `data/templates/`；UI 填的名單**不持久化**（in-memory CSV bytes 走既有路徑） (012-web-roster-form)
- Python 3.11（沿用；映像基底 `python:3.11-slim-bookworm`） + 沿用（fastapi、uvicorn[standard]、jinja2、weasyprint、authlib、itsdangerous、PyYAML、openpyxl、Typer）；環境以 **uv** 安裝（沿用工具鏈） (020-k8s-deploy)
- 純檔案系統 `data/`（match 紀錄 JSON + 範本 YAML），掛在 **PVC**（k3s local-path 動態供應）；無 DB (020-k8s-deploy)

- Python 3.11+ + Typer（CLI）、PyYAML（YAML 解析）、pytest（測試）；不額外引入 schema / validation 套件，所有結構化驗證在 `rules.py` / `roster.py` 內以純 Python 完成 (001-core-allocator)

## Project Structure

```text
src/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python 3.11+: Follow standard conventions

## Recent Changes
- 020-k8s-deploy: Added Python 3.11（沿用；映像基底 `python:3.11-slim-bookworm`） + 沿用（fastapi、uvicorn[standard]、jinja2、weasyprint、authlib、itsdangerous、PyYAML、openpyxl、Typer）；環境以 **uv** 安裝（沿用工具鏈）
- 012-web-roster-form: Added Python 3.11+（沿用） + 沿用（fastapi、uvicorn、jinja2、python-multipart、PyYAML、openpyxl、Typer、pytest、httpx[dev]、weasyprint）+ Tailwind Play CDN + Alpine.js（CDN，無 build）——**無新增**
- 011-template-author-ui: Added Python 3.11+（沿用） + 沿用（fastapi、uvicorn[standard]、jinja2、python-multipart、PyYAML、openpyxl、Typer、pytest、httpx[dev]、weasyprint）——**無新增**


<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->

# matcher Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-05-24

## Active Technologies
- Python 3.11+（沿用階段 1） + Typer、PyYAML、pytest（沿用，無新增） (002-template-system)
- 內建模板存於套件資源 `src/matcher/templates/builtin/*.yaml`；自訂模板由使用者提供路徑 (002-template-system)
- Python 3.11+（沿用） + Typer、PyYAML、pytest（沿用）+ **openpyxl ≥ 3.1**（新增，用於 .xlsx） (003-data-import)
- 無持久化（沿用） (003-data-import)
- Python 3.11+（沿用） + 沿用（Typer、PyYAML、pytest、openpyxl）+ **新增 fastapi ≥ 0.110、uvicorn[standard] ≥ 0.27、jinja2 ≥ 3.1、python-multipart ≥ 0.0.9** (004-web-ui-main)
- `data/matches/` 下純檔案系統 JSON（每次媒合一檔）；無資料庫 (004-web-ui-main)
- Python 3.11+（沿用） + 沿用（無新增）；本 feature 僅在 `matcher.web` 套件內加程式碼 (005-individual-view)
- 無新增（從既有 `data/matches/*.json` 讀） (005-individual-view)

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
- 007-m2-boston-mechanism: Added Python 3.11+（沿用） + 沿用（無新增）
- 006-m1-rsd-mechanism: Added Python 3.11+（沿用） + 沿用（無新增）
- 005-individual-view: Added Python 3.11+（沿用） + 沿用（無新增）；本 feature 僅在 `matcher.web` 套件內加程式碼


<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->

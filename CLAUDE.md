# matcher Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-05-22

## Active Technologies
- Python 3.11+（沿用階段 1） + Typer、PyYAML、pytest（沿用，無新增） (002-template-system)
- 內建模板存於套件資源 `src/matcher/templates/builtin/*.yaml`；自訂模板由使用者提供路徑 (002-template-system)
- Python 3.11+（沿用） + Typer、PyYAML、pytest（沿用）+ **openpyxl ≥ 3.1**（新增，用於 .xlsx） (003-data-import)
- 無持久化（沿用） (003-data-import)

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
- 003-data-import: Added Python 3.11+（沿用） + Typer、PyYAML、pytest（沿用）+ **openpyxl ≥ 3.1**（新增，用於 .xlsx）
- 002-template-system: Added Python 3.11+（沿用階段 1） + Typer、PyYAML、pytest（沿用，無新增）

- 001-core-allocator: Added Python 3.11+ + Typer（CLI）、PyYAML（YAML 解析）、pytest（測試）；不額外引入 schema / validation 套件，所有結構化驗證在 `rules.py` / `roster.py` 內以純 Python 完成

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->

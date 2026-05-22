# Research: 核心媒合引擎技術選型

**Branch**: `001-core-allocator` | **Date**: 2026-05-22

本文件記錄 Phase 0 的所有技術選型理由。每項決策以「決策 / 理由 / 替代方案」三段式記錄。

---

## R-001 程式語言：Python 3.11+

- **Decision**：Python 3.11+
- **Rationale**：
  - CLI 與 TDD 開發速度最快；pytest 生態成熟，與 constitution「TDD」原則契合度最高。
  - YAML/JSON 解析、命令列、結構化錯誤皆有成熟標準做法。
  - 標準函式庫的 `random.Random(seed)` 自 Python 3.2 起對 Mersenne Twister 演算法做出穩定承諾，跨版本可重現（限本研究中採用的呼叫模式：僅用 `randrange`，不使用 `shuffle`／`sample`／`choices`）。
  - 學校行政情境下未來 Web UI 採 FastAPI + 前端框架是常見且輕量的組合，與本階段選擇相容。
- **Alternatives considered**：
  - **TypeScript/Node**：與未來 Web UI 共享語言；但 seedable RNG 必須依賴第三方套件（如 `seedrandom`）且跨平台一致性需自行驗證。
  - **Go**：單一 binary 部署最簡，K8s 友好；但測試風格與 TDD 流程較不流暢、Web UI 仍需另選前端框架，整體節省有限。
  - **Rust**：對本階段而言過度工程，違反「簡潔優先」。

---

## R-002 隨機性：`random.Random(seed)` + 顯式 Fisher–Yates

- **Decision**：使用 `random.Random(seed)` 作為唯一 RNG 來源，洗牌邏輯顯式實作 Fisher–Yates，僅以 `randrange(n)` 取樣，**不使用** `random.shuffle`、`random.sample`、`random.choices`。
- **Rationale**：
  - CPython 對 Mersenne Twister 的 `randrange` 行為承諾跨版本穩定（自 3.2 起）。
  - `random.shuffle` 等高階方法在歷史上有過實作細節變動（例如 3.11 移除 `random` 參數），顯式 Fisher–Yates 可避免這類風險。
  - 顯式洗牌使「每一步隨機決策」能逐步寫入稽核紀錄（對應 FR-008f）。
- **Alternatives considered**：
  - **自實作 PCG / xoshiro**：可移植性更強，但對本階段是 over-engineering，違反「簡潔優先」。
  - **直接用 `random.shuffle`**：簡短但無法逐步紀錄、且高階方法的跨版本承諾較弱。

---

## R-003 CLI 框架：Typer

- **Decision**：Typer
- **Rationale**：
  - 以 type hint 為主，API 簡潔；自動產生 `--help`。
  - 與 pytest 整合容易，`CliRunner` 可直接做端對端測試。
  - 依賴鏈小（內含 Click，再無其他大型依賴）。
- **Alternatives considered**：
  - **argparse**（stdlib）：無外部依賴，但對結構化命令、子命令、自動文件較為繁瑣。
  - **Click**（Typer 底層）：與 Typer 相同特性但 API 較古老。

---

## R-004 YAML 解析：PyYAML

- **Decision**：PyYAML（以 `yaml.safe_load`）
- **Rationale**：
  - 最廣為使用、文件齊全；本階段不需要保留註解的 round-trip 能力。
  - 用 `safe_load` 避免任意 Python 物件構造的安全風險。
- **Alternatives considered**：
  - **ruamel.yaml**：保留註解、適合 round-trip；本階段只讀不寫，無此需求。

---

## R-005 規則表達式：自訂簡易 AST

- **Decision**：在 `rules.py` 內以純 Python 實作一個小型 AST（`Eq`、`In`、`Ge`、`Le`、`And`、`Or`、`Not`），規則來源於 YAML 後遞迴解析為 AST 並評估。
- **Rationale**：
  - 表達能力對齊 FR-013（等值、邏輯、範圍/集合），且為閉集合，不允許任意 Python 程式碼，保證可解釋。
  - 不引入 DSL 解析器（如 `lark`、`pyparsing`），符合「簡潔優先」。
- **Alternatives considered**：
  - **嵌入 Python `eval`**：能力過強且不可解釋，違反原則 1。
  - **JSONLogic / CEL**：依賴外部規格與套件；對本階段過度複雜。

---

## R-006 稽核紀錄格式：JSON

- **Decision**：稽核紀錄以 JSON 序列化，使用 `json.dumps(..., ensure_ascii=False, sort_keys=True, indent=2)`。
- **Rationale**：
  - 廣為機讀、可被任何工具 diff／重播。
  - `sort_keys=True` 保證跨平台逐位元組相同（SC-001）。
  - `ensure_ascii=False` 保留繁中可讀性（FR-014）。
- **Alternatives considered**：
  - **YAML 輸出**：可讀性更高，但跨平台序列化字串穩定性不如 JSON。
  - **二進位（msgpack / cbor）**：無 diff 友好性、違反「可稽核」精神。

---

## R-007 錯誤策略：明確類別 + 結構化退出碼

- **Decision**：以一組 Exception 子類（`QualifiedSetEmpty`、`CapacityShortage`、`RuleContradiction`、`EmptyRoster`、`DuplicateIdentity`、`UnknownAttribute`、`SeedMissing`、`PreferencesNotSupported`）對應 FR-011；CLI 入口將其攔截並以**不同非零退出碼**搭配繁中訊息退出。
- **Rationale**：
  - 與原則 V「結構化錯誤」直接對應；機讀（退出碼）與人讀（繁中訊息）並行。
  - 測試容易：可直接 `pytest.raises(QualifiedSetEmpty)`。
- **Alternatives considered**：
  - **單一通用 Exception**：違反原則 V，且測試只能依賴訊息字串。

---

## R-008 黃金檔測試：JSON 逐位元組比對

- **Decision**：基準場景的稽核紀錄寫入 `tests/golden/teacher-class-baseline.audit.json`；測試以 `assert generated == golden` 逐位元組比對。
- **Rationale**：
  - 是 SC-001（100% 可重現）最直接的驗證。
  - 黃金檔在 PR 中可被肉眼 diff，符合「可稽核」精神。
- **Alternatives considered**：
  - **僅比對最終配對**：無法驗證稽核紀錄完整性。
  - **結構性比對**：較不嚴格，會掩蓋細微跨版本差異。

---

## R-009 專案布局：單一 Python 套件

- **Decision**：採 `src/matcher/` 單一套件布局，library 與 CLI 共存；以 `pyproject.toml` 宣告 `matcher` console script entry point。
- **Rationale**：
  - 符合現代 Python 慣例（src layout 避免 import-shadowing）。
  - 與「過濾」與「分配」明確分離為兩個模組（`filter.py` / `allocator.py`）一致。
- **Alternatives considered**：
  - **拆兩套件（matcher-core / matcher-cli）**：本階段尚無共享需求，違反「簡潔優先」。

---

## 已解決的 NEEDS CLARIFICATION 列表

本 plan Technical Context 中無 NEEDS CLARIFICATION 標記；所有先前在 spec.md `Assumptions` 中標為「由 plan 決定」的項目皆於上述 R-001 ~ R-009 解決。

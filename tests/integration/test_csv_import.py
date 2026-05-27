"""US1：CSV 匯入整合測試 + 三路徑等價。"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from matcher.cli import app

runner = CliRunner()
ROOT = Path(__file__).resolve().parents[2]


def _run_csv(csv_path: Path, audit: Path, seed: int = 123456) -> None:
    r = runner.invoke(app, [
        "run",
        "--template", "teacher-class",
        "--roster-csv", str(csv_path),
        "--seed", str(seed),
        "--output", str(audit),
    ])
    assert r.exit_code == 0, r.output


def test_csv_runs_successfully(tmp_path: Path):
    audit = tmp_path / "audit.json"
    _run_csv(ROOT / "examples" / "teacher-class" / "roster.csv", audit)
    data = json.loads(audit.read_text(encoding="utf-8"))
    assert data["schema_version"] == "1.5"
    assert data["import_metadata"]["source_type"] == "csv"
    assert data["import_metadata"]["encoding"] in {"utf-8", "utf-8-sig"}
    assert data["import_metadata"]["row_count"] == 10


def test_csv_yaml_equivalence_core_fields(tmp_path: Path):
    """SC-001：CSV 與 YAML 同資料同 seed → 五段中四段相同（template_snapshot 略過，因 YAML 路徑無模板）。"""
    yaml_out = tmp_path / "y.json"
    csv_out = tmp_path / "c.json"

    runner.invoke(app, [
        "run",
        "--rules", str(ROOT / "examples" / "teacher-class" / "rules.yaml"),
        "--roster", str(ROOT / "examples" / "teacher-class" / "roster.yaml"),
        "--seed", "123456",
        "--output", str(yaml_out),
    ])
    _run_csv(ROOT / "examples" / "teacher-class" / "roster.csv", csv_out)

    y = json.loads(yaml_out.read_text(encoding="utf-8"))
    c = json.loads(csv_out.read_text(encoding="utf-8"))
    for key in ["qualified_set", "assignment", "filter_trace", "allocation_trace"]:
        assert y[key] == c[key], f"{key} 不相等"


def test_csv_two_runs_byte_identical(tmp_path: Path):
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    _run_csv(ROOT / "examples" / "teacher-class" / "roster.csv", a)
    _run_csv(ROOT / "examples" / "teacher-class" / "roster.csv", b)
    assert a.read_bytes() == b.read_bytes()


def test_csv_with_bom(tmp_path: Path):
    """UTF-8 BOM 編碼的 CSV 仍能正常讀取（Excel 另存常見格式）。"""
    src = (ROOT / "examples" / "teacher-class" / "roster.csv").read_text(encoding="utf-8")
    bom_csv = tmp_path / "roster.csv"
    bom_csv.write_text(src, encoding="utf-8-sig")
    (tmp_path / "roster.targets.yaml").write_bytes(
        (ROOT / "examples" / "teacher-class" / "roster.targets.yaml").read_bytes()
    )
    audit = tmp_path / "audit.json"
    _run_csv(bom_csv, audit)
    data = json.loads(audit.read_text(encoding="utf-8"))
    assert data["import_metadata"]["encoding"] == "utf-8-sig"


def test_csv_with_cp950(tmp_path: Path):
    """CP950（Big5）編碼的 CSV 也能讀取。"""
    src = (ROOT / "examples" / "teacher-class" / "roster.csv").read_text(encoding="utf-8")
    cp950_csv = tmp_path / "roster.csv"
    cp950_csv.write_bytes(src.encode("cp950"))
    (tmp_path / "roster.targets.yaml").write_bytes(
        (ROOT / "examples" / "teacher-class" / "roster.targets.yaml").read_bytes()
    )
    audit = tmp_path / "audit.json"
    _run_csv(cp950_csv, audit)
    data = json.loads(audit.read_text(encoding="utf-8"))
    assert data["import_metadata"]["encoding"] == "cp950"


def test_csv_ignores_unknown_columns(tmp_path: Path):
    """CSV 多欄位（模板未宣告）→ 忽略不報錯（FR-009）。"""
    src = (ROOT / "examples" / "teacher-class" / "roster.csv").read_text(encoding="utf-8")
    # 加一個「備註」欄
    lines = src.splitlines()
    lines[0] = lines[0] + ",備註"
    for i in range(1, len(lines)):
        lines[i] = lines[i] + ",test"
    extra_csv = tmp_path / "roster.csv"
    extra_csv.write_text("\n".join(lines) + "\n", encoding="utf-8")
    (tmp_path / "roster.targets.yaml").write_bytes(
        (ROOT / "examples" / "teacher-class" / "roster.targets.yaml").read_bytes()
    )
    audit = tmp_path / "audit.json"
    _run_csv(extra_csv, audit)
    # 與原始 CSV 比對，assignment 應相同
    orig = tmp_path / "orig.json"
    _run_csv(ROOT / "examples" / "teacher-class" / "roster.csv", orig)
    d1 = json.loads(audit.read_text(encoding="utf-8"))
    d2 = json.loads(orig.read_text(encoding="utf-8"))
    assert d1["assignment"] == d2["assignment"]

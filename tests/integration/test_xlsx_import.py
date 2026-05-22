"""US2：Excel 匯入整合測試。"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from matcher.cli import app

runner = CliRunner()
ROOT = Path(__file__).resolve().parents[2]


def test_xlsx_single_sheet(tmp_path: Path):
    audit = tmp_path / "audit.json"
    r = runner.invoke(app, [
        "run",
        "--template", "study-group",
        "--roster-xlsx", str(ROOT / "examples" / "study-group" / "roster.xlsx"),
        "--seed", "2026",
        "--output", str(audit),
    ])
    assert r.exit_code == 0, r.output
    data = json.loads(audit.read_text(encoding="utf-8"))
    assert data["import_metadata"]["source_type"] == "xlsx"
    assert data["import_metadata"]["sheet_name"] == "Sheet1"
    assert data["import_metadata"]["row_count"] == 9


def test_xlsx_multi_sheet_without_sheet_arg(tmp_path: Path):
    r = runner.invoke(app, [
        "run",
        "--template", "study-group",
        "--roster-xlsx", str(ROOT / "examples" / "study-group" / "roster-multi.xlsx"),
        "--seed", "1",
        "--output", str(tmp_path / "a.json"),
    ])
    assert r.exit_code == 33
    msg = r.output + (r.stderr or "")
    assert "未指定 --sheet" in msg
    assert "報名表" in msg


def test_xlsx_multi_sheet_with_sheet_arg(tmp_path: Path):
    audit = tmp_path / "audit.json"
    r = runner.invoke(app, [
        "run",
        "--template", "study-group",
        "--roster-xlsx", str(ROOT / "examples" / "study-group" / "roster-multi.xlsx"),
        "--sheet", "報名表",
        "--seed", "2026",
        "--output", str(audit),
    ])
    assert r.exit_code == 0, r.output
    data = json.loads(audit.read_text(encoding="utf-8"))
    assert data["import_metadata"]["sheet_name"] == "報名表"


def test_xlsx_invalid_sheet_name(tmp_path: Path):
    r = runner.invoke(app, [
        "run",
        "--template", "study-group",
        "--roster-xlsx", str(ROOT / "examples" / "study-group" / "roster-multi.xlsx"),
        "--sheet", "不存在的表",
        "--seed", "1",
        "--output", str(tmp_path / "a.json"),
    ])
    assert r.exit_code == 33
    assert "不存在" in (r.output + (r.stderr or ""))


def test_xlsx_two_runs_byte_identical(tmp_path: Path):
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    for out in (a, b):
        runner.invoke(app, [
            "run",
            "--template", "study-group",
            "--roster-xlsx", str(ROOT / "examples" / "study-group" / "roster.xlsx"),
            "--seed", "2026",
            "--output", str(out),
        ])
    assert a.read_bytes() == b.read_bytes()

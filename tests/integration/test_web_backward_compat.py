"""Polish：階段 1/2a/2b CLI 介面未被 Web feature 影響。"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from matcher.cli import app

runner = CliRunner()
ROOT = Path(__file__).resolve().parents[2]


def test_cli_legacy_rules_roster_still_works(tmp_path: Path):
    out = tmp_path / "a.json"
    r = runner.invoke(app, [
        "run",
        "--rules", str(ROOT / "examples" / "teacher-class" / "rules.yaml"),
        "--roster", str(ROOT / "examples" / "teacher-class" / "roster.yaml"),
        "--seed", "123456",
        "--output", str(out),
    ])
    assert r.exit_code == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["template_snapshot"] is None
    assert data["import_metadata"] is None


def test_cli_template_csv_still_works(tmp_path: Path):
    out = tmp_path / "a.json"
    r = runner.invoke(app, [
        "run",
        "--template", "teacher-class",
        "--roster-csv", str(ROOT / "examples" / "teacher-class" / "roster.csv"),
        "--seed", "123456",
        "--output", str(out),
    ])
    assert r.exit_code == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["template_snapshot"]["id"] == "teacher-class"
    assert data["import_metadata"]["source_type"] == "csv"


def test_cli_template_subcommands_still_work():
    r = runner.invoke(app, ["template", "list"])
    assert r.exit_code == 0
    assert "teacher-class" in r.output

    r = runner.invoke(app, ["template", "show", "teacher-class"])
    assert r.exit_code == 0
    assert "R001" in r.output

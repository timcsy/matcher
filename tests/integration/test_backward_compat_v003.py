"""Polish：階段 1+2a 既有 YAML 路徑仍可用（SC-007）。"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from matcher.cli import app

runner = CliRunner()
ROOT = Path(__file__).resolve().parents[2]


def test_legacy_rules_roster_still_works(tmp_path: Path):
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
    assert data["schema_version"] == "1.4"
    assert data["template_snapshot"] is None
    assert data["import_metadata"] is None


def test_legacy_template_yaml_roster(tmp_path: Path):
    out = tmp_path / "a.json"
    r = runner.invoke(app, [
        "run",
        "--template", "teacher-class",
        "--roster", str(ROOT / "examples" / "teacher-class" / "roster.yaml"),
        "--seed", "123456",
        "--output", str(out),
    ])
    assert r.exit_code == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["template_snapshot"]["id"] == "teacher-class"
    assert data["import_metadata"] is None

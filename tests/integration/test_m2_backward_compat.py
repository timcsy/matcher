"""US3：既有 M0/M1 路徑向後相容（tie_break_random_index 為 null）。"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from matcher.cli import app

runner = CliRunner()
ROOT = Path(__file__).resolve().parents[2]


def test_m0_trace_has_null_tie_break(tmp_path: Path):
    out = tmp_path / "audit.json"
    runner.invoke(app, [
        "run",
        "--rules", str(ROOT / "examples" / "teacher-class" / "rules.yaml"),
        "--roster", str(ROOT / "examples" / "teacher-class" / "roster.yaml"),
        "--seed", "123456",
        "--output", str(out),
    ])
    data = json.loads(out.read_text(encoding="utf-8"))
    for entry in data["allocation_trace"]:
        assert entry["tie_break_random_index"] is None


def test_m1_trace_has_null_tie_break(tmp_path: Path):
    out = tmp_path / "audit.json"
    runner.invoke(app, [
        "run",
        "--template", "study-group",
        "--roster-csv", str(ROOT / "examples" / "study-group" / "roster-m1.csv"),
        "--seed", "2026",
        "--mechanism", "M1",
        "--output", str(out),
    ])
    data = json.loads(out.read_text(encoding="utf-8"))
    for entry in data["allocation_trace"]:
        assert entry["tie_break_random_index"] is None


def test_schema_version_unchanged(tmp_path: Path):
    """audit schema 保持 v1.3，不升版本。"""
    out = tmp_path / "audit.json"
    runner.invoke(app, [
        "run",
        "--rules", str(ROOT / "examples" / "teacher-class" / "rules.yaml"),
        "--roster", str(ROOT / "examples" / "teacher-class" / "roster.yaml"),
        "--seed", "123456",
        "--output", str(out),
    ])
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["schema_version"] == "1.3"

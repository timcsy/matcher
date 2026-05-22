"""Polish：matcher filter 子命令（FR-005）。"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from matcher.cli import app

runner = CliRunner()

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "examples" / "teacher-class"
F = ROOT / "tests" / "fixtures" / "edge_cases"


def test_filter_success(tmp_path: Path):
    out = tmp_path / "qualified.json"
    r = runner.invoke(app, [
        "filter",
        "--rules", str(EXAMPLES / "rules.yaml"),
        "--roster", str(EXAMPLES / "roster.yaml"),
        "--output", str(out),
    ])
    assert r.exit_code == 0, r.output
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert "qualified_set" in payload
    assert "filter_trace" in payload
    # 不應含分配資料
    assert "assignment" not in payload
    assert "allocation_trace" not in payload


def test_filter_does_not_require_seed(tmp_path: Path):
    """filter 子命令不需要 --seed。"""
    out = tmp_path / "q.json"
    r = runner.invoke(app, [
        "filter",
        "--rules", str(EXAMPLES / "rules.yaml"),
        "--roster", str(EXAMPLES / "roster.yaml"),
        "--output", str(out),
    ])
    assert r.exit_code == 0


def test_filter_propagates_rule_contradiction():
    r = runner.invoke(app, [
        "filter",
        "--rules", str(F / "rule_contradiction.rules.yaml"),
        "--roster", str(F / "minimal.roster.yaml"),
    ])
    assert r.exit_code == 12


def test_filter_propagates_qualified_set_empty():
    r = runner.invoke(app, [
        "filter",
        "--rules", str(F / "empty_qualified.rules.yaml"),
        "--roster", str(F / "empty_qualified.roster.yaml"),
    ])
    assert r.exit_code == 10

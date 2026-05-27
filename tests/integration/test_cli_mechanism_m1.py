"""US1：CLI --mechanism M1 整合測試。"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from matcher.cli import app

runner = CliRunner()
ROOT = Path(__file__).resolve().parents[2]


def _run_m1(audit: Path, seed: int = 2026) -> None:
    r = runner.invoke(app, [
        "run",
        "--template", "study-group",
        "--roster-csv", str(ROOT / "examples" / "study-group" / "roster-m1.csv"),
        "--seed", str(seed),
        "--mechanism", "M1",
        "--output", str(audit),
    ])
    assert r.exit_code == 0, r.output


def test_m1_runs_successfully(tmp_path: Path):
    audit = tmp_path / "audit.json"
    _run_m1(audit)
    data = json.loads(audit.read_text(encoding="utf-8"))
    assert data["schema_version"] == "1.5"
    assert data["mechanism"] == "M1"
    assert data["processing_order"] is not None
    assert len(data["processing_order"]) == 9  # 9 students


def test_m1_two_runs_byte_identical(tmp_path: Path):
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    _run_m1(a)
    _run_m1(b)
    assert a.read_bytes() == b.read_bytes()


def test_m1_preference_rank_is_legal(tmp_path: Path):
    """每位被分配學生的 preference_rank 為 1-based 或 null。"""
    audit = tmp_path / "audit.json"
    _run_m1(audit)
    data = json.loads(audit.read_text(encoding="utf-8"))
    for entry in data["allocation_trace"]:
        pr = entry.get("preference_rank")
        assert pr is None or (isinstance(pr, int) and pr >= 1)


def test_m1_matches_golden(tmp_path: Path):
    out = tmp_path / "audit.json"
    _run_m1(out)
    golden = ROOT / "tests" / "golden" / "study-group-m1.audit.json"
    assert out.read_bytes() == golden.read_bytes()


def test_m1_stdout_shows_processing_order(tmp_path: Path):
    out = tmp_path / "audit.json"
    r = runner.invoke(app, [
        "run",
        "--template", "study-group",
        "--roster-csv", str(ROOT / "examples" / "study-group" / "roster-m1.csv"),
        "--seed", "2026",
        "--mechanism", "M1",
        "--output", str(out),
    ])
    assert "輪流挑" in r.output
    assert "挑志願順序" in r.output

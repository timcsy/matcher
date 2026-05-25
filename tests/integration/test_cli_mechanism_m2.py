"""US1：CLI --mechanism M2 整合測試。"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from matcher.cli import app

runner = CliRunner()
ROOT = Path(__file__).resolve().parents[2]


def _run_m2(audit: Path, seed: int = 2026) -> None:
    r = runner.invoke(app, [
        "run",
        "--template", "study-group",
        "--roster-csv", str(ROOT / "examples" / "study-group" / "roster-m1.csv"),
        "--seed", str(seed),
        "--mechanism", "M2",
        "--output", str(audit),
    ])
    assert r.exit_code == 0, r.output


def test_m2_runs_successfully(tmp_path: Path):
    audit = tmp_path / "audit.json"
    _run_m2(audit)
    data = json.loads(audit.read_text(encoding="utf-8"))
    assert data["schema_version"] == "1.4"
    assert data["mechanism"] == "M2"
    assert data["processing_order"] is not None


def test_m2_two_runs_byte_identical(tmp_path: Path):
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    _run_m2(a)
    _run_m2(b)
    assert a.read_bytes() == b.read_bytes()


def test_m2_matches_golden(tmp_path: Path):
    out = tmp_path / "audit.json"
    _run_m2(out)
    golden = ROOT / "tests" / "golden" / "study-group-m2.audit.json"
    assert out.read_bytes() == golden.read_bytes()


def test_m2_stdout_shows_boston_label(tmp_path: Path):
    out = tmp_path / "audit.json"
    r = runner.invoke(app, [
        "run",
        "--template", "study-group",
        "--roster-csv", str(ROOT / "examples" / "study-group" / "roster-m1.csv"),
        "--seed", "2026",
        "--mechanism", "M2",
        "--output", str(out),
    ])
    assert "依志願先後填滿" in r.output


def test_m2_preference_rank_in_audit(tmp_path: Path):
    audit = tmp_path / "audit.json"
    _run_m2(audit)
    data = json.loads(audit.read_text(encoding="utf-8"))
    # 每筆 trace 條目要嘛 preference_rank 為 1..N，要嘛為 null（fallback）
    for entry in data["allocation_trace"]:
        pr = entry.get("preference_rank")
        assert pr is None or (isinstance(pr, int) and pr >= 1)

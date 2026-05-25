"""US3：既有 M0 路徑向後相容（v1.3 + null 欄位）。"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from matcher.cli import app

runner = CliRunner()
ROOT = Path(__file__).resolve().parents[2]


def test_m0_audit_has_null_processing_order(tmp_path: Path):
    out = tmp_path / "audit.json"
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
    assert data["mechanism"] == "M0"
    assert data["processing_order"] is None


def test_m0_allocation_trace_has_null_m1_fields(tmp_path: Path):
    """M0 路徑每筆 allocation_trace 條目的 M1 相關欄位皆為 null。"""
    out = tmp_path / "audit.json"
    r = runner.invoke(app, [
        "run",
        "--rules", str(ROOT / "examples" / "teacher-class" / "rules.yaml"),
        "--roster", str(ROOT / "examples" / "teacher-class" / "roster.yaml"),
        "--seed", "123456",
        "--output", str(out),
    ])
    assert r.exit_code == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    for entry in data["allocation_trace"]:
        assert entry.get("preferred_order") is None
        assert entry.get("preference_rank") is None
        assert entry.get("fallback_random_index") is None

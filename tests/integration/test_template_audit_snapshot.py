"""US1：template_snapshot 進入稽核 + 兩次執行 bytes 相同。"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from matcher.cli import app

runner = CliRunner()
ROOT = Path(__file__).resolve().parents[2]


def _run(out: Path, seed: int = 123456) -> None:
    r = runner.invoke(app, [
        "run",
        "--template", "teacher-class",
        "--roster", str(ROOT / "examples" / "teacher-class" / "roster.yaml"),
        "--seed", str(seed),
        "--output", str(out),
    ])
    assert r.exit_code == 0, r.output


def test_two_runs_with_template_are_byte_identical(tmp_path: Path):
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    _run(a)
    _run(b)
    assert a.read_bytes() == b.read_bytes()


def test_template_snapshot_contains_full_template(tmp_path: Path):
    out = tmp_path / "audit.json"
    _run(out)
    data = json.loads(out.read_text(encoding="utf-8"))
    snap = data["template_snapshot"]
    assert snap["id"] == "teacher-class"
    assert snap["schema_version"] == "1.0"
    assert "name" in snap
    assert "description" in snap
    assert "attributes" in snap
    assert "rules" in snap


def test_audit_schema_version_is_1_5(tmp_path: Path):
    out = tmp_path / "audit.json"
    _run(out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["schema_version"] == "1.5"

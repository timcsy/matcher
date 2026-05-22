"""US1：matcher run --template 整合測試。"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from matcher.cli import app

runner = CliRunner()
ROOT = Path(__file__).resolve().parents[2]


def test_run_with_template_id(tmp_path: Path):
    audit = tmp_path / "audit.json"
    r = runner.invoke(app, [
        "run",
        "--template", "teacher-class",
        "--roster", str(ROOT / "examples" / "teacher-class" / "roster.yaml"),
        "--seed", "123456",
        "--output", str(audit),
    ])
    assert r.exit_code == 0, r.output
    assert "teacher-class" in r.output
    data = json.loads(audit.read_text(encoding="utf-8"))
    assert data["schema_version"] == "1.1"
    assert data["template_snapshot"] is not None
    assert data["template_snapshot"]["id"] == "teacher-class"


def test_run_with_nonexistent_template(tmp_path: Path):
    r = runner.invoke(app, [
        "run",
        "--template", "no-such",
        "--roster", str(ROOT / "examples" / "teacher-class" / "roster.yaml"),
        "--seed", "1",
        "--output", str(tmp_path / "a.json"),
    ])
    assert r.exit_code == 20
    assert "找不到模板" in (r.output + (r.stderr or ""))


def test_run_with_template_file(tmp_path: Path):
    """先 export，再以 --template-file 載入跑。"""
    exported = tmp_path / "tc.yaml"
    r1 = runner.invoke(app, [
        "template", "export", "teacher-class", "--output", str(exported),
    ])
    assert r1.exit_code == 0, r1.output

    audit = tmp_path / "audit.json"
    r2 = runner.invoke(app, [
        "run",
        "--template-file", str(exported),
        "--roster", str(ROOT / "examples" / "teacher-class" / "roster.yaml"),
        "--seed", "123456",
        "--output", str(audit),
    ])
    assert r2.exit_code == 0, r2.output

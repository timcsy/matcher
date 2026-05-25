"""Polish：階段 1 既有介面持續可用（SC-007）。"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from matcher.cli import app

runner = CliRunner()
ROOT = Path(__file__).resolve().parents[2]


def test_legacy_rules_roster_still_works(tmp_path: Path):
    out = tmp_path / "audit.json"
    r = runner.invoke(app, [
        "run",
        "--rules", str(ROOT / "examples" / "teacher-class" / "rules.yaml"),
        "--roster", str(ROOT / "examples" / "teacher-class" / "roster.yaml"),
        "--seed", "123456",
        "--output", str(out),
    ])
    assert r.exit_code == 0, r.output
    data = json.loads(out.read_text(encoding="utf-8"))
    # schema 升級到 1.2
    assert data["schema_version"] == "1.4"
    # 但不使用模板 → template_snapshot 為 null
    assert data["template_snapshot"] is None
    # YAML 路徑 → import_metadata 為 null
    assert data["import_metadata"] is None


def test_legacy_matches_baseline_golden(tmp_path: Path):
    """與重新生成的階段 1 baseline 黃金檔比對。"""
    out = tmp_path / "audit.json"
    r = runner.invoke(app, [
        "run",
        "--rules", str(ROOT / "examples" / "teacher-class" / "rules.yaml"),
        "--roster", str(ROOT / "examples" / "teacher-class" / "roster.yaml"),
        "--seed", "123456",
        "--output", str(out),
    ])
    assert r.exit_code == 0
    golden = ROOT / "tests" / "golden" / "teacher-class-baseline.audit.json"
    assert out.read_bytes() == golden.read_bytes()

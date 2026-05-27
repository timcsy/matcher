"""US1 整合：基準場景 CLI 端對端。"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from matcher.cli import app

runner = CliRunner()

EXAMPLES = Path(__file__).resolve().parents[2] / "examples" / "teacher-class"


def test_baseline_runs_successfully(tmp_path: Path):
    audit = tmp_path / "audit.json"
    result = runner.invoke(app, [
        "run",
        "--rules", str(EXAMPLES / "rules.yaml"),
        "--roster", str(EXAMPLES / "roster.yaml"),
        "--seed", "123456",
        "--output", str(audit),
    ])
    assert result.exit_code == 0, result.output
    assert "稽核紀錄已寫入" in result.output
    assert audit.exists()
    data = json.loads(audit.read_text(encoding="utf-8"))
    assert data["schema_version"] == "1.5"
    assert data["mechanism"] == "M0"
    assert data["seed"] == 123456
    assert "assignment" in data
    assert "filter_trace" in data
    assert "allocation_trace" in data
    assert data["template_snapshot"] is None  # --rules 路徑不應有 template snapshot


def test_assignment_within_qualified_set(tmp_path: Path):
    audit = tmp_path / "audit.json"
    runner.invoke(app, [
        "run",
        "--rules", str(EXAMPLES / "rules.yaml"),
        "--roster", str(EXAMPLES / "roster.yaml"),
        "--seed", "999",
        "--output", str(audit),
    ])
    data = json.loads(audit.read_text(encoding="utf-8"))
    qs = data["qualified_set"]
    for participant_id, target_id in data["assignment"].items():
        if target_id is not None:
            assert target_id in qs[participant_id], f"{participant_id}→{target_id} 不在資格集合內"

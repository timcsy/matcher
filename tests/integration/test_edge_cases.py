"""US2：邊界情境的明確錯誤訊息與 exit code。"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from matcher.cli import app

runner = CliRunner()
F = Path(__file__).resolve().parents[1] / "fixtures" / "edge_cases"


def _invoke(*args: str):
    return runner.invoke(app, list(args))


def test_qualified_set_empty():
    r = _invoke(
        "run",
        "--rules", str(F / "empty_qualified.rules.yaml"),
        "--roster", str(F / "empty_qualified.roster.yaml"),
        "--seed", "1",
    )
    assert r.exit_code == 10
    assert "資格集合為空" in (r.output + (r.stderr or ""))


def test_capacity_shortage():
    r = _invoke(
        "run",
        "--rules", str(F / "capacity_shortage.rules.yaml"),
        "--roster", str(F / "capacity_shortage.roster.yaml"),
        "--seed", "1",
    )
    assert r.exit_code == 11
    msg = r.output + (r.stderr or "")
    assert "容量不足" in msg
    assert "超額" in msg


def test_rule_contradiction():
    r = _invoke(
        "run",
        "--rules", str(F / "rule_contradiction.rules.yaml"),
        "--roster", str(F / "minimal.roster.yaml"),
        "--seed", "1",
    )
    assert r.exit_code == 12
    assert "矛盾" in (r.output + (r.stderr or ""))


def test_seed_missing():
    r = _invoke(
        "run",
        "--rules", str(F / "passthrough.rules.yaml"),
        "--roster", str(F / "minimal.roster.yaml"),
    )
    assert r.exit_code == 13
    assert "seed 未提供" in (r.output + (r.stderr or ""))


def test_empty_roster():
    r = _invoke(
        "run",
        "--rules", str(F / "passthrough.rules.yaml"),
        "--roster", str(F / "empty_roster.yaml"),
        "--seed", "1",
    )
    assert r.exit_code == 14
    assert "名單為空" in (r.output + (r.stderr or ""))


def test_duplicate_identity():
    r = _invoke(
        "run",
        "--rules", str(F / "passthrough.rules.yaml"),
        "--roster", str(F / "duplicate_identity.roster.yaml"),
        "--seed", "1",
    )
    assert r.exit_code == 15
    assert "重複身分" in (r.output + (r.stderr or ""))


def test_unknown_attribute():
    r = _invoke(
        "run",
        "--rules", str(F / "unknown_attribute.rules.yaml"),
        "--roster", str(F / "minimal.roster.yaml"),
        "--seed", "1",
    )
    assert r.exit_code == 16
    assert "未定義" in (r.output + (r.stderr or ""))

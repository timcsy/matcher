"""US1 整合：可重現性（SC-001）+ 黃金檔比對。"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from matcher.cli import app

runner = CliRunner()

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "examples" / "teacher-class"
GOLDEN = ROOT / "tests" / "golden" / "teacher-class-baseline.audit.json"


def _run(audit_path: Path, seed: int = 123456) -> None:
    result = runner.invoke(app, [
        "run",
        "--rules", str(EXAMPLES / "rules.yaml"),
        "--roster", str(EXAMPLES / "roster.yaml"),
        "--seed", str(seed),
        "--output", str(audit_path),
    ])
    assert result.exit_code == 0, result.output


def test_two_runs_byte_identical(tmp_path: Path):
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    _run(a)
    _run(b)
    assert a.read_bytes() == b.read_bytes()


def test_matches_golden(tmp_path: Path):
    """SC-001 + 黃金檔比對。"""
    if not GOLDEN.exists():
        import pytest
        pytest.skip("黃金檔尚未生成（將於 T024 建立後此測試上線）")
    out = tmp_path / "audit.json"
    _run(out)
    assert out.read_bytes() == GOLDEN.read_bytes()


def test_different_seed_same_qualified_set(tmp_path: Path):
    """規則篩選不受 seed 影響。"""
    import json
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    _run(a, seed=1)
    _run(b, seed=999)
    da = json.loads(a.read_text(encoding="utf-8"))
    db = json.loads(b.read_text(encoding="utf-8"))
    assert da["qualified_set"] == db["qualified_set"]

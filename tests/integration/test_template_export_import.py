"""US2：模板匯出後再匯入，跑出的稽核紀錄逐位元組相同（SC-003）。"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from matcher.cli import app

runner = CliRunner()
ROOT = Path(__file__).resolve().parents[2]


def _run_with_id(tmp_path: Path, template_id: str, roster: Path, seed: int = 123) -> Path:
    out = tmp_path / f"{template_id}-id.json"
    r = runner.invoke(app, [
        "run",
        "--template", template_id,
        "--roster", str(roster),
        "--seed", str(seed),
        "--output", str(out),
    ])
    assert r.exit_code == 0, r.output
    return out


def _run_with_file(tmp_path: Path, template_id: str, roster: Path, seed: int = 123) -> Path:
    exported = tmp_path / f"{template_id}.yaml"
    runner.invoke(app, ["template", "export", template_id, "--output", str(exported)])
    out = tmp_path / f"{template_id}-file.json"
    r = runner.invoke(app, [
        "run",
        "--template-file", str(exported),
        "--roster", str(roster),
        "--seed", str(seed),
        "--output", str(out),
    ])
    assert r.exit_code == 0, r.output
    return out


def test_teacher_class_export_import_byte_identical(tmp_path: Path):
    roster = ROOT / "examples" / "teacher-class" / "roster.yaml"
    a = _run_with_id(tmp_path, "teacher-class", roster)
    b = _run_with_file(tmp_path, "teacher-class", roster)
    assert a.read_bytes() == b.read_bytes()


def test_study_group_export_import_byte_identical(tmp_path: Path):
    roster = ROOT / "examples" / "study-group" / "roster.yaml"
    a = _run_with_id(tmp_path, "study-group", roster)
    b = _run_with_file(tmp_path, "study-group", roster)
    assert a.read_bytes() == b.read_bytes()

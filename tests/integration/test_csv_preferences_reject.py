"""US3：CSV 含非空 preferences 在 M0 下被拒絕（沿用階段 1 exit 17）。"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from matcher.cli import app

runner = CliRunner()
ROOT = Path(__file__).resolve().parents[2]


def _make_study_group_targets(tmp_path: Path, name: str) -> None:
    p = tmp_path / f"{name}.targets.yaml"
    p.write_bytes((ROOT / "examples" / "study-group" / "roster.targets.yaml").read_bytes())


def test_csv_with_nonempty_preferences_rejected(tmp_path: Path):
    csv = tmp_path / "withpref.csv"
    csv.write_text(
        "id,姓名,年級,志願組別\n"
        "S01,小明,5,G1;G2;G3\n"
        "S02,小華,4,\n",
        encoding="utf-8",
    )
    _make_study_group_targets(tmp_path, "withpref")
    r = runner.invoke(app, [
        "run", "--template", "study-group",
        "--roster-csv", str(csv), "--seed", "1",
        "--output", str(tmp_path / "a.json"),
    ])
    assert r.exit_code == 17
    msg = r.output + (r.stderr or "")
    assert "M0 純抽籤" in msg
    # 階段 6 改：M1 已啟用，訊息現在指引「改用 --mechanism M1」
    assert ("--mechanism M1" in msg) or ("階段 4" in msg)


def test_csv_with_empty_preferences_passes(tmp_path: Path):
    csv = tmp_path / "emptypref.csv"
    csv.write_text(
        "id,姓名,年級,志願組別\n"
        "S01,小明,5,\n"
        "S02,小華,4,\n"
        "S03,小美,6,\n",
        encoding="utf-8",
    )
    _make_study_group_targets(tmp_path, "emptypref")
    r = runner.invoke(app, [
        "run", "--template", "study-group",
        "--roster-csv", str(csv), "--seed", "1",
        "--output", str(tmp_path / "a.json"),
    ])
    assert r.exit_code == 0, r.output

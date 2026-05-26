"""Feature 015 US1：CLI 空資格集合診斷。"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from matcher.cli import app

runner = CliRunner()

# teacher-class：班級 feature 填無效值 → R003 對所有組合失敗 → 空集合
BAD_SIDECAR = """targets:
  - id: C01
    capacity: 2
    attributes: {name: "甲班", required_subjects: ["國文"], feature: "不存在的特色"}
"""
CSV = "id,name,speciality,seniority\nT01,王老師,國文,8\n"

FORBIDDEN = ("filter_trace", "qualified_set", "exit_code", "role.", "target.")


def test_cli_empty_set_exit10_with_culprit(tmp_path: Path):
    csv = tmp_path / "r.csv"
    csv.write_text(CSV, encoding="utf-8")
    (tmp_path / "r.targets.yaml").write_text(BAD_SIDECAR, encoding="utf-8")
    r = runner.invoke(app, [
        "run", "--template", "teacher-class",
        "--roster-csv", str(csv), "--seed", "1",
    ])
    assert r.exit_code == 10, r.output
    out = r.output
    # 指出元兇規則 R003 的「描述」與卡住組數
    assert "班級特色" in out  # R003 描述含此詞
    assert "卡住" in out or "沒通過" in out
    # 不洩漏技術 token
    for tok in FORBIDDEN:
        assert tok not in out, f"CLI 輸出含技術 token: {tok}"

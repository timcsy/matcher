"""Feature 010 US3：CLI matcher report 指令。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from matcher.cli import app
from matcher.web.pdf import _WEASYPRINT_AVAILABLE

ROOT = Path(__file__).resolve().parents[2]
runner = CliRunner()


def _make_audit_json(tmp_path: Path) -> Path:
    """先用 CLI run 產 audit，再給 report 用。"""
    audit_path = tmp_path / "audit.json"
    r = runner.invoke(app, [
        "run",
        "--template", "study-group",
        "--roster-csv", str(ROOT / "examples" / "study-group" / "roster-m1.csv"),
        "--seed", "2026",
        "--mechanism", "M2",
        "--output", str(audit_path),
    ])
    assert r.exit_code == 0, r.output
    return audit_path


@pytest.mark.skipif(not _WEASYPRINT_AVAILABLE, reason="WeasyPrint 不可用")
def test_cli_report_admin_pdf_success(tmp_path: Path):
    audit = _make_audit_json(tmp_path)
    pdf = tmp_path / "admin.pdf"
    r = runner.invoke(app, [
        "report", "--audit", str(audit), "--output", str(pdf),
    ])
    assert r.exit_code == 0, r.output
    assert pdf.exists()
    assert pdf.read_bytes()[:8].startswith(b"%PDF-")
    assert "PDF 已寫入" in r.output


@pytest.mark.skipif(not _WEASYPRINT_AVAILABLE, reason="WeasyPrint 不可用")
def test_cli_report_individual_pdf_success(tmp_path: Path):
    audit = _make_audit_json(tmp_path)
    pdf = tmp_path / "indiv.pdf"
    r = runner.invoke(app, [
        "report", "--audit", str(audit), "--participant-id", "S01", "--output", str(pdf),
    ])
    assert r.exit_code == 0, r.output
    assert pdf.exists()


def test_cli_report_invalid_audit_exits_51(tmp_path: Path):
    """audit JSON 缺核心欄位。"""
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"mechanism": "M0"}), encoding="utf-8")
    pdf = tmp_path / "x.pdf"
    r = runner.invoke(app, [
        "report", "--audit", str(bad), "--output", str(pdf),
    ])
    assert r.exit_code == 51, r.output
    assert "audit 缺" in (r.output + (r.stderr if hasattr(r, 'stderr') and r.stderr else ""))


@pytest.mark.skipif(not _WEASYPRINT_AVAILABLE, reason="WeasyPrint 不可用")
def test_cli_report_unknown_participant_exits_52(tmp_path: Path):
    audit = _make_audit_json(tmp_path)
    pdf = tmp_path / "x.pdf"
    r = runner.invoke(app, [
        "report", "--audit", str(audit), "--participant-id", "S99", "--output", str(pdf),
    ])
    assert r.exit_code == 52, r.output


def test_cli_report_exits_50_when_weasyprint_unavailable(tmp_path: Path, monkeypatch):
    """無 WeasyPrint → exit 50 + 安裝指引。"""
    monkeypatch.setattr("matcher.web.pdf._WEASYPRINT_AVAILABLE", False)
    # 仍須一個 valid audit JSON 才走到 render
    audit = tmp_path / "a.json"
    audit.write_text(json.dumps({
        "assignment": {}, "roster_snapshot": {"participants": []},
    }), encoding="utf-8")
    pdf = tmp_path / "x.pdf"
    r = runner.invoke(app, [
        "report", "--audit", str(audit), "--output", str(pdf),
    ])
    assert r.exit_code == 50, r.output

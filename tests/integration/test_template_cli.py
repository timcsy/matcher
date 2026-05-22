"""US2：matcher template list/show/export CLI 整合測試。"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from matcher.cli import app

runner = CliRunner()


def test_template_list():
    r = runner.invoke(app, ["template", "list"])
    assert r.exit_code == 0, r.output
    assert "teacher-class" in r.output
    assert "study-group" in r.output
    assert "教師-班級配對" in r.output
    assert "研習分組" in r.output


def test_template_show_text():
    r = runner.invoke(app, ["template", "show", "teacher-class"])
    assert r.exit_code == 0, r.output
    assert "teacher-class" in r.output
    assert "屬性 schema" in r.output
    assert "規則" in r.output
    assert "R001" in r.output


def test_template_show_study_group_has_preferences_section():
    r = runner.invoke(app, ["template", "show", "study-group"])
    assert r.exit_code == 0, r.output
    assert "preferences schema" in r.output
    assert "本階段不啟用" in r.output


def test_template_show_not_found():
    r = runner.invoke(app, ["template", "show", "no-such"])
    assert r.exit_code == 20
    assert "找不到模板" in (r.output + (r.stderr or ""))


def test_template_export(tmp_path: Path):
    out = tmp_path / "tc.yaml"
    r = runner.invoke(app, ["template", "export", "teacher-class", "--output", str(out)])
    assert r.exit_code == 0, r.output
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "schema_version: '1.0'" in content or "schema_version: \"1.0\"" in content or "schema_version: 1.0" in content
    assert "teacher-class" in content


def test_template_show_yaml_format(tmp_path: Path):
    r = runner.invoke(app, ["template", "show", "teacher-class", "--format", "yaml"])
    assert r.exit_code == 0, r.output
    assert "id: teacher-class" in r.output or "id:" in r.output

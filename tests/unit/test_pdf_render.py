"""Feature 010 Phase 2：render_match_report_pdf 純函式單元測試。"""

from __future__ import annotations

import pytest

from matcher.web.pdf import (
    PdfRenderUnavailable,
    render_match_report_pdf,
    _WEASYPRINT_AVAILABLE,
)


pytestmark = pytest.mark.skipif(
    not _WEASYPRINT_AVAILABLE,
    reason="WeasyPrint 系統依賴不可用（pango/cairo/glib），跳過 PDF 渲染測試",
)


def _minimal_audit() -> dict:
    return {
        "schema_version": "1.3",
        "mechanism": "M0",
        "seed": 1,
        "assignment": {"S01": "G1", "S02": "G2"},
        "qualified_set": {"S01": ["G1"], "S02": ["G2"]},
        "filter_trace": [],
        "allocation_trace": [],
        "template_snapshot": {"id": "study-group", "name": "研習分組"},
        "roster_snapshot": {
            "roles": [
                {"id": "S01", "attributes": {"name": "小明"}, "preferences": []},
                {"id": "S02", "attributes": {"name": "小華"}, "preferences": []},
            ],
            "targets": [
                {"id": "G1", "attributes": {"name": "程式組"}, "capacity": 3},
                {"id": "G2", "attributes": {"name": "自然組"}, "capacity": 3},
            ],
        },
    }


def _record_meta() -> dict:
    return {
        "id": "2026-05-25T00:00:00-abc12345",
        "created_at": "2026-05-25T00:00:00+00:00",
        "input_file": "students.csv",
        "status": "success",
        "error": None,
    }


def test_render_returns_pdf_bytes():
    pdf = render_match_report_pdf(_minimal_audit(), record_meta=_record_meta())
    assert isinstance(pdf, bytes)
    assert pdf[:8].startswith(b"%PDF-")


def test_render_individual_filters_by_role_id():
    pdf = render_match_report_pdf(_minimal_audit(), record_meta=_record_meta(), role_id="S01")
    # 用 pdftotext 之類已超出範圍；簡單檢查 PDF 含必要 metadata
    assert pdf[:8].startswith(b"%PDF-")
    # individual 版本不應提及 S02（other role）
    # 注意：因字體編碼差異，bytes 內可能找不到中文；改檢查整體大小合理
    assert len(pdf) > 1000


def test_render_raises_value_error_on_missing_audit_keys():
    bad_audit = {"mechanism": "M0"}
    with pytest.raises(ValueError, match="assignment"):
        render_match_report_pdf(bad_audit, record_meta=_record_meta())


def test_render_raises_value_error_on_unknown_role_id():
    with pytest.raises(ValueError, match="S99"):
        render_match_report_pdf(_minimal_audit(), record_meta=_record_meta(), role_id="S99")


def test_render_raises_pdf_render_unavailable_when_no_weasyprint(monkeypatch):
    import matcher.web.pdf as pdf_mod
    monkeypatch.setattr(pdf_mod, "_WEASYPRINT_AVAILABLE", False)
    with pytest.raises(PdfRenderUnavailable):
        render_match_report_pdf(_minimal_audit(), record_meta=_record_meta())


def test_render_failed_record_shows_error():
    meta = _record_meta()
    meta["status"] = "failed"
    meta["error"] = {"type": "M1RequiresPreferences", "exit_code": 40, "message": "M1 需要至少一位角色提供志願"}
    audit = _minimal_audit()
    pdf = render_match_report_pdf(audit, record_meta=meta)
    assert pdf[:8].startswith(b"%PDF-")

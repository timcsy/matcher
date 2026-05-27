"""PDF 渲染：把 audit + record_meta 渲染為 A4 列印格式 PDF。

D4：純函式介面，Web 與 CLI 共用。
D2：WeasyPrint 系統依賴缺失時 graceful degrade。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from matcher.web.humanize import (
    mechanism_label,
    preference_rank_display,
    humanize_rule_description,
)

_TEMPLATES_DIR = Path(__file__).parent / "templates" / "pdf"


class PdfRenderUnavailable(Exception):
    """WeasyPrint 套件或系統依賴（pango/cairo/harfbuzz/glib）不可用。"""


def _try_import_weasyprint():
    try:
        from weasyprint import HTML  # noqa: F401
        return True
    except (ImportError, OSError):
        return False


_WEASYPRINT_AVAILABLE = _try_import_weasyprint()


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )


def _format_dt(iso_str: str) -> str:
    if not iso_str:
        return ""
    try:
        from datetime import datetime
        return datetime.fromisoformat(iso_str.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return iso_str


def _build_admin_context(audit: dict, record_meta: dict) -> dict:
    mechanism = audit.get("mechanism", "M0")
    roster = audit.get("roster_snapshot", {}) or {}
    participants = roster.get("participants", []) or []
    targets = roster.get("targets", []) or []
    participant_name_by_id = {r["id"]: (r.get("attributes") or {}).get("name", r["id"]) for r in participants}
    target_name_by_id = {t["id"]: (t.get("attributes") or {}).get("name", t["id"]) for t in targets}

    processing_order = audit.get("processing_order")
    processing_order_display = None
    if processing_order:
        processing_order_display = [(rid, participant_name_by_id.get(rid, rid)) for rid in processing_order]

    rank_by_participant: dict[str, str] = {}
    for entry in audit.get("allocation_trace", []) or []:
        display = preference_rank_display(
            mechanism, entry.get("preference_rank"), entry.get("fallback_random_index"),
        )
        if display is not None:
            rank_by_participant[entry["participant_id"]] = display

    allocation_rows = []
    for rid, tid in sorted((audit.get("assignment") or {}).items()):
        allocation_rows.append({
            "participant_id": rid,
            "participant_name": participant_name_by_id.get(rid, ""),
            "target_id": tid,
            "target_name": target_name_by_id.get(tid, "") if tid else None,
            "rank_display": rank_by_participant.get(rid, ""),
        })

    tpl_snap = audit.get("template_snapshot") or {}
    return {
        "record_id": record_meta.get("id", "（未知）"),
        "created_at": _format_dt(record_meta.get("created_at", "")),
        "input_file": record_meta.get("input_file") or "（無）",
        "status": record_meta.get("status", "success"),
        "error_type": (record_meta.get("error") or {}).get("type"),
        "error_message": (record_meta.get("error") or {}).get("message"),
        "template_name": tpl_snap.get("name", "（無模板）"),
        "template_id": tpl_snap.get("id", ""),
        "mechanism": mechanism,
        "mechanism_label": mechanism_label(mechanism),
        "seed": audit.get("seed"),
        "processing_order_display": processing_order_display,
        "allocation_rows": allocation_rows,
    }


def _build_individual_context(audit: dict, record_meta: dict, participant_id: str, template: Any) -> dict:
    roster = audit.get("roster_snapshot", {}) or {}
    participants = roster.get("participants", []) or []
    targets = roster.get("targets", []) or []
    participant = next((r for r in participants if r["id"] == participant_id), None)
    if participant is None:
        raise ValueError(f"參與者 {participant_id} 不在 audit.roster_snapshot.participants 中")

    mechanism = audit.get("mechanism", "M0")
    target_name_by_id = {t["id"]: (t.get("attributes") or {}).get("name", t["id"]) for t in targets}
    assigned_id = (audit.get("assignment") or {}).get(participant_id)
    assigned_name = target_name_by_id.get(assigned_id) if assigned_id else None

    preference_rank = None
    fallback_random_index = None
    for entry in audit.get("allocation_trace", []) or []:
        if entry.get("participant_id") == participant_id:
            preference_rank = entry.get("preference_rank")
            fallback_random_index = entry.get("fallback_random_index")
            break

    preferred_count = len(participant.get("preferences", []) or [])

    # participant attributes 顯示用——優先用 template description
    participant_attrs_display = []
    attrs = participant.get("attributes", {}) or {}
    if template and getattr(template, "attributes", None):
        decls = getattr(template.attributes, "participants", ())
        decl_by_key = {d.key: d.description for d in decls}
        for key, value in attrs.items():
            participant_attrs_display.append((decl_by_key.get(key) or key, value))
    else:
        for key, value in attrs.items():
            participant_attrs_display.append((key, value))

    tpl_snap = audit.get("template_snapshot") or {}
    return {
        "record_id": record_meta.get("id", "（未知）"),
        "created_at": _format_dt(record_meta.get("created_at", "")),
        "template_name": tpl_snap.get("name", "（無模板）"),
        "mechanism": mechanism,
        "mechanism_label": mechanism_label(mechanism),
        "participant_id": participant_id,
        "participant_name": attrs.get("name", participant_id),
        "participant_attrs_display": participant_attrs_display,
        "assigned_target_id": assigned_id,
        "assigned_target_name": assigned_name,
        "preference_rank": preference_rank,
        "fallback_random_index": fallback_random_index,
        "preferred_count": preferred_count,
    }


def render_match_report_pdf(
    audit: dict,
    *,
    record_meta: dict,
    participant_id: Optional[str] = None,
    template: Any = None,
) -> bytes:
    """A4 PDF bytes。

    - audit 必須含 `assignment` + `roster_snapshot.participants`；否則 raise ValueError
    - participant_id=None → admin 版；str → individual 版（須在 roster 中）
    - WeasyPrint 不可用 → raise PdfRenderUnavailable
    """
    if not _WEASYPRINT_AVAILABLE:
        raise PdfRenderUnavailable(
            "WeasyPrint 不可用——請見 README 安裝系統依賴（macOS: brew install pango glib）"
        )
    if "assignment" not in audit:
        raise ValueError("audit 缺欄位 `assignment`")
    if "roster_snapshot" not in audit or "participants" not in (audit.get("roster_snapshot") or {}):
        raise ValueError("audit 缺欄位 `roster_snapshot.participants`")

    env = _env()
    if participant_id is None:
        ctx = _build_admin_context(audit, record_meta)
        tpl = env.get_template("match_report.html")
    else:
        ctx = _build_individual_context(audit, record_meta, participant_id, template)
        tpl = env.get_template("individual_report.html")

    html_str = tpl.render(**ctx)
    from weasyprint import HTML
    return HTML(string=html_str, base_url=str(_TEMPLATES_DIR)).write_pdf()

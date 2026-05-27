"""CLI `matcher report` 指令：從 audit JSON 產出 PDF 報告。

D6：獨立檔，cli.py 僅 1 行加 app.command 註冊。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from matcher.web.pdf import PdfRenderUnavailable, render_match_report_pdf


def report(
    audit: Path = typer.Option(..., "--audit", help="audit JSON 檔路徑"),
    output: Path = typer.Option(..., "--output", help="PDF 輸出檔路徑"),
    role_id: Optional[str] = typer.Option(None, "--role-id", help="缺省 → admin 版；有值 → individual 版"),
    record_id: Optional[str] = typer.Option(None, "--record-id", help="顯示用；缺省從 audit 推導或標「（CLI 產生）」"),
    created_at: Optional[str] = typer.Option(None, "--created-at", help="ISO-8601；缺省從 audit.generated_at 或當下"),
):
    """從 audit JSON 產出 PDF 報告（admin 或 individual 版）。"""
    try:
        audit_data = json.loads(audit.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        typer.echo(f"無法讀取 audit JSON：{e}", err=True)
        raise typer.Exit(code=51)

    from datetime import datetime, timezone
    record_meta = {
        "id": record_id or audit_data.get("audit_id") or "（CLI 產生）",
        "created_at": created_at or audit_data.get("generated_at") or datetime.now(timezone.utc).isoformat(),
        "input_file": "",
        "status": "success",
        "error": None,
    }

    try:
        pdf_bytes = render_match_report_pdf(
            audit_data, record_meta=record_meta, role_id=role_id, template=None,
        )
    except PdfRenderUnavailable as e:
        typer.echo(
            f"PDF 渲染功能不可用：{e}\n安裝指引：macOS `brew install pango glib`；Debian/Ubuntu `apt install libpango-1.0-0 libcairo2 libgobject-2.0-0`",
            err=True,
        )
        raise typer.Exit(code=50)
    except ValueError as e:
        msg = str(e)
        if role_id and role_id in msg:
            typer.echo(f"參與者不存在：{e}", err=True)
            raise typer.Exit(code=52)
        typer.echo(f"audit 缺核心欄位：{e}", err=True)
        raise typer.Exit(code=51)

    output.write_bytes(pdf_bytes)
    typer.echo(f"PDF 已寫入 {output}")

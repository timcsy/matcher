"""CLI（Typer）：matcher run / filter / template list|show|export。"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import typer

from matcher.audit import dump_audit_json
from matcher.data_import import load_roster_csv, load_roster_xlsx
from matcher.errors import MatcherError, SeedMissing, TemplateNotFound
from matcher.io_yaml import load_preferences, load_roster, load_ruleset, load_template
from matcher.pipeline import MatcherInput, run_filter_only, run_match
from matcher.template_loader import TemplateRegistry, dump_template_yaml

app = typer.Typer(
    add_completion=False,
    help="matcher：核心媒合引擎。依規則過濾出資格集合，於 M0 純抽籤分支下完成分配。",
)

template_app = typer.Typer(
    add_completion=False,
    help="模板系統：list / show / export。",
)
app.add_typer(template_app, name="template")


def _print_summary(audit: dict) -> None:
    if audit.get("template_snapshot"):
        tpl = audit["template_snapshot"]
        typer.echo("=== 模板 ===")
        typer.echo(f"ID：{tpl['id']}")
        typer.echo(f"名稱：{tpl['name']}")
        typer.echo(f"版本：{tpl['schema_version']}")
        typer.echo("")

    rules = audit["rules_snapshot"]["rules"]
    typer.echo("=== 規則檔 ===")
    for r in rules:
        typer.echo(f"  {r['id']}：{r['description']}")

    qs = audit["qualified_set"]
    n_pairs = sum(len(v) for v in qs.values())
    n_with_options = sum(1 for v in qs.values() if v)
    typer.echo("")
    typer.echo("=== 過濾階段 ===")
    typer.echo(f"資格集合大小：{n_pairs} 個合法配對；{n_with_options} 位角色至少有一個可分配對象。")

    typer.echo("")
    typer.echo(f"=== 分配階段（{audit['mechanism']} 純抽籤）===")
    typer.echo(f"seed：{audit['seed']}")
    typer.echo("最終配對：")

    role_attrs = {r["id"]: r["attributes"] for r in audit["roster_snapshot"]["roles"]}
    target_attrs = {t["id"]: t["attributes"] for t in audit["roster_snapshot"]["targets"]}
    for role_id in sorted(audit["assignment"]):
        target_id = audit["assignment"][role_id]
        ra = role_attrs.get(role_id, {})
        if target_id is None:
            typer.echo(f"  {role_id}（{ra.get('name', '')}）→ 未分配")
        else:
            ta = target_attrs.get(target_id, {})
            typer.echo(
                f"  {role_id}（{ra.get('name', '')}）→ {target_id}（{ta.get('name', '')}）"
            )


def _die(err: MatcherError) -> None:
    typer.echo(f"錯誤：{err}", err=True)
    raise typer.Exit(code=err.exit_code)


@app.command("run")
def run_cmd(
    rules: Optional[Path] = typer.Option(None, "--rules", exists=True, dir_okay=False, readable=True),
    roster: Optional[Path] = typer.Option(None, "--roster", exists=True, dir_okay=False, readable=True),
    roster_csv: Optional[Path] = typer.Option(
        None, "--roster-csv", exists=True, dir_okay=False, readable=True,
        help="從 CSV 匯入名單；需附旁檔 <stem>.targets.yaml",
    ),
    roster_xlsx: Optional[Path] = typer.Option(
        None, "--roster-xlsx", exists=True, dir_okay=False, readable=True,
        help="從 Excel .xlsx 匯入名單；需附旁檔 <stem>.targets.yaml",
    ),
    sheet: Optional[str] = typer.Option(None, "--sheet", help="Excel 工作表名稱（多表時必填）"),
    seed: Optional[int] = typer.Option(None, "--seed", help="整數隨機種子（必填）"),
    preferences: Optional[Path] = typer.Option(
        None, "--preferences", exists=True, dir_okay=False, readable=True
    ),
    mechanism: str = typer.Option("M0", "--mechanism"),
    output: Path = typer.Option(Path("audit.json"), "--output"),
    template: Optional[str] = typer.Option(None, "--template", help="使用內建模板的 id"),
    template_file: Optional[Path] = typer.Option(
        None, "--template-file", exists=True, dir_okay=False, readable=True,
        help="使用外部模板檔",
    ),
) -> None:
    """執行一次完整媒合（過濾 → 分配 → 寫稽核）。"""
    # 規則來源三組互斥檢查
    n_rules_source = sum([template is not None, template_file is not None, rules is not None])
    if n_rules_source == 0:
        typer.echo(
            "錯誤：請提供下列三組之一的規則來源——\n"
            "  (A) --template <id>\n"
            "  (B) --template-file <path>\n"
            "  (C) --rules <path>",
            err=True,
        )
        raise typer.Exit(code=2)
    if n_rules_source > 1:
        typer.echo(
            "錯誤：--template / --template-file / --rules 三組參數互斥，請擇一。",
            err=True,
        )
        raise typer.Exit(code=2)

    # 名單來源三組互斥檢查
    n_roster_source = sum([roster is not None, roster_csv is not None, roster_xlsx is not None])
    if n_roster_source == 0:
        typer.echo(
            "錯誤：請提供下列三組之一的名單來源——\n"
            "  (A) --roster <yaml>\n"
            "  (B) --roster-csv <path>\n"
            "  (C) --roster-xlsx <path> [--sheet <name>]",
            err=True,
        )
        raise typer.Exit(code=2)
    if n_roster_source > 1:
        typer.echo(
            "錯誤：--roster / --roster-csv / --roster-xlsx 三組參數互斥，請擇一。",
            err=True,
        )
        raise typer.Exit(code=2)

    if seed is None:
        _die(SeedMissing("seed 未提供。\n建議：以 --seed <整數> 提供隨機種子。"))

    try:
        tpl_obj = None
        if template is not None:
            reg = TemplateRegistry()
            tpl_obj = reg.get(template)
            rs = tpl_obj.ruleset
        elif template_file is not None:
            tpl_obj = load_template(template_file)
            rs = tpl_obj.ruleset
        else:
            rs = load_ruleset(rules)

        # 名單載入
        import_metadata: Optional[dict] = None
        if roster_csv is not None:
            if tpl_obj is None:
                typer.echo(
                    "錯誤：--roster-csv 必須搭配 --template 或 --template-file 使用。\n"
                    "細節：CSV 匯入依賴模板的 attributes schema 對齊欄位。\n"
                    "建議：加上 --template <id> 或改用 --roster <yaml>。",
                    err=True,
                )
                raise typer.Exit(code=2)
            ro, import_metadata = load_roster_csv(roster_csv, tpl_obj)
        elif roster_xlsx is not None:
            if tpl_obj is None:
                typer.echo(
                    "錯誤：--roster-xlsx 必須搭配 --template 或 --template-file 使用。\n"
                    "細節：Excel 匯入依賴模板的 attributes schema 對齊欄位。\n"
                    "建議：加上 --template <id> 或改用 --roster <yaml>。",
                    err=True,
                )
                raise typer.Exit(code=2)
            ro, import_metadata = load_roster_xlsx(roster_xlsx, tpl_obj, sheet=sheet)
        else:
            ro = load_roster(roster)

        prefs = load_preferences(preferences)

        result = run_match(MatcherInput(
            ruleset=rs,
            roster=ro,
            seed=seed,
            preferences=prefs if prefs else None,
            mechanism=mechanism,
            template=tpl_obj,
            import_metadata=import_metadata,
        ))
    except MatcherError as e:
        _die(e)

    dump_audit_json(result.audit, output)
    _print_summary(result.audit)
    if result.audit.get("import_metadata"):
        meta = result.audit["import_metadata"]
        typer.echo("")
        typer.echo("=== 資料來源 ===")
        typer.echo(f"類型：{meta['source_type']}")
        if meta.get("encoding"):
            typer.echo(f"編碼：{meta['encoding']}")
        if meta.get("sheet_name"):
            typer.echo(f"工作表：{meta['sheet_name']}")
        typer.echo(f"資料列數：{meta['row_count']}")
        typer.echo(f"檔案：{meta['file_basename']}")
    typer.echo("")
    typer.echo("=== 完成 ===")
    typer.echo(f"稽核紀錄已寫入：{output}")


@app.command("filter")
def filter_cmd(
    rules: Path = typer.Option(..., "--rules", exists=True, dir_okay=False, readable=True),
    roster: Path = typer.Option(..., "--roster", exists=True, dir_okay=False, readable=True),
    output: Path = typer.Option(Path("qualified.json"), "--output"),
) -> None:
    """只執行過濾階段（FR-005），不需要 seed。"""
    try:
        rs = load_ruleset(rules)
        ro = load_roster(roster)
        qs, trace = run_filter_only(rs, ro)
    except MatcherError as e:
        _die(e)

    payload = {
        "qualified_set": qs,
        "filter_trace": trace,
    }
    s = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2)
    output.write_text(s + "\n", encoding="utf-8")

    n_pairs = sum(len(v) for v in qs.values())
    typer.echo(f"資格集合大小：{n_pairs} 個合法配對。")
    typer.echo(f"已寫入：{output}")


# ── matcher template ────────────────────────────────────────────────


@template_app.command("list")
def template_list_cmd() -> None:
    """列出所有內建模板。"""
    reg = TemplateRegistry()
    typer.echo(f"{'ID':<16}{'名稱':<20}{'一句話描述'}")
    typer.echo(f"{'-' * 14:<16}{'-' * 18:<20}{'-' * 40}")
    for tid in reg.list_ids():
        tpl = reg.get(tid)
        typer.echo(f"{tpl.id:<16}{tpl.name:<20}{tpl.description}")


@template_app.command("show")
def template_show_cmd(
    template_id: str = typer.Argument(..., help="模板 id"),
    format: str = typer.Option("text", "--format", help="text | yaml | json"),
) -> None:
    """顯示指定模板的完整內容。"""
    reg = TemplateRegistry()
    try:
        tpl = reg.get(template_id)
    except MatcherError as e:
        _die(e)

    if format == "yaml":
        import tempfile
        tmp = Path(tempfile.mkstemp(suffix=".yaml")[1])
        dump_template_yaml(tpl, tmp)
        typer.echo(tmp.read_text(encoding="utf-8"))
        tmp.unlink(missing_ok=True)
        return
    if format == "json":
        from matcher.audit import _template_to_dict
        s = json.dumps(_template_to_dict(tpl), ensure_ascii=False, sort_keys=True, indent=2)
        typer.echo(s)
        return

    # text（預設）
    typer.echo(f"ID：{tpl.id}")
    typer.echo(f"名稱：{tpl.name}")
    typer.echo(f"描述：{tpl.description}")
    typer.echo(f"版本：{tpl.schema_version}")
    typer.echo("")
    typer.echo("=== 屬性 schema ===")
    typer.echo("角色：")
    for a in tpl.attributes.roles:
        typer.echo(f"  - {a.key}（{a.type}）：{a.description}")
    typer.echo("對象：")
    for a in tpl.attributes.targets:
        typer.echo(f"  - {a.key}（{a.type}）：{a.description}")
    typer.echo("")
    typer.echo("=== 規則 ===")
    for r in tpl.ruleset.rules:
        typer.echo(f"  {r.id}：{r.description}")
    if tpl.ui_fields:
        typer.echo("")
        typer.echo("=== UI 欄位宣告 ===")
        for u in tpl.ui_fields:
            typer.echo(f"  {u.key}（{u.type}）：{u.label}")
    if tpl.report_fields:
        typer.echo("")
        typer.echo("=== 稽核報告欄位宣告 ===")
        for rf in tpl.report_fields:
            typer.echo(f"  {rf.key}：{rf.label} ← {rf.source}")
    if tpl.preferences_schema is not None:
        ps = tpl.preferences_schema
        typer.echo("")
        typer.echo("=== preferences schema ===")
        typer.echo(f"  最多可填 {ps.max_choices} 個志願；強制：{ps.required}")
        typer.echo(f"  說明：{ps.description}")


@template_app.command("export")
def template_export_cmd(
    template_id: str = typer.Argument(..., help="模板 id"),
    output: Path = typer.Option(..., "--output", help="匯出檔路徑"),
) -> None:
    """匯出指定模板為單一 YAML 檔。"""
    reg = TemplateRegistry()
    try:
        tpl = reg.get(template_id)
    except MatcherError as e:
        _die(e)
    dump_template_yaml(tpl, output)
    typer.echo(f"已匯出 `{template_id}` 至：{output}")


if __name__ == "__main__":
    app()

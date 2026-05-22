"""CLI（Typer）：matcher run / matcher filter。"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import typer

from matcher.audit import dump_audit_json
from matcher.errors import MatcherError, SeedMissing
from matcher.io_yaml import load_preferences, load_roster, load_ruleset
from matcher.pipeline import MatcherInput, run_filter_only, run_match

app = typer.Typer(
    add_completion=False,
    help="matcher：核心媒合引擎。依規則過濾出資格集合，於 M0 純抽籤分支下完成分配。",
)


def _print_summary(audit: dict) -> None:
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
    rules: Path = typer.Option(..., "--rules", exists=True, dir_okay=False, readable=True),
    roster: Path = typer.Option(..., "--roster", exists=True, dir_okay=False, readable=True),
    seed: Optional[int] = typer.Option(None, "--seed", help="整數隨機種子（必填）"),
    preferences: Optional[Path] = typer.Option(
        None, "--preferences", exists=True, dir_okay=False, readable=True
    ),
    mechanism: str = typer.Option("M0", "--mechanism"),
    output: Path = typer.Option(Path("audit.json"), "--output"),
) -> None:
    """執行一次完整媒合（過濾 → 分配 → 寫稽核）。"""
    if seed is None:
        _die(SeedMissing("seed 未提供。\n建議：以 --seed <整數> 提供隨機種子。"))

    try:
        rs = load_ruleset(rules)
        ro = load_roster(roster)
        prefs = load_preferences(preferences)

        result = run_match(MatcherInput(
            ruleset=rs,
            roster=ro,
            seed=seed,
            preferences=prefs if prefs else None,
            mechanism=mechanism,
        ))
    except MatcherError as e:
        _die(e)

    dump_audit_json(result.audit, output)
    _print_summary(result.audit)
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


if __name__ == "__main__":
    app()

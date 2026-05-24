"""Feature 008 T014/T015：Web 與 CLI 同 mechanism+seed 跑出 audit 五段 bytewise 相等。"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from matcher.cli import app as cli_app
from matcher.web.app import create_app

ROOT = Path(__file__).resolve().parents[2]
FIVE_KEYS = ["qualified_set", "assignment", "filter_trace",
             "allocation_trace", "template_snapshot"]


def _client(tmp_path: Path) -> TestClient:
    import matcher.web.store as store_mod
    store_mod.MatchStore.__init__.__defaults__ = (tmp_path,)
    return TestClient(create_app())


def _web_audit(c: TestClient, mechanism: str) -> dict:
    csv_path = ROOT / "examples" / "study-group" / "roster-m1.csv"
    with csv_path.open("rb") as f:
        r = c.post(
            "/match/run",
            data={"template_id": "study-group", "seed": "2026", "mechanism": mechanism},
            files={"roster": ("roster-m1.csv", f, "text/csv")},
        )
    assert r.status_code == 200, r.text
    m = re.search(r'<code>([0-9T:-]+-[a-f0-9]{8})</code>', r.text)
    assert m
    rid = m.group(1)
    return json.loads(c.get(f"/match/{rid}/audit").content)


def _cli_audit(tmp_path: Path, mechanism: str) -> dict:
    out = tmp_path / "cli.json"
    csv_path = ROOT / "examples" / "study-group" / "roster-m1.csv"
    runner = CliRunner()
    r = runner.invoke(cli_app, [
        "run",
        "--template", "study-group",
        "--roster-csv", str(csv_path),
        "--seed", "2026",
        "--mechanism", mechanism,
        "--output", str(out),
    ])
    assert r.exit_code == 0, r.output
    return json.loads(out.read_text(encoding="utf-8"))


@pytest.mark.parametrize("mechanism", ["M1", "M2"])
def test_web_cli_audit_five_keys_equal(tmp_path: Path, mechanism: str):
    web_dir = tmp_path / "web"
    web_dir.mkdir()
    cli_dir = tmp_path / "cli"
    cli_dir.mkdir()

    web = _web_audit(_client(web_dir), mechanism)
    cli = _cli_audit(cli_dir, mechanism)

    for key in FIVE_KEYS:
        s_w = json.dumps(web[key], sort_keys=True, ensure_ascii=False)
        s_c = json.dumps(cli[key], sort_keys=True, ensure_ascii=False)
        assert s_w == s_c, f"{key} 不相等（mechanism={mechanism}）"

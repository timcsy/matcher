"""Feature 009 SC-007：50 學生 × 3 志願 規模測試。"""

from __future__ import annotations

import json
import re
from pathlib import Path

from fastapi.testclient import TestClient

from matcher.web.app import create_app

ROOT = Path(__file__).resolve().parents[2]


def _client(tmp_path: Path) -> TestClient:
    import matcher.web.store as store_mod
    store_mod.MatchStore.__init__.__defaults__ = (tmp_path,)
    return TestClient(create_app())


def test_50_students_3_choices_renders_and_submits(tmp_path: Path):
    """T050：50 學生 → 表單含 150 個 select → POST 成功。"""
    # 注意：study-group 內建 default_targets G1/G2/G3 各 capacity=3，總共僅 9 個 slot
    # 50 學生會大量未分配，但 audit 仍應產生（M1 處理流程正常）
    c = _client(tmp_path)
    lines = ["id,姓名,年級,志願組別"]
    for i in range(1, 51):
        lines.append(f"S{i:02d},S{i},5,")
    csv = ("\n".join(lines) + "\n").encode("utf-8")

    r1 = c.post(
        "/match/run",
        data={"template_id": "study-group", "seed": "1", "mechanism": "M1"},
        files={"roster": ("big.csv", csv, "text/csv")},
    )
    assert r1.status_code == 200
    selects = re.findall(r'<select name="pref_S\d{2}_\d"', r1.text)
    assert len(selects) == 150, f"預期 150 個 select、實際 {len(selects)}"

    hidden = {}
    for m in re.finditer(r'<input[^>]*type="hidden"[^>]*name="(\w+)"[^>]*value="([^"]*)"', r1.text):
        hidden[m.group(1)] = m.group(2)

    # 50 學生輪流選 G1/G2/G3 第一志願；前 9 個拿到一志願、其餘走 fallback
    data = {**hidden, "_action": "submit"}
    targets = ["G1", "G2", "G3"]
    for i in range(1, 51):
        rid = f"S{i:02d}"
        data[f"pref_{rid}_1"] = targets[(i - 1) % 3]
        data[f"pref_{rid}_2"] = ""
        data[f"pref_{rid}_3"] = ""

    r2 = c.post("/match/preferences", data=data)
    assert r2.status_code == 200, r2.text
    assert "媒合完成" in r2.text or "媒合失敗" in r2.text

    if "媒合完成" in r2.text:
        m = re.search(r'<code>([0-9T:-]+-[a-f0-9]{8})</code>', r2.text)
        rid = m.group(1)
        audit = json.loads(c.get(f"/match/{rid}/audit").content)
        assert audit["mechanism"] == "M1"
        assert len(audit["roster_snapshot"]["roles"]) == 50

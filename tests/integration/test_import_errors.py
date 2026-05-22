"""US3：匯入錯誤路徑（4 種情境）。"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from matcher.cli import app

runner = CliRunner()
ROOT = Path(__file__).resolve().parents[2]


def _make_targets_sidecar(tmp_path: Path, name: str) -> None:
    """為 tmp 目錄下的 CSV/xlsx 建立對應的 targets 旁檔。"""
    p = tmp_path / f"{name}.targets.yaml"
    p.write_bytes((ROOT / "examples" / "teacher-class" / "roster.targets.yaml").read_bytes())


def test_csv_decode_error(tmp_path: Path):
    """UTF-16 編碼 → exit 30。"""
    csv = tmp_path / "bad.csv"
    csv.write_bytes("姓名,專業科目,年資\n王老師,國文,8\n".encode("utf-16"))
    _make_targets_sidecar(tmp_path, "bad")
    r = runner.invoke(app, [
        "run", "--template", "teacher-class",
        "--roster-csv", str(csv), "--seed", "1",
        "--output", str(tmp_path / "a.json"),
    ])
    assert r.exit_code == 30
    msg = r.output + (r.stderr or "")
    assert "無法解碼" in msg
    assert "cp950" in msg


def test_csv_missing_column(tmp_path: Path):
    """缺必填欄位 → exit 31，訊息列出 aliases。"""
    csv = tmp_path / "missing.csv"
    csv.write_text("姓名,年資\n王老師,8\n", encoding="utf-8")  # 缺「專業科目」
    _make_targets_sidecar(tmp_path, "missing")
    r = runner.invoke(app, [
        "run", "--template", "teacher-class",
        "--roster-csv", str(csv), "--seed", "1",
        "--output", str(tmp_path / "a.json"),
    ])
    assert r.exit_code == 31
    msg = r.output + (r.stderr or "")
    assert "缺少" in msg
    assert "speciality" in msg
    assert "專業科目" in msg


def test_csv_duplicate_column(tmp_path: Path):
    """重複欄位 → exit 31。"""
    csv = tmp_path / "dup.csv"
    csv.write_text("姓名,姓名,專業科目,年資\n王,王,國文,8\n", encoding="utf-8")
    _make_targets_sidecar(tmp_path, "dup")
    r = runner.invoke(app, [
        "run", "--template", "teacher-class",
        "--roster-csv", str(csv), "--seed", "1",
        "--output", str(tmp_path / "a.json"),
    ])
    assert r.exit_code == 31
    assert "重複" in (r.output + (r.stderr or ""))


def test_csv_type_error(tmp_path: Path):
    """int 欄填中文 → exit 32。"""
    csv = tmp_path / "badtype.csv"
    csv.write_text("姓名,專業科目,年資\n王老師,國文,八年\n", encoding="utf-8")
    _make_targets_sidecar(tmp_path, "badtype")
    r = runner.invoke(app, [
        "run", "--template", "teacher-class",
        "--roster-csv", str(csv), "--seed", "1",
        "--output", str(tmp_path / "a.json"),
    ])
    assert r.exit_code == 32
    msg = r.output + (r.stderr or "")
    assert "八年" in msg
    assert "型別" in msg

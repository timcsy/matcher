"""Feature 011 Phase 2：TemplateRegistry 自訂模板掃描與版本控制。"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from matcher.template_loader import TemplateRegistry


def _minimal_tpl_dict(tpl_id: str) -> dict:
    return {
        "schema_version": "1.0",
        "id": tpl_id,
        "name": f"測試模板 {tpl_id}",
        "description": "單元測試用",
        "attributes": {
            "participants": [{"key": "name", "type": "str", "required": True, "description": "姓名"}],
            "targets": [{"key": "name", "type": "str", "required": True, "description": "對象名"}],
        },
        "rules": [
            {"id": "R001", "description": "至少需要一條規則", "expr": {"eq": {"field": "participant.name", "value": "any"}}}
        ],
    }


def test_scan_empty_custom_dir_works(tmp_path: Path):
    custom = tmp_path / "templates"
    custom.mkdir()
    reg = TemplateRegistry(custom_dir=custom)
    # builtin 仍應在
    assert "teacher-class" in reg.list_ids()
    assert "study-group" in reg.list_ids()


def test_scan_custom_template_v1(tmp_path: Path):
    custom = tmp_path / "templates"
    tpl_dir = custom / "my-tpl"
    tpl_dir.mkdir(parents=True)
    (tpl_dir / "v1.yaml").write_text(
        yaml.safe_dump(_minimal_tpl_dict("my-tpl"), allow_unicode=True), encoding="utf-8"
    )

    reg = TemplateRegistry(custom_dir=custom)
    assert "my-tpl" in reg.list_ids()
    assert reg.is_builtin("my-tpl") is False
    assert reg.is_builtin("teacher-class") is True
    assert reg.list_versions("my-tpl") == [1]
    assert reg.list_versions("teacher-class") == []


def test_get_returns_latest_version(tmp_path: Path):
    custom = tmp_path / "templates"
    tpl_dir = custom / "my-tpl"
    tpl_dir.mkdir(parents=True)
    for v in (1, 2, 3):
        d = _minimal_tpl_dict("my-tpl")
        d["name"] = f"版本 {v}"
        (tpl_dir / f"v{v}.yaml").write_text(
            yaml.safe_dump(d, allow_unicode=True), encoding="utf-8"
        )

    reg = TemplateRegistry(custom_dir=custom)
    assert reg.get("my-tpl").name == "版本 3"
    assert reg.get_version("my-tpl", 1).name == "版本 1"
    assert reg.get_version("my-tpl", 2).name == "版本 2"
    assert reg.list_versions("my-tpl") == [1, 2, 3]


def test_save_custom_writes_v1_then_v2(tmp_path: Path):
    custom = tmp_path / "templates"
    custom.mkdir()
    reg = TemplateRegistry(custom_dir=custom)

    tpl_id, v = reg.save_custom(_minimal_tpl_dict("club"))
    assert tpl_id == "club"
    assert v == 1
    assert (custom / "club" / "v1.yaml").exists()

    d2 = _minimal_tpl_dict("club")
    d2["name"] = "更新後"
    tpl_id2, v2 = reg.save_custom(d2)
    assert v2 == 2
    assert (custom / "club" / "v2.yaml").exists()
    assert reg.get("club").name == "更新後"


def test_save_custom_rejects_builtin_id(tmp_path: Path):
    custom = tmp_path / "templates"
    custom.mkdir()
    reg = TemplateRegistry(custom_dir=custom)
    with pytest.raises(ValueError, match="已存在於內建模板"):
        reg.save_custom(_minimal_tpl_dict("teacher-class"))


def test_invalidate_picks_up_new_template(tmp_path: Path):
    custom = tmp_path / "templates"
    custom.mkdir()
    reg = TemplateRegistry(custom_dir=custom)
    assert "new-tpl" not in reg.list_ids()

    # 模擬外部寫檔
    (custom / "new-tpl").mkdir()
    (custom / "new-tpl" / "v1.yaml").write_text(
        yaml.safe_dump(_minimal_tpl_dict("new-tpl"), allow_unicode=True), encoding="utf-8"
    )
    reg.invalidate()
    assert "new-tpl" in reg.list_ids()


def test_is_builtin_distinguishes_correctly(tmp_path: Path):
    custom = tmp_path / "templates"
    custom.mkdir()
    reg = TemplateRegistry(custom_dir=custom)
    assert reg.is_builtin("teacher-class") is True
    assert reg.is_builtin("study-group") is True
    assert reg.is_builtin("nonexistent") is False
    reg.save_custom(_minimal_tpl_dict("custom-one"))
    assert reg.is_builtin("custom-one") is False


def test_save_custom_rejects_invalid_id_format(tmp_path: Path):
    custom = tmp_path / "templates"
    custom.mkdir()
    reg = TemplateRegistry(custom_dir=custom)
    bad = _minimal_tpl_dict("Bad ID With Spaces")
    bad["id"] = "Bad ID With Spaces"
    with pytest.raises(ValueError, match="格式不合法"):
        reg.save_custom(bad)

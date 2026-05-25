"""US2：Web 頁面整合測試。"""

from __future__ import annotations

from fastapi.testclient import TestClient

from matcher.web.app import create_app

client = TestClient(create_app())


def test_index():
    r = client.get("/")
    assert r.status_code == 200
    assert "新增一次配對" in r.text
    assert "所有範本" in r.text
    assert "過去紀錄" in r.text


def test_templates_list():
    r = client.get("/templates")
    assert r.status_code == 200
    assert "teacher-class" in r.text
    assert "study-group" in r.text
    assert "教師-班級配對" in r.text
    assert "研習分組" in r.text


def test_template_detail_teacher_class():
    r = client.get("/templates/teacher-class")
    assert r.status_code == 200
    assert "R001" in r.text
    assert "R002" in r.text
    assert "R003" in r.text
    # Feature 013：移除預設對象區段


def test_template_detail_study_group_has_preferences():
    r = client.get("/templates/study-group")
    assert r.status_code == 200
    assert "preferences" in r.text or "志願" in r.text
    assert "本階段" in r.text  # preferences 提示


def test_template_not_found():
    r = client.get("/templates/no-such")
    assert r.status_code == 404
    assert "找不到模板" in r.text


def test_html_lang_attribute():
    """所有頁面必須宣告 lang=zh-Hant。"""
    for path in ["/", "/templates", "/templates/teacher-class", "/match/new", "/matches"]:
        r = client.get(path)
        assert r.status_code == 200, f"{path} returned {r.status_code}"
        assert 'lang="zh-Hant"' in r.text, f"{path} missing zh-Hant lang"

"""Feature 008 T018：humanize 模組的 mechanism 與志願排名顯示函式。"""

from __future__ import annotations

import pytest

from matcher.web.humanize import (
    mechanism_label,
    mechanism_description,
    preference_rank_display,
)


@pytest.mark.parametrize("code,label", [
    ("M0", "純抽籤"),
    ("M1", "輪流挑"),
    ("M2", "依志願先後填滿"),
])
def test_mechanism_label_known(code: str, label: str):
    assert mechanism_label(code) == label


def test_mechanism_label_unknown_passthrough():
    assert mechanism_label("M99") == "M99"


def test_mechanism_description_known():
    """每個 mechanism 都有對應的白話說明。"""
    assert "公平隨機" in mechanism_description("M0")
    assert "隨機" in mechanism_description("M1")
    assert "第一志願" in mechanism_description("M2")


def test_preference_rank_display_m0_returns_none():
    assert preference_rank_display("M0", None, None) is None
    assert preference_rank_display("M0", 1, None) is None


def test_preference_rank_display_m1_with_rank():
    assert preference_rank_display("M1", 1, None) == "第 1 志願"
    assert preference_rank_display("M1", 3, None) == "第 3 志願"


def test_preference_rank_display_m2_fallback():
    assert preference_rank_display("M2", None, 0) == "抽籤"
    assert preference_rank_display("M2", None, 5) == "抽籤"


def test_preference_rank_display_m1_neither():
    assert preference_rank_display("M1", None, None) == ""

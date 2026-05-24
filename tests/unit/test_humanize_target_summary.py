"""Feature 009 T001：humanize.target_summary 純函式。"""

from __future__ import annotations

from matcher.web.humanize import target_summary


def test_target_summary_basic():
    assert target_summary({"id": "G1", "name": "程式組", "capacity": 3}) == "程式組（容量 3 人）"


def test_target_summary_name_fallback_to_id():
    assert target_summary({"id": "G1", "capacity": 3}) == "G1（容量 3 人）"


def test_target_summary_no_capacity_shows_name_only():
    assert target_summary({"id": "G1", "name": "程式組"}) == "程式組"


def test_target_summary_only_id():
    assert target_summary({"id": "G1"}) == "G1"


def test_target_summary_capacity_one():
    assert target_summary({"id": "G1", "name": "程式組", "capacity": 1}) == "程式組（容量 1 人）"

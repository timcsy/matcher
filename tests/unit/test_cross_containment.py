"""Feature 019：跨側包含（participant_in_target_field）對稱化——不論哪邊是清單都聰明判斷。

語意：
- 兩邊單值 → 相等
- 參與者單值、對象清單 → 參與者值 ∈ 對象清單（原行為，內建 teacher-class 用）
- 參與者清單、對象單值 → 對象值 ∈ 參與者清單（teacher-class-allocation 用）
- 兩邊清單 → 交集非空
"""

from __future__ import annotations

from matcher.rules import ParticipantInTargetField, evaluate

R = ParticipantInTargetField(participant_field="subjects", target_field="category")


def _ev(pv, tv):
    return evaluate(R, {"subjects": pv}, {"category": tv})


def test_both_single():
    assert _ev("第一類組", "第一類組") is True
    assert _ev("第一類組", "第二類組") is False


def test_participant_single_target_list():
    # 原行為：老師專業（單） ∈ 班級需要科目（清單）
    assert _ev("數學", ["數學", "英文"]) is True
    assert _ev("國文", ["數學", "英文"]) is False


def test_participant_list_target_single():
    # teacher-class-allocation：班級類組（單） ∈ 老師可帶類組（清單）
    assert _ev(["第一類組"], "第一類組") is True
    assert _ev(["第一類組", "第二類組"], "第二類組") is True
    assert _ev(["第一類組"], "第二類組") is False


def test_both_lists_intersection():
    assert _ev(["第一類組", "第二類組"], ["第二類組", "第三類組"]) is True
    assert _ev(["第一類組"], ["第二類組", "第三類組"]) is False

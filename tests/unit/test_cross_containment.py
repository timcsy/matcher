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


# ── 明確模式覆寫（feature 019 後續：自動判斷＋可手動覆寫）──

def _evm(mode, pv, tv):
    r = ParticipantInTargetField(participant_field="subjects", target_field="category", mode=mode)
    return evaluate(r, {"subjects": pv}, {"category": tv})


def test_mode_default_is_auto():
    # 不給 mode → auto；與不帶 mode 的物件行為一致
    assert ParticipantInTargetField("a", "b").mode == "auto"


def test_mode_equal():
    assert _evm("equal", "第一類組", "第一類組") is True
    assert _evm("equal", "第一類組", "第二類組") is False
    assert _evm("equal", ["第一類組", "第二類組"], ["第二類組", "第一類組"]) is True  # 集合相等、順序無關


def test_mode_participant_in_target():  # P ⊆ T
    assert _evm("participant_in_target", "數學", ["數學", "英文"]) is True       # 1:N
    assert _evm("participant_in_target", ["第一類組"], ["第一類組", "第二類組"]) is True  # N:N 子集
    assert _evm("participant_in_target", ["第一類組", "第三類組"], ["第一類組"]) is False


def test_mode_target_in_participant():  # T ⊆ P
    assert _evm("target_in_participant", ["第一類組", "第二類組"], "第一類組") is True  # N:1
    assert _evm("target_in_participant", ["第一類組"], "第二類組") is False


def test_mode_intersect():
    assert _evm("intersect", ["第一類組", "第二類組"], ["第二類組", "第三類組"]) is True
    assert _evm("intersect", ["第一類組"], ["第二類組"]) is False


def test_unknown_mode_rejected():
    import pytest

    from matcher.errors import UnknownAttribute
    from matcher.rules import parse_expr
    with pytest.raises(UnknownAttribute):
        parse_expr({"participant_in_target_field":
                    {"participant_field": "a", "target_field": "b", "mode": "bogus"}})


def test_form_assembly_carries_mode_and_description():
    # 表單（含 mode）→ YAML dict → parse → evaluate 全程
    from matcher.web.template_form import _auto_description, _build_expr
    fields = {"participant_field": "subjects", "target_field": "category",
              "mode": "target_in_participant"}
    expr = _build_expr("participant_in_target_field", fields)
    assert expr["participant_in_target_field"]["mode"] == "target_in_participant"
    desc = _auto_description("participant_in_target_field", fields, {})
    assert "都在" in desc  # 「對象的… 必須都在…裡」
    # auto 時不寫 mode（保 golden）
    auto = _build_expr("participant_in_target_field",
                       {"participant_field": "a", "target_field": "b", "mode": "auto"})
    assert "mode" not in auto["participant_in_target_field"]


# ── 空=不設限（feature 021：empty_ok checkbox）──

def test_empty_ok_passes_when_a_side_empty_or_missing():
    r = ParticipantInTargetField(participant_field="subjects", target_field="category", mode="intersect", empty_ok=True)
    # 對象沒填值（空清單）→ 不設限 → 通過
    assert evaluate(r, {"subjects": ["第一類組"]}, {"category": []}) is True
    # 對象缺整個屬性 → 不設限 → 通過（不再 UnknownAttribute）
    assert evaluate(r, {"subjects": ["第一類組"]}, {}) is True
    # 參與者空字串 → 通過
    assert evaluate(r, {"subjects": ""}, {"category": "第二類組"}) is True
    # 兩邊都有值且非空 → 照常比對（intersect）
    assert evaluate(r, {"subjects": ["第一類組"]}, {"category": "第二類組"}) is False
    assert evaluate(r, {"subjects": ["第一類組"]}, {"category": "第一類組"}) is True


def test_empty_ok_default_off_keeps_strict():
    r = ParticipantInTargetField(participant_field="subjects", target_field="category", mode="intersect")
    assert r.empty_ok is False
    # 預設嚴格：對象缺屬性 → UnknownAttribute（維持現狀）
    import pytest
    from matcher.errors import UnknownAttribute
    with pytest.raises(UnknownAttribute):
        evaluate(r, {"subjects": ["第一類組"]}, {})


def test_empty_ok_parses_from_dsl():
    from matcher.rules import parse_expr
    e = parse_expr({"participant_in_target_field": {
        "participant_field": "subjects", "target_field": "category", "empty_ok": True}})
    assert e.empty_ok is True


def test_empty_ok_pipeline_tolerates_missing_target_attr():
    # 含 empty_ok 規則時，對象缺該屬性不應在 pipeline 靜態檢查報錯
    from matcher.roster import Roster, Participant, Target
    from matcher.rules import Rule, Ruleset
    from matcher.pipeline import _validate_attribute_references
    rs = Ruleset(rules=(Rule(id="R1", description="x",
        expr=ParticipantInTargetField(participant_field="subjects", target_field="category",
                                       mode="intersect", empty_ok=True)),))
    roster = Roster(
        participants=(Participant(id="T1", attributes={"subjects": ["第一類組"]}),),
        targets=(Target(id="C1", capacity=1, attributes={"name": "203"}),))  # 無 category
    _validate_attribute_references(rs, roster)  # 不應拋例外

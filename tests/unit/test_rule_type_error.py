"""Feature 017：ge/le 用在非數值屬性 → 友善 RuleTypeError（非裸 TypeError）。"""

from __future__ import annotations

import pytest

from matcher.errors import RuleTypeError
from matcher.rules import Ge, Le, evaluate


def test_ge_on_string_raises_rule_type_error():
    with pytest.raises(RuleTypeError) as ei:
        evaluate(Ge("participant.seniority", 3), {"seniority": "資深"}, {})
    assert "seniority" in str(ei.value)
    # 是可預期的 MatcherError（有退出碼），不是裸 TypeError
    assert ei.value.exit_code == 18


def test_le_on_string_raises_rule_type_error():
    with pytest.raises(RuleTypeError):
        evaluate(Le("target.min_grade", 5), {}, {"min_grade": "高年級"})


def test_ge_on_bool_raises():
    # bool 不算數值（避免 True>=1 之類的意外通過）
    with pytest.raises(RuleTypeError):
        evaluate(Ge("participant.x", 1), {"x": True}, {})


def test_ge_on_int_still_works():
    assert evaluate(Ge("participant.seniority", 3), {"seniority": 5}, {}) is True
    assert evaluate(Ge("participant.seniority", 3), {"seniority": 2}, {}) is False

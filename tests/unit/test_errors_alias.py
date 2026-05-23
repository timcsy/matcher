"""Foundational：MechanismRequiresPreferences alias 測試。"""

from __future__ import annotations

from matcher.errors import M1RequiresPreferences, MechanismRequiresPreferences


def test_alias_is_same_class():
    assert M1RequiresPreferences is MechanismRequiresPreferences


def test_exit_code_unchanged():
    assert MechanismRequiresPreferences.exit_code == 40
    assert M1RequiresPreferences.exit_code == 40


def test_isinstance_via_alias():
    exc = MechanismRequiresPreferences("test")
    assert isinstance(exc, M1RequiresPreferences)


def test_raise_via_old_name():
    """既有測試以 M1RequiresPreferences 拋出仍能正常運作。"""
    import pytest
    with pytest.raises(MechanismRequiresPreferences):
        raise M1RequiresPreferences("test")

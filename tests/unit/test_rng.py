"""US1：seedable RNG 與 Fisher–Yates 確定性。"""

from __future__ import annotations

import inspect

import pytest

from matcher.rng import SeededRandom, fisher_yates_shuffle


def test_same_seed_same_sequence():
    a = SeededRandom(42)
    b = SeededRandom(42)
    seq_a = [a.randrange(100) for _ in range(20)]
    seq_b = [b.randrange(100) for _ in range(20)]
    assert seq_a == seq_b


def test_different_seed_different_sequence():
    a = SeededRandom(42)
    b = SeededRandom(43)
    seq_a = [a.randrange(1000) for _ in range(20)]
    seq_b = [b.randrange(1000) for _ in range(20)]
    assert seq_a != seq_b


def test_seed_must_be_int():
    with pytest.raises(TypeError):
        SeededRandom("42")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        SeededRandom(True)  # type: ignore[arg-type]


def test_fisher_yates_determinism():
    items = list(range(10))
    a, idx_a = fisher_yates_shuffle(items, SeededRandom(1234))
    b, idx_b = fisher_yates_shuffle(items, SeededRandom(1234))
    assert a == b
    assert idx_a == idx_b


def test_fisher_yates_uses_only_randrange():
    """確保我們不偷偷用了 random.shuffle / sample / choices。"""
    src = inspect.getsource(fisher_yates_shuffle)
    for forbidden in (".shuffle(", ".sample(", ".choices("):
        assert forbidden not in src, f"fisher_yates_shuffle 不可使用 {forbidden}"

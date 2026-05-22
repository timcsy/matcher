"""可重現的 RNG 與顯式 Fisher–Yates 洗牌。

僅暴露 randrange；不使用 random.shuffle / sample / choices（見 research.md R-002）。
"""

from __future__ import annotations

import random
from typing import TypeVar

T = TypeVar("T")


class SeededRandom:
    def __init__(self, seed: int) -> None:
        if not isinstance(seed, int) or isinstance(seed, bool):
            raise TypeError(f"seed 必須為整數，得到 {type(seed).__name__}")
        self._rng = random.Random(seed)

    def randrange(self, n: int) -> int:
        if n <= 0:
            raise ValueError(f"randrange 需要 n > 0，得到 {n}")
        return self._rng.randrange(n)


def fisher_yates_shuffle(items: list[T], rng: SeededRandom) -> tuple[list[T], list[int]]:
    """顯式 Fisher–Yates 洗牌。

    回傳：(洗牌後的新 list, 每步抽取的索引序列)。
    每步紀錄使下游能將「索引序列」寫入稽核紀錄。
    """
    a = list(items)
    indices: list[int] = []
    n = len(a)
    for i in range(n - 1, 0, -1):
        j = rng.randrange(i + 1)
        indices.append(j)
        a[i], a[j] = a[j], a[i]
    return a, indices

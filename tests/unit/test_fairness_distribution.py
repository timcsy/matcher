"""Feature 017：統計公平性測試。

既有測試只驗「同 seed → 同結果」（determinism），抓不到「有偏差但仍確定」的 bug
（例如 Fisher-Yates off-by-one）。本測試跑多 seed 統計分布，守住「公平隨機」這個賣點。
"""

from __future__ import annotations

from collections import Counter

from matcher.rng import SeededRandom, fisher_yates_shuffle

N_SEEDS = 6000


def test_fisher_yates_position_distribution_uniform():
    """每個元素落在每個位置的頻率應接近均勻（n=4 → 各 1/4）。"""
    items = ["A", "B", "C", "D"]
    n = len(items)
    # pos_counts[element][position] = 次數
    pos_counts: dict[str, Counter] = {e: Counter() for e in items}
    for seed in range(N_SEEDS):
        shuffled, _ = fisher_yates_shuffle(items, SeededRandom(seed))
        for pos, e in enumerate(shuffled):
            pos_counts[e][pos] += 1

    expected = N_SEEDS / n
    tol = expected * 0.12  # ±12% 容差（6000 樣本下足夠穩定，又能抓出明顯偏差）
    for e in items:
        for pos in range(n):
            got = pos_counts[e][pos]
            assert abs(got - expected) < tol, (
                f"元素 {e} 落在位置 {pos} 的次數 {got} 偏離期望 {expected:.0f} 太多"
                f"（容差 ±{tol:.0f}）——洗牌可能有偏差"
            )


def test_fisher_yates_all_permutations_reachable():
    """n=3 的 6 種排列在多 seed 下都應出現，且頻率接近均勻。"""
    items = ["x", "y", "z"]
    perms = Counter()
    for seed in range(N_SEEDS):
        shuffled, _ = fisher_yates_shuffle(items, SeededRandom(seed))
        perms[tuple(shuffled)] += 1
    assert len(perms) == 6, f"只出現 {len(perms)} 種排列，應為 6 種"
    expected = N_SEEDS / 6
    for perm, count in perms.items():
        assert abs(count - expected) < expected * 0.15, (
            f"排列 {perm} 出現 {count} 次，偏離期望 {expected:.0f} 太多"
        )

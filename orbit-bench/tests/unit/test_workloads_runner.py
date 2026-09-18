"""Deterministic workloads + runner methodology on the memory backend."""

from orbitbench.backends.memory import MemoryBackend
from orbitbench.runner import run_scenario
from orbitbench.workloads import OpStream, SCENARIOS, Scenario, build_value, split_ops


def test_same_seed_same_ops():
    scenario = SCENARIOS["read_heavy"]
    a = [OpStream(42, scenario).next_op() for _ in range(50)]
    b = [OpStream(42, scenario).next_op() for _ in range(50)]
    c = [OpStream(43, scenario).next_op() for _ in range(50)]
    assert a == b
    assert a != c


def test_split_ops_sums_to_total():
    for workers in (1, 3, 8, 16):
        for total in (0, 1, 7, 100, 1000):
            counts = [len(chunk) for chunk in split_ops(total, workers)]
            assert sum(counts) == total


def test_build_value_respects_size():
    value = build_value(512, nonce=7)
    assert value["nonce"] == 7
    assert len(value["pad"]) == 512


async def test_runner_read_heavy_has_high_hit_ratio():
    backend = MemoryBackend()
    stats = await run_scenario(backend, SCENARIOS["read_heavy"], seed=42)

    assert stats.ops == 1000
    assert stats.errors == 0
    assert stats.reads > 0
    # prefilled key space + no eviction -> nearly all reads hit
    assert stats.hit_ratio > 0.85
    assert stats.ops_per_sec > 0
    assert len(stats.latencies_ms) == 1000


async def test_runner_hot_key_scenario():
    backend = MemoryBackend()
    scenario = SCENARIOS["hot_key"]
    stats = await run_scenario(backend, scenario, seed=42)
    assert stats.reads == stats.ops  # read_ratio=1.0
    assert stats.hit_ratio == 1.0    # single key, prefilled, never evicted


async def test_runner_is_reproducible():
    scenario = Scenario(name="det", ops=100, read_ratio=0.5, key_space=10, concurrency=4)

    async def run() -> tuple[int, int, int, int]:
        backend = MemoryBackend()
        stats = await run_scenario(backend, scenario, seed=7)
        return stats.ops, stats.reads, stats.hits, stats.errors

    a, b = await run(), await run()
    # same seed -> same workload -> identical stats (timing aside)
    assert a == b

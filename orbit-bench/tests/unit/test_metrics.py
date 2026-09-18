"""Percentile math - the numbers are the product, so they get tested hard."""

import statistics

from orbitbench.metrics import Stats, console_table, percentile


def test_percentile_known_values():
    samples = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert percentile(samples, 0.0) == 1.0
    assert percentile(samples, 1.0) == 5.0
    assert percentile(samples, 0.5) == 3.0
    assert percentile(samples, 0.95) == 4.8  # interpolated between 4 and 5
    assert percentile(samples, 0.99) == 4.96


def test_percentile_matches_stdlib_quartiles():
    samples = [float(i * i % 37) for i in range(1, 200)]
    assert abs(percentile(samples, 0.25) - statistics.quantiles(samples, n=4)[0]) < 1.0
    assert abs(percentile(samples, 0.75) - statistics.quantiles(samples, n=4)[2]) < 1.0


def test_percentile_edge_cases():
    assert percentile([], 0.5) == 0.0
    assert percentile([7.0], 0.95) == 7.0


def test_stats_derived_fields():
    stats = Stats(
        backend="memory",
        scenario="read_heavy",
        ops=100,
        errors=2,
        reads=90,
        hits=81,
        total_s=2.0,
        latencies_ms=[float(i) for i in range(1, 101)],
    )
    assert stats.mean_ms == 50.5
    assert stats.p50_ms == 50.5
    assert stats.hit_ratio == 0.9
    assert stats.ops_per_sec == 50.0
    payload = stats.as_dict()
    assert payload["p99_ms"] == 99.01  # k=98.01 interpolates between 99 and 100


def test_console_table_renders_all_rows():
    stats = Stats(backend="memory", scenario="mixed", ops=10, total_s=0.1,
                  latencies_ms=[1.0, 2.0])
    table = console_table([stats])
    assert "memory" in table and "mixed" in table and "p99" in table

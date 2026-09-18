"""The runner: prefill, distribute ops across workers, measure, summarize."""

import asyncio
import time

from orbitbench.backends.base import CacheBackend
from orbitbench.metrics import Stats
from orbitbench.workloads import OpStream, Scenario, build_value, split_ops


async def run_scenario(
    backend: CacheBackend, scenario: Scenario, seed: int = 42
) -> Stats:
    """Execute one scenario against one backend and return honest stats.

    Methodology (visible in the code, not just the docs):
    1. PREFILL the full key space (untimed) so reads measure reads.
    2. Split ops across `concurrency` workers; each worker owns
       Random(seed + worker_index) for full run reproducibility.
    3. Time every op individually; count errors and read-hits.
    """
    keys = [f"key-{i}" for i in range(scenario.key_space)]
    for i, key in enumerate(keys):  # untimed prefill
        await backend.set(key, build_value(scenario.value_bytes, seed * 1000 + i),
                          ttl_seconds=scenario.ttl_seconds)

    worker_op_counts = split_ops(scenario.ops, scenario.concurrency)
    latencies: list[float] = []
    errors = 0
    reads = 0
    hits = 0

    async def worker(worker_index: int, op_count: int) -> tuple[list[float], int, int, int]:
        stream = OpStream(seed + worker_index, scenario)
        local_latencies: list[float] = []
        local_errors = 0
        local_reads = 0
        local_hits = 0

        for _ in range(op_count):
            op, key, nonce = stream.next_op()
            started = time.perf_counter()
            try:
                if op == "get":
                    local_reads += 1
                    if await backend.get(key) is not None:
                        local_hits += 1
                else:
                    await backend.set(key, build_value(scenario.value_bytes, nonce),
                                      ttl_seconds=scenario.ttl_seconds)
            except Exception:  # noqa: BLE001 - errors are data, not crashes
                local_errors += 1
            local_latencies.append((time.perf_counter() - started) * 1000)

        return local_latencies, local_errors, local_reads, local_hits

    started = time.perf_counter()
    results = await asyncio.gather(
        *(worker(i, len(count)) for i, count in enumerate(worker_op_counts))
    )
    total_s = time.perf_counter() - started

    for lats, err, rd, hit in results:
        latencies.extend(lats)
        errors += err
        reads += rd
        hits += hit

    return Stats(
        backend=backend.name,
        scenario=scenario.name,
        ops=scenario.ops,
        errors=errors,
        reads=reads,
        hits=hits,
        total_s=total_s,
        latencies_ms=latencies,
    )


async def run_suite(
    backend: CacheBackend, scenarios: list[Scenario], seed: int = 42
) -> list[Stats]:
    return [await run_scenario(backend, scenario, seed) for scenario in scenarios]

"""Deterministic workloads: same seed -> same ops -> comparable runs.

The "honest" part lives here as much as in the runner:
- reads are only measured against a PREFILLED backend (cold misses measure
  the write path, not the read path - the two are never mixed in one number)
- every worker owns its own Random(seed + worker_index), so a run is
  byte-for-byte reproducible
"""

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class Scenario:
    name: str
    ops: int = 1000
    read_ratio: float = 0.9
    key_space: int = 500
    concurrency: int = 8
    value_bytes: int = 512
    ttl_seconds: int | None = None


SCENARIOS: dict[str, Scenario] = {
    "read_heavy": Scenario(name="read_heavy", ops=1000, read_ratio=0.9, key_space=500,
                           concurrency=8),
    "write_heavy": Scenario(name="write_heavy", ops=1000, read_ratio=0.1, key_space=500,
                            concurrency=8),
    "mixed": Scenario(name="mixed", ops=1000, read_ratio=0.5, key_space=500, concurrency=8),
    "hot_key": Scenario(name="hot_key", ops=500, read_ratio=1.0, key_space=1,
                        concurrency=16),
}


def build_value(value_bytes: int, nonce: int) -> dict:
    """Dict payload of ~value_bytes (protocol deals in dicts, not bytes)."""
    return {"nonce": nonce, "pad": "x" * max(0, value_bytes)}


class OpStream:
    """Per-worker deterministic op sequence."""

    def __init__(self, seed: int, scenario: Scenario) -> None:
        self._rng = random.Random(seed)
        self._scenario = scenario

    def next_op(self) -> tuple[str, str, int]:
        """Returns (op, key, nonce): op is 'get' or 'set'."""
        key = f"key-{self._rng.randrange(self._scenario.key_space)}"
        if self._rng.random() < self._scenario.read_ratio:
            return "get", key, 0
        return "set", key, self._rng.randrange(2**30)


def split_ops(total: int, workers: int) -> list[list[int]]:
    """Even split of op counts across workers."""
    base, remainder = divmod(total, workers)
    return [([0] * (base + (1 if w < remainder else 0))) for w in range(workers)]

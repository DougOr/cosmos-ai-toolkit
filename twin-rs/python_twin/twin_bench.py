"""CosmoTwin - the rewrite-hypothesis benchmark (Python asyncio side).

Stdlib-only twin of the Rust implementation in src/. Same scenarios, same
xorshift PRNG (identical op sequences for the same seed), same output table
and JSON keys.

Run:
    python python_twin/twin_bench.py --ops 200000 --concurrency 8 --seed 42
    python python_twin/twin_bench.py --selftest
"""

import argparse
import asyncio
import json
import math
import time

M64 = (1 << 64) - 1


# ---------------------------------------------------------------- PRNG (twin of src/rng.rs)

def splitmix64(seed: int) -> int:
    z = (seed + 0x9E3779B97F4A7C15) & M64
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & M64
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & M64
    return z ^ (z >> 31)


class Xorshift64Star:
    def __init__(self, seed: int) -> None:
        state = splitmix64(seed)
        self.state = state or 1

    def next_u64(self) -> int:
        x = self.state
        x ^= x >> 12
        x ^= (x << 25) & M64
        x ^= x >> 27
        self.state = x & M64
        return (x * 0x2545F4914F6CDD1D) & M64

    def next_f64(self) -> float:
        return (self.next_u64() >> 11) / float(1 << 53)


# ---------------------------------------------------------------- backend (twin of src/backend.rs)

class MemoryBackend:
    def __init__(self) -> None:
        self.data: dict[str, tuple[float | None, dict]] = {}
        self.locks: dict[str, asyncio.Lock] = {}
        self._registry = asyncio.Lock()

    def get(self, key: str) -> bool:
        entry = self.data.get(key)
        if entry is None:
            return False
        expires_at, _ = entry
        if expires_at is not None and time.monotonic() > expires_at:
            del self.data[key]
            return False
        return True

    def set(self, key: str, value: dict, ttl: float | None = None) -> None:
        expires_at = time.monotonic() + ttl if ttl else None
        self.data[key] = (expires_at, value)

    def lock_for(self, key: str) -> asyncio.Lock:
        # single-threaded event loop: registry access needs no outer lock
        if key not in self.locks:
            self.locks[key] = asyncio.Lock()
        return self.locks[key]


def build_value(value_bytes: int, nonce: int) -> dict:
    return {"nonce": nonce, "pad": "x" * value_bytes}


# ---------------------------------------------------------------- workload (twin of src/workload.rs)

def scenarios(ops: int, concurrency: int) -> list[dict]:
    return [
        {"name": "read_heavy", "ops": ops, "read_ratio": 0.9, "key_space": 500,
         "concurrency": concurrency, "value_bytes": 512},
        {"name": "write_heavy", "ops": ops, "read_ratio": 0.1, "key_space": 500,
         "concurrency": concurrency, "value_bytes": 512},
        {"name": "mixed", "ops": ops, "read_ratio": 0.5, "key_space": 500,
         "concurrency": concurrency, "value_bytes": 512},
        {"name": "hot_key", "ops": ops // 2, "read_ratio": 1.0, "key_space": 1,
         "concurrency": concurrency * 2, "value_bytes": 512},
    ]


class OpStream:
    """Identical op sequence to the Rust OpStream for the same seed."""

    def __init__(self, seed: int, scenario: dict) -> None:
        self.rng = Xorshift64Star(seed)
        self.read_ratio = scenario["read_ratio"]
        self.key_space = scenario["key_space"]

    def next_op(self) -> tuple[str, str, int]:
        decision = self.rng.next_f64()
        key_index = self.rng.next_u64() % self.key_space
        nonce = self.rng.next_u64()
        op = "get" if decision < self.read_ratio else "set"
        return op, f"key-{key_index}", nonce


# ---------------------------------------------------------------- metrics (twin of src/metrics.rs)

def percentile(samples: list[float], q: float) -> float:
    if not samples:
        return 0.0
    ordered = sorted(samples)
    if len(ordered) == 1:
        return ordered[0]
    k = (len(ordered) - 1) * q
    f, c = math.floor(k), math.ceil(k)
    if f == c:
        return ordered[int(k)]
    return ordered[f] + (ordered[c] - ordered[f]) * (k - f)


def summarize(backend: str, scenario: str, ops: int, reads: int, hits: int,
              total_s: float, latencies: list[float]) -> dict:
    return {
        "backend": backend,
        "scenario": scenario,
        "ops": ops,
        "errors": 0,
        "reads": reads,
        "hit_ratio": round(hits / reads, 3) if reads else 0.0,
        "total_s": round(total_s, 3),
        "ops_per_sec": round(ops / total_s, 1) if total_s > 0 else 0.0,
        "mean_ms": round(sum(latencies) / len(latencies), 4) if latencies else 0.0,
        "p50_ms": round(percentile(latencies, 0.50), 4),
        "p95_ms": round(percentile(latencies, 0.95), 4),
        "p99_ms": round(percentile(latencies, 0.99), 4),
    }


# ---------------------------------------------------------------- runner (twin of src/main.rs)

async def run_scenario(scenario: dict, cfg: argparse.Namespace) -> dict:
    backend = MemoryBackend()

    for i in range(scenario["key_space"]):  # untimed prefill
        backend.set(f"key-{i}", build_value(scenario["value_bytes"], cfg.seed * 1000 + i))

    per_worker, remainder = divmod(scenario["ops"], scenario["concurrency"])
    started = time.perf_counter()

    async def worker(w: int, count: int) -> tuple[list[float], int, int]:
        stream = OpStream(cfg.seed + w, scenario)
        latencies: list[float] = []
        reads = hits = 0
        for i in range(count):
            op, key, nonce = stream.next_op()
            t0 = time.perf_counter()
            if op == "get":
                reads += 1
                if backend.get(key):
                    hits += 1
            else:
                backend.set(key, build_value(scenario["value_bytes"], (nonce + i) & M64))
            latencies.append((time.perf_counter() - t0) * 1000.0)
        return latencies, reads, hits

    results = await asyncio.gather(
        *(worker(w, per_worker + (1 if w < remainder else 0))
          for w in range(scenario["concurrency"]))
    )
    total_s = time.perf_counter() - started

    latencies: list[float] = []
    reads = hits = 0
    for lats, r, h in results:
        latencies.extend(lats)
        reads += r
        hits += h

    return summarize("python-memory", scenario["name"], scenario["ops"],
                     reads, hits, total_s, latencies)


async def run_stampede(waiters: int, gen_cost_us: int) -> dict:
    backend = MemoryBackend()
    key = "cold-42"

    async def get_or_generate(w: int) -> int:
        async with backend.lock_for(key):
            if backend.get(key):
                return 0
            await asyncio.sleep(gen_cost_us / 1_000_000)  # the "LLM"
            backend.set(key, build_value(512, w))
            return 1

    started = time.perf_counter()
    generations = sum(await asyncio.gather(*(get_or_generate(w) for w in range(waiters))))
    return {"waiters": waiters, "generations": generations,
            "wall_ms": round((time.perf_counter() - started) * 1000, 2)}


def print_table(results: list[dict]) -> None:
    headers = ["backend", "scenario", "ops", "errors", "hit%", "ops/s",
               "mean", "p50", "p95", "p99"]
    rows = [[
        r["backend"], r["scenario"], str(r["ops"]), str(r["errors"]),
        f"{r['hit_ratio']:.0%}", f"{r['ops_per_sec']:.0f}",
        f"{r['mean_ms']:.4f}", f"{r['p50_ms']:.4f}",
        f"{r['p95_ms']:.4f}", f"{r['p99_ms']:.4f}",
    ] for r in results]
    widths = [max(len(h), *(len(row[i]) for row in rows)) for i, h in enumerate(headers)]
    print("  ".join(h.ljust(w) for h, w in zip(headers, widths)))
    print("-" * len("  ".join(h.ljust(w) for h, w in zip(headers, widths))))
    for row in rows:
        print("  ".join(c.ljust(w) for c, w in zip(row, widths)))
    print("-" * len("  ".join(h.ljust(w) for h, w in zip(headers, widths))))
    print("(latency columns in ms; this benchmark isolates in-process cache logic - no network)")


async def main() -> None:
    parser = argparse.ArgumentParser(prog="twin_bench", description="CosmoTwin (Python side)")
    parser.add_argument("mode", nargs="?", default="bench", choices=["bench", "selftest"])
    parser.add_argument("--ops", type=int, default=200_000)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--json", default=None)
    parser.add_argument("--stampede-waiters", type=int, default=10_000)
    parser.add_argument("--stampede-gen-us", type=int, default=300)
    args = parser.parse_args()

    if args.mode == "selftest":
        rng = Xorshift64Star(1)
        print("prng-vector seed=1:")
        for _ in range(3):
            print(f"  {rng.next_u64():016x}")
        return

    print(f"CosmoTwin (Python asyncio) - ops={args.ops} concurrency={args.concurrency} "
          f"seed={args.seed} value=512B")
    print()

    results = [await run_scenario(sc, args) for sc in scenarios(args.ops, args.concurrency)]
    print_table(results)

    stampede = await run_stampede(args.stampede_waiters, args.stampede_gen_us)
    print()
    print(f"stampede: {stampede['waiters']} concurrent get-or-generate on one cold key "
          f"(generation = {args.stampede_gen_us} micros simulated)")
    ok = stampede["generations"] == 1
    print(f"  wall {stampede['wall_ms']} ms | generations: {stampede['generations']} "
          f"(must be 1) | {'OK' if ok else 'FAILED'}")

    if args.json:
        payload = {"generated_by": "cosmotwin python", "results": results, "stampede": stampede}
        with open(args.json, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
        print(f"json: {args.json}")


if __name__ == "__main__":
    asyncio.run(main())

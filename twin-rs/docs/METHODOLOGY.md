# CosmoTwin Methodology

## The question

*"Would rewriting the Python cache core in Rust (or Go) make the Cosmos DB
toolkit meaningfully faster?"*

Not "is Rust faster than Python?" - that question was settled decades ago.
The question is whether **this system** would notice.

## What is measured

The in-process cache logic only: hash-map get/set, payload construction
(512-byte pad), per-key lock coordination, and the harness PRNG + scheduler
overhead that sits between ops. Two implementations of the identical
benchmark:

| | Rust side | Python side |
|---|---|---|
| Location | `src/` | `python_twin/twin_bench.py` |
| Runtime | tokio, multi-threaded | asyncio, single-threaded |
| Dependencies | tokio only | stdlib only |
| Scenarios | read_heavy 90/10, write_heavy 10/90, mixed 50/50, hot_key, stampede | identical shapes |
| Percentiles | linear interpolation, p50/p95/p99 | identical formula |

## Identical op sequences across languages

Both sides implement the same `splitmix64`-seeded `xorshift64*`. The same
seed replays the **same ops, call for call, in both languages** - verified by
the `selftest` mode printing the same hex vector:

```
4b46a55df3611b9b
d7e1f1410e763ef4
5f14ec66975f9b06
```

This removes workload composition as a confounder: differences in `ops`,
`reads`, and `hits` columns must be zero, and are.

## What is NOT measured (on purpose)

- **No network, no Cosmos DB.** The storage side is the variable being
  *compared against*, not part of the race. Cosmos-side numbers come from
  OrbitBench AI on the same machine: 73 ops/s, p50 23.6 ms (cosmos backend)
  vs 608k ops/s (memory backend).
- **No claims about idiomatic-production code.** Both sides are deliberately
  minimal twins, not tuned production systems. The comparison is of the
  *model* (compiled multi-threaded runtime vs interpreted single-threaded
  event loop), not of engineering effort.

## Declared asymmetries (documented, not hidden)

1. **Runtime model:** tokio spreads workers across cores; asyncio
   serializes on one event loop. That is not a bug - it is the real
   concurrency model each language's cache service would ship with. It
   shows up in the results as an inversion (see RESULTS.md, finding F3).
2. **PRNG cost is untimed per-op but inside wall time** - identical choice
   both sides; it penalizes Python's pure-int xorshift in throughput while
   leaving per-op latency clean. Both views are reported.
3. **Payload construction is timed** on both sides (matches OrbitBench
   methodology).

## Reproduce

```bash
# Rust side
cargo run --release -- bench --ops 200000 --concurrency 8 --seed 42 --json rust_results.json

# Python side (any Python >= 3.11, no install)
python python_twin/twin_bench.py bench --ops 200000 --concurrency 8 --seed 42 --json python_results.json

# cross-language sequence check (must print identical vectors)
cargo run --release -- selftest
python python_twin/twin_bench.py selftest
```

# OrbitBench AI Architecture

```
                 CLI (orbitbench run)         FastAPI (orbitbench serve)
                ┌──────────────────┐        ┌──────────────────────────┐
  flags ───────▶│ cli.py           │        │ api.py  /bench/run       │
                └────────┬─────────┘        │  /backends /scenarios    │
                         │                  └────────────┬─────────────┘
                         │  create_backend(name)         │
                ┌────────▼─────────────────────────────────▼─────────────┐
                │ backends/  registry → one protocol, many orbits        │
                │  ┌──────────┐  ┌────────────────┐  ┌────────────────┐  │
                │  │ memory   │  │ cosmos (aio)   │  │ redis (extra)  │  │
                │  │ control  │  │ emulator,      │  │ optional       │  │
                │  │ group    │  │ sha256 + upsert│  │ JSON values    │  │
                │  └──────────┘  └────────────────┘  └────────────────┘  │
                └────────────────────┬───────────────────────────────────┘
                                     │ get/set/delete/clear/health
                ┌────────────────────▼─────────────┐
                │ runner.py  run_scenario          │
                │  1. prefill key space (untimed)  │
                │  2. N workers × seeded OpStream  │
                │  3. per-op latency, errors counted│
                └────────────────────┬─────────────┘
                ┌────────────────────▼─────────────┐
                │ metrics.py  Stats (p50/95/99)    │──▶ report.py (MD/JSON)
                └──────────────────────────────────┘
```

## The backend protocol

```
get(key) -> dict | None      set(key, value, ttl_seconds=None)
delete(key) -> bool          clear() -> int
health() -> dict             close()
```

Seven methods, dicts in and out, async only. Every backend is *dropped in*
without touching the runner - which is precisely why cross-backend numbers
are comparable: nothing above the protocol knows which backend is running.

## Scenarios

| Scenario | read% | key space | concurrency | What it isolates |
|---|---|---|---|---|
| `read_heavy` | 90% | 500 | 8 | point-read cost against a warm store |
| `write_heavy` | 10% | 500 | 8 | ingest/upsert cost |
| `mixed` | 50% | 500 | 8 | blended traffic |
| `hot_key` | 100% | 1 | 16 | single-key read concurrency (stampede shape) |

## Methodology (the honest part, in checklist form)

- **Prefill is untimed.** Read scenarios measure reads, never cold-write
  paths sneaking into the numbers.
- **Per-worker seeded RNG.** `Random(seed + worker_index)`; the same seed
  replays the identical workload byte-for-byte (tested).
- **Errors are data.** Counted in their own column, never swallowed, never
  crashing the run.
- **Per-op latency.** p50/p95/p99 over raw samples; the mean is reported but
  is never the headline.
- **Fresh instances + purge.** Default run creates new backends and clears
  persistent ones, so yesterday's data can't flattering today's numbers.
- **The memory backend is the control group.** The gap between `memory` and
  `cosmos` in the same table is the storage cost - measured, not asserted.

## Results artifacts

- Console table (immediate)
- `RESULTS.md` (markdown, with methodology footer and provenance meta)
- `results.json` (machine-readable, for charts and regression tracking)

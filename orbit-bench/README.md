# OrbitBench AI 🛰️

**Pluggable cache backends + honest benchmarks for Azure Cosmos DB.**
Every backend in orbit around one protocol; every number on record.
100% local - runs on the Cosmos DB emulator, zero cloud.

![python](https://img.shields.io/badge/python-3.11%2B-blue)
![uv](https://img.shields.io/badge/managed%20with-uv-purple)
![scope](https://img.shields.io/badge/scope-local%20emulator%20only-green)
![methodology](https://img.shields.io/badge/percentiles-p50%20%7C%20p95%20%7C%20p99-orange)

Part of the three-piece Cosmos DB AI toolkit:

| Project | Role |
|---|---|
| [QuasarAI](../cosmos-quasar-ai) | async cache **engine** (stampede locks, parallel bulk, TTL) |
| [NebulaMind](../cosmos-nebula-mind) | **semantic LLM cache** with pluggable providers |
| **OrbitBench AI** *(this repo)* | cache **backends + honest benchmarks** - the receipts |

## Why this exists

The v1 caching harness printed "17.9x faster with cache" from a benchmark
that compared its own hard-coded sleep against a localhost read - untimed
prefill mixed into read numbers, means only, no error column, no
reproducibility. OrbitBench AI is the fix, as a tool you can point at any
cache backend:

- **One protocol, many backends** - `memory` (control group), `cosmos`
  (async SDK, emulator), `redis` (optional extra). The runner can't tell
  them apart, which is exactly why the numbers compare.
- **Deterministic workloads** - per-worker seeded RNG; same seed, same ops,
  byte-for-byte (tested).
- **Honest methodology** - prefill untimed, errors counted in their own
  column, percentiles over raw samples, purge-by-default isolation.
- **Artifacts, not screenshots** - console table + `RESULTS.md` + `results.json`
  with provenance meta.

## Quick start

Prerequisites: [uv](https://docs.astral.sh/uv/) + the
[Azure Cosmos DB Emulator](https://learn.microsoft.com/azure/cosmos-db/local-emulator)
on `https://localhost:8081` (only needed for the `cosmos` backend).

```bash
cd cosmos-orbit-bench

uv sync
uv run orbitbench check      # TLS guard + emulator + backend availability
uv run orbitbench list       # backends and scenario catalogue

# the headline run: control group vs Cosmos, same seed
uv run orbitbench run --backend memory --backend cosmos --ops 2000 --md RESULTS.md
```

```
backend  scenario     ops   errors  hit%  ops/s   mean     p50     p95      p99     
------------------------------------------------------------------------------------
memory   read_heavy   2000  0       100%  607921  0.001    0.000   0.001    0.001   
memory   write_heavy  2000  0       100%  446399  0.001    0.001   0.001    0.001   
memory   mixed        2000  0       100%  536466  0.001    0.001   0.001    0.001   
memory   hot_key      2000  0       100%  764672  0.000    0.000   0.000    0.000   
cosmos   read_heavy   2000  22      99%   73      104.311  23.626  550.365  1009.143
cosmos   write_heavy  2000  21      98%   36      211.750  72.628  899.248  1454.128
cosmos   mixed        2000  11      99%   47      156.695  42.660  676.535  1248.953
cosmos   hot_key      2000  15      99%   82      91.165   17.449  534.675  1047.441
------------------------------------------------------------------------------------
(latency columns in ms; in-memory backends legitimately show sub-ms values)
```

**Measured 2026-09-05**, Azure Cosmos DB Windows emulator, warm container
(warmup run discarded per `docs/EMULATOR.md`), seed 42, 512-byte values.
Reproduce: `uv run orbitbench run --backend memory --backend cosmos --ops 2000 --md RESULTS.md`.

What the errors column is telling you (this is the benchmark working, not
breaking): at 8-way concurrency, ~1% of Cosmos ops come back **429
TooManyRequests** - the emulator enforces its provisioned 400 RU/s. A
sequential probe (`uv run python demo/probe_errors.py`) confirms zero errors
at low pace. The throttling is *surfaced as data* instead of inflating
latency percentiles silently - precisely the failure mode this tool exists
to catch in other people's benchmarks.

Demo variant (smaller, writes artifacts):

```bash
uv run python demo/demo_orbit.py
```

HTTP API:

```bash
uv run orbitbench serve          # http://127.0.0.1:8003/docs
curl -X POST http://127.0.0.1:8003/bench/run -H "Content-Type: application/json" \
  -d '{"backends": ["memory", "cosmos"], "scenarios": ["read_heavy"], "ops": 2000}'
```

## Scenarios

| Scenario | read% | key space | concurrency | isolates |
|---|---|---|---|---|
| `read_heavy` | 90% | 500 | 8 | point-read cost on a warm store |
| `write_heavy` | 10% | 500 | 8 | ingest/upsert cost |
| `mixed` | 50% | 500 | 8 | blended traffic |
| `hot_key` | 100% | 1 | 16 | single-key read concurrency (stampede shape) |

## Using it as a tool

The backend protocol is seven async methods (`get/set/delete/clear/health/close`,
dicts in/out). Subclass `CacheBackend`, register it in the factory, and your
storage joins the same benchmark table as Cosmos DB - that's the intended
reuse: point it at your real cache layer and get receipts.

## Tests

```bash
uv run pytest              # unit suite - no emulator needed
uv run pytest -m emulator  # Cosmos backend CRUD + small scenario (skips if emulator down)
```

`test_runner_is_reproducible` is the thesis in test form: same seed →
identical ops, reads, hits, and errors.

## Documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - protocol, scenarios, methodology checklist
- [docs/EMULATOR.md](docs/EMULATOR.md) - setup + first run + troubleshooting
- [docs/CLOUD_DELTAS.md](docs/CLOUD_DELTAS.md) - RU accounting, integrated cache, multi-region
- [docs/DECISIONS.md](docs/DECISIONS.md) - eight ADRs (control-group backend, untimed prefill, seeded workloads, percentiles over means, ...)

## License

Portfolio demonstration project. Emulator key = well-known public dev key.

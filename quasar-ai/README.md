# QuasarAI ⚡

**Async-first Azure Cosmos DB caching engine for LLM workloads.**
100% local - runs on the Cosmos DB emulator, zero cloud, zero cost.

![python](https://img.shields.io/badge/python-3.11%2B-blue)
![uv](https://img.shields.io/badge/managed%20with-uv-purple)
![scope](https://img.shields.io/badge/scope-local%20emulator%20only-green)
![sync](https://img.shields.io/badge/Cosmos%20SDK-async%20only-orange)

> **The fastest cache engine in the universe** - and the honest v2 of the v1
> caching harness that froze its lessons into this repo's design.

QuasarAI is the **async core** of a three-piece Cosmos DB AI toolkit:

| Project | Role |
|---|---|
| **QuasarAI** *(this repo)* | async get-or-generate cache engine: stampede locks, parallel bulk, TTL presets, parameterized invalidation |
| [NebulaMind](../cosmos-nebula-mind) | real-LLM **semantic** cache: exact + similarity hits, pluggable providers |
| [OrbitBench AI](../cosmos-orbit-bench) | pluggable cache **backends + honest benchmarks** with p50/p95/p99 receipts |
| *v1 reference:* [`v1-harness/`](../v1-harness/) | frozen "before" - every v1 flaw is an ADR here ([docs/DECISIONS.md](docs/DECISIONS.md)) |

## Why QuasarAI exists

The v1 harness worked, and did everything wrong that a portfolio project can
get away with: sync SDK inside async handlers (blocking the event loop),
no stampede protection (concurrent misses generated N times and 409-crashed),
md5 ids, naive datetimes mixed with aware ones, SQL built by string
interpolation, and `indefinite` TTLs that expired anyway. QuasarAI fixes all
of it and documents each fix as an ADR - because "what I got wrong" is the
strongest content a portfolio can ship.

## Features

- ⚡ **Async only** - `azure.cosmos.aio`; the sync SDK is never imported, so nothing blocks the event loop
- 🔒 **Stampede protection** - per-key `asyncio.Lock`: 1,000 concurrent misses, exactly 1 generation
- 🛡️ **Race-safe writes** - upsert semantics; concurrent writers converge, never 409
- ⏱️ **TTL presets** - the same 9 presets as v1 (`indefinite` now actually means never)
- 🚀 **Genuinely parallel bulk** - `asyncio.gather`, not a for-loop
- 🎯 **Parameterized invalidation** - `CONTAINS` with query params, no string interpolation
- 🧪 **Tested** - unit suite runs anywhere; emulator integration tests self-skip when it's down
- 🔐 **TLS guard** - skipped cert verification is impossible off localhost, by construction
- 📖 **Swagger UI** at `/docs`

## Quick start

Prerequisites: [uv](https://docs.astral.sh/uv/) + the
[Azure Cosmos DB Emulator](https://learn.microsoft.com/azure/cosmos-db/local-emulator)
(Windows MSI) running on `https://localhost:8081`.

```bash
cd cosmos-quasar-ai

uv sync                  # creates .venv from uv.lock, resolves everything
uv run quasar-ai check   # preflight: TLS guard + emulator reachability
uv run quasar-ai serve   # FastAPI on http://127.0.0.1:8001  (Swagger: /docs)
```

Try it:

```bash
# miss (generates + caches), then hit
curl http://127.0.0.1:8001/cache/demo:quantum
curl http://127.0.0.1:8001/cache/demo:quantum

# benchmark: p50/p95 for misses vs hits + speedup
curl http://127.0.0.1:8001/benchmark
```

End-to-end demo without HTTP:

```bash
uv run python demo/demo_quasar.py
```

## API

| Method | Path | What it does |
|---|---|---|
| `POST` | `/cache` | generate (mock LLM) + cache under `cache_key` |
| `GET` | `/cache/{cache_key}` | get-or-generate with stampede protection |
| `DELETE` | `/cache/{cache_key}` | delete one entry |
| `POST` | `/cache/bulk` | concurrent get-or-generate (up to 100) |
| `POST` | `/cache/warm` | pre-generate common keys |
| `DELETE` | `/cache/invalidate?pattern=` | parameterized `CONTAINS` invalidation |
| `POST/GET/DELETE` | `/generic[/{key}]` | arbitrary JSON + TTL on a second container |
| `GET` | `/benchmark` | miss-vs-hit race, p50/p95 + speedup |
| `GET` | `/health` | liveness + entry count + TTL presets |

## Configuration (`.env`)

| Variable | Default | Notes |
|---|---|---|
| `COSMOS_ENDPOINT` | `https://localhost:8081/` | local emulator |
| `COSMOS_KEY` | well-known emulator key | public by design - see docs |
| `DATABASE_NAME` | `QuasarDB` | |
| `INTELLIGENT_CONTAINER` | `quasar-intelligent` | LLM-payload cache |
| `GENERIC_CONTAINER` | `quasar-generic` | arbitrary JSON |
| `DEFAULT_TTL` | `120` | seconds |
| `SIMULATED_LATENCY_SECONDS` | `0.3` | mock LLM latency |
| `VERIFY_EMULATOR_TLS` | `false` | guard refuses non-localhost when false |

## Tests

```bash
uv run pytest              # unit suite (no emulator needed)
uv run pytest -m emulator  # integration vs the real emulator (skips if it's down)
```

The stampede test is the portfolio headline: 10 concurrent misses on a cold
key produce exactly **one** generation and nine hits.

## Benchmark

```bash
uv run python demo/demo_quasar.py    # narrative demo
curl http://127.0.0.1:8001/benchmark # structured numbers
```

**Measured on this machine** (2026-09-05, Azure Cosmos DB Windows emulator,
deterministic mock LLM at 300 ms simulated latency):

| Probe | Result |
|---|---|
| Cache miss (generate + store) | 349.5 ms |
| Cache hit (point read) | 6.3 ms |
| **Speedup** | **55x** |
| Stampede: 20 concurrent cold-key requests | **exactly 1 generation**, 19 hits |
| Parallel bulk: 12 distinct misses | 610 ms total (concurrent, not serial) |

Reproducibility over screenshots: the mock LLM is deterministic (ADR-010), so
your numbers will match mine modulo disk. For cross-backend bake-offs, use
[OrbitBench AI](../cosmos-orbit-bench).

## Documentation

- [docs/EMULATOR.md](docs/EMULATOR.md) - install, preflight, troubleshooting
- [docs/CLOUD_DELTAS.md](docs/CLOUD_DELTAS.md) - what the emulator can't show and what cloud migration would change
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - component map, request flow, data model
- [docs/DECISIONS.md](docs/DECISIONS.md) - ten ADRs, each mapped to a v1 flaw

## License

Portfolio demonstration project. The emulator key in `.env.example` is the
well-known public dev key - it opens your local emulator and nothing else.

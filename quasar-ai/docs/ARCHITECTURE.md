# QuasarAI Architecture

## Component map

```
                FastAPI (lifespan)                     CLI
               ┌───────────────────┐          ┌──────────────────┐
 HTTP  ───────▶│ api.py            │◀─────────│ cli.py serve     │
               │  /cache  /generic │          │ cli.py check     │
               │  /bulk   /warm    │          └──────────────────┘
               │  /benchmark /health│
               └────────┬──────────┘
                        │ app.state.engine / .generic / .mock
               ┌────────▼──────────┐
               │ engine.py         │  AsyncCacheEngine          GenericStore
               │  get_or_generate  │  per-key asyncio.Lock      upsert JSON + TTL
               │  bulk (gather)    │  upsert on miss            read/delete
               │  invalidate       │  parameterized CONTAINS
               └────────┬──────────┘
               ┌────────▼──────────┐      ┌───────────────────────┐
               │ cosmos.py         │      │ generators.py         │
               │ CosmosResources   │      │ MockLLM (deterministic)│
               │ aio client + DB   │      └───────────────────────┘
               │ + containers      │
               └────────┬──────────┘
                        │ azure.cosmos.aio  (async SDK, sync SDK never imported)
               ┌────────▼──────────┐
               │ Cosmos DB emulator│  https://localhost:8081 (Windows, local only)
               └───────────────────┘
```

## Request flow: get-or-generate

1. `key → sha256 → doc id`
2. Acquire the **per-key `asyncio.Lock`** (stampede gate).
3. Point-read the document. Hit → compute `ttl_remaining`, return.
4. Miss → call the generator hook (mock LLM, ~300 ms simulated).
5. `upsert_item` the payload with `ttl` (never 409s; last writer converges).
6. Return `status="miss"`. Concurrent waiters re-read → `status="hit"`.

## Modules

| Module | Responsibility | v1 counterpart (what changed) |
|---|---|---|
| `config.py` | typed settings + TLS guard | raw `os.getenv` + hardcoded fallbacks |
| `ttl.py` | preset table (v1-compatible) | inline dict |
| `keys.py` | sha256 doc ids | md5 |
| `cosmos.py` | async bootstrap, one place for auth | startup event globals |
| `engine.py` | cache logic, stampede locks | endpoint functions, no locks |
| `generators.py` | pluggable mock LLM | inline simulate function |
| `models.py` | pydantic v2 schemas | pydantic v1-style models |
| `api.py` | lifespan-based FastAPI | deprecated `on_event` |

## Data model (intelligent container)

```json
{
  "id":       "<sha256(cache_key)>",
  "pk":       "primary",
  "cache_key": "demo:quantum",
  "payload":  { "...": "generator output" },
  "created_at": "2026-09-05T12:00:00.000000+00:00",
  "ttl_value": 300,
  "ttl":      300
}
```

`ttl` is the Cosmos DB native field: positive = seconds to live, `-1` = never
expires. `ttl_value` mirrors it for application-side `ttl_remaining`
math (the emulator enforces native TTL lazily, so the API surface reports
remaining time deterministically).

## Concurrency model

- One event loop, one process. `asyncio.gather` drives bulk/warm/benchmark.
- Per-key locks guarantee single generation under concurrency.
- The sync `azure.cosmos` SDK is never imported; nothing blocks the loop.
- Multi-process deployments: safe-by-upsert (duplicate generation allowed),
  or add a distributed lock - see `DECISIONS.md` ADR-003.

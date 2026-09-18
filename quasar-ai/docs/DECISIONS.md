# QuasarAI Decision Record

Each decision below exists because the v1 harness
([`v1-harness/`](../v1-harness/), kept frozen as the reference line) did
the opposite, and the consequences were observable. This is the
"what I got wrong" ledger, kept next to the code.

## ADR-001: Async SDK only, lifespan startup

**Decision:** `azure.cosmos.aio` everywhere; FastAPI `lifespan` context
manager; no `@app.on_event`.

**Why:** v1 called the *synchronous* SDK inside `async def` endpoints - every
Cosmos call blocked the event loop, so "parallel" bulk ops were neither.
`on_event` is deprecated upstream.

## ADR-002: Per-key stampede locks

**Decision:** `asyncio.Lock` per cache key around get-or-generate.

**Why:** v1 let N concurrent misses fire N generations for the same key
(thundering herd) and then crash N-1 times on `create_item` 409s.
In-process scope is deliberate; ADR-003 covers the multi-instance story.

## ADR-003: Upsert instead of create

**Decision:** `upsert_item` on cache fill.

**Why:** makes ADR-002's residue benign: even without a lock, racing writers
converge instead of raising. Correctness layering: lock avoids work;
upsert avoids errors.

## ADR-004: Static partition key kept (for now)

**Decision:** single partition `/pk = "primary"`, like v1.

**Why:** keeps v1-vs-QuasarAI benchmarks comparable (same data distribution)
and matches the emulator demo scale. In the cloud this becomes a real
decision (tenant or hash-prefix partitioning). Recorded as debt, not
hidden.

## ADR-005: sha256 document ids

**Decision:** `doc_id = sha256(cache_key)`.

**Why:** v1 used md5. No security exposure in v1's use, but sha256 costs
nothing and stops the code review conversation at "why md5?".

## ADR-006: Timezone-aware timestamps

**Decision:** `datetime.now(timezone.utc)` stored as ISO-8601 with offset;
`ttl_remaining` computes aware-vs-aware.

**Why:** v1 mixed naive `utcnow()` with `fromisoformat()` of offset strings
and swallowed the resulting TypeError with a broad `except` (plus a dead
duplicated `return None` at the end of the function). The bug class
disappears instead of being caught.

## ADR-007: Parameterized invalidation queries

**Decision:** `CONTAINS(c.cache_key, @pat, true)` with query parameters.

**Why:** v1 f-string-interpolated the user-supplied pattern into the SQL
text - functionally injection-shaped, even inside a demo.

## ADR-008: TLS guard on the emulator shortcut

**Decision:** `connection_verify` may only be `False` for localhost
endpoints; `Settings.tls_guard()` fails fast otherwise.

**Why:** the emulator's self-signed cert forces skipped verification; v1
hardcoded `connection_verify=False` unconditionally. The guard keeps the
shortcut local-only by construction.

## ADR-009: `ttl = -1` for indefinite entries

**Decision:** indefinite TTL writes the native Cosmos `-1` (never expire).

**Why:** v1 wrote the *default* TTL for indefinite requests - the item
expired anyway. Presets now have exactly the meaning they advertise.

## ADR-010: Mock LLM is deterministic

**Decision:** the mock generator hashes (system, prompt) into its output.

**Why:** benchmarks must be reproducible and cache-hit demos must show
byte-identical payloads. Real LLM generation lives in the sibling project
NebulaMind, which is the point of that repo.

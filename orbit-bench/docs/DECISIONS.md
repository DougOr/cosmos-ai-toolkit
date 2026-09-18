# OrbitBench AI Decision Record

## ADR-001: Protocol-first backends

**Decision:** one abstract `CacheBackend` (get/set/delete/clear/health/close,
async, dicts in/out); backends register through a single factory.

**Why:** comparability is the product. If the runner knows nothing about the
backend, cross-backend tables measure the backend and nothing else. v1's
benchmark was welded to its own endpoints and could only ever measure itself.

## ADR-002: The memory backend is mandatory, not a stub

**Decision:** every run can include the in-process `memory` backend.

**Why:** it is the control group. The `memory` vs `cosmos` delta in one table
is the measured cost of storage - a claim you can defend, versus a latency
number floating in space.

## ADR-003: Prefill excluded from timing

**Decision:** the key space is fully written before measurement starts.

**Why:** v1's "cache miss" numbers were dominated by a hard-coded
`asyncio.sleep(0.3)` simulating an LLM - the benchmark measured its own
theatre. In OrbitBench, read scenarios measure read paths; if you want
generation cost in the picture, that is NebulaMind's benchmark with real
providers.

## ADR-004: Deterministic seeded workloads

**Decision:** per-worker `Random(seed + worker_index)`; scenarios are frozen
dataclasses; ops split evenly across workers.

**Why:** reproducibility is what turns a demo number into a claim. Same seed
= same op sequence = comparable runs across machines and days (tested).

## ADR-005: Percentiles over means

**Decision:** p50/p95/p99 over raw per-op samples; mean reported for context.

**Why:** latency distributions are long-tailed; a mean lets a fast 90% hide
a miserable 10%. v1 reported only means.

## ADR-006: Errors are a column, not an exception

**Decision:** worker catches per-op failures, increments `errors`, keeps
going; the table shows the count.

**Why:** a benchmark that dies on its first backend hiccup measures
fragility, not performance; one that hides errors lies. Counted-and-visible
preserves both the run and the honesty.

## ADR-007: Purge by default, `--no-purge` documented as load-dependent

**Decision:** persistent backends are cleared before each run unless the
flag says otherwise.

**Why:** leftover entries change hit ratios and RU costs silently. Default
to isolation; make deviation explicit.

## ADR-008: Redis is an optional extra with an honest error

**Decision:** `orbitbench[redis]` extra; the registry raises a message that
names the fix (`uv sync --extra redis`) when selected without it.

**Why:** the default install must stay hermetic (emulator + stdlib), and a
missing-dependency error should never make you read source code.

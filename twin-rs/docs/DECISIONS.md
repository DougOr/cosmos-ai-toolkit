# CosmoTwin Decision Record

## ADR-001: Duplicate the harness in two languages instead of sharing code

**Decision:** `src/` (Rust) and `python_twin/` (Python) are deliberately
separate implementations of the same benchmark, not one codebase with
bindings.

**Why:** sharing code via FFI/pyo3 would measure the bridge, not the
languages. The duplication *is* the experiment, and it is small enough
(~400 lines each side) that drift is reviewable by eye.

## ADR-002: xorshift64* + splitmix seeding, implemented identically in both

**Decision:** no `rand` crate, no `random` module - a ~15-line PRNG with a
pinned self-test vector, byte-identical in both languages.

**Why:** same seed → same op sequence → the `ops/reads/hits` columns must
match across languages, which turns workload composition from a confounder
into a verified invariant. (Mersenne Twister parity was rejected:
replicating CPython's stdlib generator in Rust is possible but needless.)

## ADR-003: tokio is the only dependency

**Decision:** Rust side = std + tokio; Python side = stdlib only.

**Why:** async concurrency is the thing being compared, so the async runtime
is in scope; everything else (CLI parsing, JSON, table formatting, hashing)
is deliberately hand-rolled to keep the surface reviewable and the
comparison honest.

## ADR-004: The runtime-model asymmetry is kept, not equalized

**Decision:** Rust runs workers on the multi-threaded tokio runtime; Python
keeps asyncio's single-threaded event loop. No attempts to force parity.

**Why:** those are the concurrency models production services would actually
ship. Equalizing them (single-threaded tokio) would answer a question nobody
is deploying. The asymmetry produced the most interesting finding (RESULTS.md
F3) - which is what honest measurement is for.

## ADR-005: No network in scope

**Decision:** the twins benchmark in-process cache logic only; Cosmos-side
numbers are cited from OrbitBench AI run on the same machine.

**Why:** the question is "how much of the system would a rewrite speed up?"
Answering it requires isolating the component, then dividing by the system.
Mixing network I/O into both twins would bury the answer under the emulator's
retry policy.

## ADR-006: Payload construction is inside the timed region

**Decision:** the 512-byte pad allocation happens between the latency
timestamps on both sides.

**Why:** cache logic that hands out values includes building the values;
excluding it would flatter both languages and break comparability with
OrbitBench's memory backend.

## ADR-007: The stampede scenario is part of the twin

**Decision:** 10,000 concurrent get-or-generate on one cold key, simulated
300-microsecond generation, generations == 1 as a hard gate.

**Why:** lock coordination under contention is where "rewrite it in Rust"
arguments usually hide, so it must be measured - and the correctness gate
proves the Python design's guarantee survives transplantation unchanged.

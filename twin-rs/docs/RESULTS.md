# CosmoTwin Results

**Machine:** Windows 11, rustc 1.98.0 (release, LTO), CPython via
`python_twin/` (stdlib asyncio). **Workload:** 200k ops per scenario,
concurrency 8, seed 42, 512-byte values. **Date:** 2026-09-05.

## Rust side (src/)

```
backend      scenario     ops     errors  hit%  ops/s    mean    p50     p95     p99
---------------------------------------------------------------------------------------
rust-memory  read_heavy   200000  0       100%  3298420  0.0021  0.0004  0.0071  0.0177
rust-memory  write_heavy  200000  0       100%  1020400  0.0074  0.0014  0.0331  0.1037
rust-memory  mixed        200000  0       100%  1230292  0.0062  0.0015  0.0258  0.0586
rust-memory  hot_key      100000  0       100%  2297815  0.0063  0.0005  0.0335  0.0797
---------------------------------------------------------------------------------------

stampede: 10000 concurrent get-or-generate, generation = 300 micros
  wall 14.36 ms | generations: 1 (must be 1) | OK
```

## Python side (python_twin/)

```
backend        scenario     ops     errors  hit%  ops/s   mean    p50     p95     p99
--------------------------------------------------------------------------------------
python-memory  read_heavy   200000  0       100%  333848  0.0005  0.0004  0.0012  0.0019
python-memory  write_heavy  200000  0       100%  433392  0.0006  0.0005  0.0009  0.0012
python-memory  mixed        200000  0       100%  498947  0.0004  0.0004  0.0007  0.0010
python-memory  hot_key      100000  0       100%  604444  0.0002  0.0002  0.0003  0.0004
--------------------------------------------------------------------------------------

stampede: 10000 concurrent get-or-generate, generation = 300 micros
  wall 105.91 ms | generations: 1 (must be 1) | OK
```

## The reference point (OrbitBench AI, same machine, same day)

```
cosmos (emulator)  read_heavy  2000 ops  73 ops/s  p50 23.626 ms  p95 550 ms
memory (Python)    read_heavy  2000 ops  607921 ops/s  p50 0.000 ms
```

## Findings

**F1 - The compiled advantage is real: ~10x raw throughput.**
read_heavy: 3.30M ops/s (Rust) vs 334k ops/s (Python). At pure in-process
cache throughput, Rust wins by an order of magnitude, as advertised.

**F2 - And it moves the system by approximately nothing.**
Per-op cache logic costs 0.4-2 microseconds in *both* languages. The Cosmos
backend costs 23,600 microseconds per op at the median. The storage is
~10,000x slower than either language's cache path. Replacing a 1.5-microsecond
component inside a 23,600-microsecond pipeline changes total latency by
~0.006%. The rewrite hypothesis is **refuted for this system** - the
bottleneck was never the language.

**F3 - The honest inversion.**
Python's *timed per-op* latency is as low or lower than Rust's (p50 0.0004 ms
both; mean lower), while Rust's *throughput* is 10x higher. Why: the twins
deliberately ship their native runtime models - tokio spreads 8 workers
across cores and pays `Mutex` contention plus cross-core cache traffic on
every access; asyncio's single event loop has zero contention. And the PRNG
+ scheduling overhead sits in wall time (untimed per-op), where Python's
pure-int xorshift is genuinely expensive - which is where most of the 10x
lives. Both effects are documented in METHODOLOGY.md, not hidden.

**F4 - Stampede correctness is language-independent.**
10,000 concurrent get-or-generate calls: exactly **1 generation** in both
languages. Rust finishes the storm in 14.4 ms vs Python's 105.9 ms (7.4x) -
the compiled advantage again - but the *guarantee* came from the design
(per-key locks + upsert), which both twins inherit unchanged.

## Verdict

The hypothesis "this toolkit would be faster in Rust" is **measured and
refuted**: 10x raw throughput improvement on a component that contributes
~0.006% of system latency. The correct conclusion is not "Rust is slow" nor
"Python is fast" - it is that **language choice was never the constraint;
the store is**. If this system ever needs >300k cache ops/s in-process, the
measurement now exists to justify revisiting - that is what a benchmark is
for.

# DEMO - CosmoTwin in 5 minutes

**Audience:** engineers arguing about rewrites (so: every team, eventually).
**One-line takeaway:** *"Rust was 10x faster at the cache logic - and the
benchmark proved it would make the actual system 0.006% faster. Measure the
rewrite before writing it."*

No emulator needed. No installs beyond cargo (which you have) and Python.

---

## Before the audience arrives (~2 minutes)

```powershell
cd twin-rs
cargo build --release        # warm the compiler cache so the live build is instant
```

Have open: `docs/RESULTS.md` and `docs/DECISIONS.md` in the browser; the
OrbitBench cosmos numbers (`..\cosmos-orbit-bench\RESULTS.md`) for the kill
shot in Act 3.

---

## Act 1 - Two twins, one workload (90 seconds)

```powershell
cargo run --release -- selftest
python python_twin/twin_bench.py selftest
```

Both print:

```
4b46a55df3611b9b
d7e1f1410e763ef4
5f14ec66975f9b06
```

> **Say:** "Same 15-line PRNG, hand-implemented in both languages. Same
> seed means both sides replay the *identical* op sequence - so when the
> numbers differ, it's the language, never the workload."

## Act 2 - The race (2 minutes)

```powershell
cargo run --release -- bench --ops 200000 --seed 42
python python_twin/twin_bench.py bench --ops 200000 --seed 42
```

Point at the two tables:

> **Say:** "Rust: 3.3 million ops per second. Python: 334 thousand. Ten-x -
> the compiled-language crowd is right, and I'm not going to pretend
> otherwise. Also look at the stampede line at the bottom: ten thousand
> concurrent requests, exactly one generation, in both languages. The
> *guarantee* is design, not language."

Then the inversion (preempt the sharp question):

> **Say:** "And the trap for the careless: look at per-op latency - Python's
> median equals Rust's. The 10x lives in the harness and scheduling, and
> Rust pays mutex contention across 8 threads that Python's single event
> loop never sees. Both asymmetries are declared in the methodology, not
> discovered by a commenter."

## Act 3 - The kill shot (60 seconds)

Open `..\cosmos-orbit-bench\RESULTS.md` next to this repo's `docs/RESULTS.md`:

> **Say:** "Here is the number that ends the rewrite argument. The Cosmos
> backend costs 23.6 *milliseconds* per op at the median. The cache logic
> costs 0.4 *microseconds* - in either language. The store is ten thousand
> times slower than the code we'd rewrite. A 10x improvement on 0.006% of
> the pipeline is a rounding error with a build system. The hypothesis was
> 'this would be faster in Rust'. Measured answer: the component, yes; the
> system, no. That's what benchmarks are for."

## Act 4 - The receipts (30 seconds)

Open `docs/DECISIONS.md`.

> **Say:** "Seven ADRs - including the asymmetries I *chose* to keep
> (multi-threaded tokio vs single-threaded asyncio, because those are what
> production would ship) and the one thing I refuse to claim (no network in
> scope). If my benchmark has a hidden assumption, I want it in writing."

---

## Contingency plans

| Problem | Fallback |
|---|---|
| `cargo` not installed on the demo machine | Present `docs/RESULTS.md` (measured tables) and run only the Python side live |
| Rust numbers differ run-to-run | Expected - throughput varies with machine load; the `ops/reads/hits` invariants and the magnitude of the gap do not |
| Audience asks "why not Go?" | Same answer structure: the store dominates; Go's SDK is GA (azcosmos) and Go would show the same null result on system latency |

## Reset between runs

Nothing to reset - no network, no database, no state outside the process.

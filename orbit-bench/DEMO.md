# DEMO - OrbitBench AI in 7 minutes

**Audience:** engineers who have ever quoted a benchmark number (so: everyone).
**One-line takeaway:** *"Every cache backend in orbit around one protocol,
every number on record - including the errors column that most benchmarks
delete."*

Runs 100% local; the cosmos backend needs the emulator, the memory backend
needs nothing.

---

## Before the audience arrives (~5 minutes)

1. Start the **Azure Cosmos DB Emulator**, wait ~20 s.
2. Terminal:

   ```powershell
   cd orbit-bench
   uv sync
   uv run orbitbench check       # emulator REACHABLE, backends listed
   uv run orbitbench run --backend cosmos --ops 100   # WARM-UP - discard output;
                                                      # absorbs container creation + JIT
   ```

3. Have `docs/DECISIONS.md` open in the browser for Act 5.

---

## Act 1 - The table (2 min)

```powershell
uv run orbitbench run --backend memory --backend cosmos --ops 2000 --seed 42 --md RESULTS.md
```

Walk the printed table (numbers ± machine noise, format identical):

```
backend  scenario     ops   errors  hit%  ops/s   mean     p50     p95      p99
--------------------------------------------------------------------------------
memory   read_heavy   2000  0       100%  607921  0.001    0.000   0.001    0.001
cosmos   read_heavy   2000  22      99%   73      104.311  23.626  550.365  1009.143
...
```

> **Say:** "Memory: 600 thousand ops per second, sub-microsecond. Cosmos:
> 73 ops per second, 24 milliseconds at the median. That gap is not Python
> being slow - it is the measured price of durability, network, and
> consistency. The memory row is the *control group*: same protocol, same
> workload, zero I/O. The delta is the storage cost, measured instead of
> guessed."

Point at `RESULTS.md` (just written): same table plus provenance meta.

## Act 2 - The errors column is the product (2 min)

> **Say:** "Now the interesting column. Twenty-two errors out of two
> thousand. Most benchmark tools would hide that. Let's find out what they
> are."

```powershell
uv run python demo/probe_errors.py
```

First run (sequential, 300 reads): `(no errors)`. Under the concurrent
benchmark load the same probe reports `429 (TooManyRequests)` - the emulator
enforcing its provisioned 400 RU/s.

> **Say:** "Sequential: zero errors. Concurrent: ~1% throttled with HTTP
> 429. The errors column *surfaces* throttling instead of silently smearing
> it into the latency percentiles. A benchmark that hides throttling doesn't
> just miss data - it lies: your p95 gets blamed on latency when it's really
> retry policy. This is the exact failure mode the v1 of this project
> benchmarked its way into."

## Act 3 - Reproducibility (60 seconds)

Run Act 1's command again, same seed. The `ops`, `errors`, `hit%` columns
come back **identical** (per-worker seeded RNG).

> **Say:** "Same seed, same workload, byte for byte. These are claims you
> can re-verify, not anecdotes. There's a unit test that asserts it."

## Act 4 - Seven methods to join the table (60 seconds)

Open `src/orbitbench/backends/base.py`: `get`, `set`, `delete`, `clear`,
`health`, `close`.

> **Say:** "This is the entire contract. Implement these seven methods and
> your storage - Redis, Postgres, whatever your team runs - appears in this
> same benchmark table next to Cosmos DB. The runner physically cannot tell
> backends apart, which is exactly why the numbers compare."

## Act 5 - Why this tool exists (60 seconds)

Open `docs/DECISIONS.md`.

> **Say:** "The v1 caching harness claimed '17.9x faster with cache' - from
> a benchmark that measured its own hard-coded sleep against a localhost
> read. Untimed prefill mixed into read numbers, means only, no error
> column, no reproducibility. Every rule in this repo - prefilled key spaces
> excluded from timing, percentiles over raw samples, errors counted in the
> open - exists because a benchmark we trusted was quietly fictional. If you
> remember one slide: *the errors column is the product*."

---

## Contingency plans

| Problem | Fallback |
|---|---|
| Emulator down | The whole demo works memory-only: `uv run orbitbench run --backend memory --ops 5000`; tell the 429 story from RESULTS.md |
| First cosmos scenario is slow | That's the warm-up you skipped - run it again and use the second table (docs/EMULATOR.md says so) |
| Audience asks "why is p95 >> p50?" | Emulator is single-node with a retry policy; bursts + 429 retries land in the tail - which is exactly why means lie |

## Reset between runs

Nothing required - persistent backends are purged at the start of each run
by default (`--no-purge` to opt out, and say why that flag exists).

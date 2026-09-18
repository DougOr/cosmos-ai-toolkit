# Cosmos AI Toolkit

Measured, reproducible caching-layer components for LLM workloads on Azure Cosmos DB - plus the frozen v1 that shows why the measurements matter.

Rule zero of this toolkit: never publish a number that is not recorded in a README, DEMO, or RESULTS file. Every figure below is measured, seeded, and reproducible from a clean clone on the free local Cosmos DB emulator.

## Modules

| Module | What it proves | Headline receipts |
|---|---|---|
| [`quasar-ai`](quasar-ai/) - **QuasarAI** | Exact-hit LLM cache done correctly | Miss 349.5 ms -> hit **6.3 ms (55x)**; 20 concurrent cold-key requests -> **exactly 1 generation** |
| [`twin-rs`](twin-rs/) - **CosmoTwin** | Rust-vs-Python rewrite hypothesis, benchmarked before rewriting | Rust **3.3M ops/s** vs Python **334k ops/s** (9.9x); identical op sequences from one shared seed; system impact of the 10x: **~0.006%** |
| [`orbit-bench`](orbit-bench/) - **OrbitBench AI** | An honest benchmark whose errors column is the best data | Memory backend **608k ops/s** vs Cosmos **73 ops/s**; **~1% HTTP 429s** surfaced in the errors column; same seed = identical runs |
| [`nebula-mind`](nebula-mind/) - **NebulaMind** | Semantic cache that refuses to lie about itself | Generated 239 ms -> exact hit **12 ms (20x)**; rephrased question scores **0.727** and says so; honesty flags stored in the data |
| [`v1-harness`](v1-harness/) - **frozen v1** | The cautionary tale: a "17.9x faster" claim built on its own simulated sleep | Kept public on purpose. Read it before trusting any benchmark, including ours |

## The three narratives

1. **Receipts over vibes** - benchmarks that surface throttling, percentiles, and reproducibility (OrbitBench, CosmoTwin).
2. **Pay once, answer fast, never lie** - LLM caching done correctly (QuasarAI, NebulaMind).
3. **Show your wrongs** - v1 -> v2 decision-record culture as a seniority signal (v1-harness vs everything above).

## Running it

Each module is self-contained: its folder carries a README and a DEMO that run from a clean clone against the free Cosmos DB emulator. No cloud account, no keys, no cost.

## Why the v1 sits next to the rest

Because the corrected numbers are only credible next to the wrong ones. The v1 harness claimed 17.9x by comparing its own hard-coded sleep to a localhost read. It stayed in the repo as a receipt.

---

Doug Ortiz - [LinkedIn](https://www.linkedin.com/in/doug-ortiz-architect/) - [Blog](https://dougortiz.blogspot.com) - [TechBits on Substack](https://techbitsdo.substack.com)

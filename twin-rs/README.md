# CosmoTwin 👥

**The rewrite-hypothesis benchmark.** The same in-memory cache core,
implemented twice - Rust (std + tokio) and Python (stdlib asyncio) - with
identical op sequences, run on the same machine, judged against the real
Cosmos DB numbers.

![rust](https://img.shields.io/badge/rust-1.98-orange)
![python](https://img.shields.io/badge/python-3.11%2B-blue)
![deps](https://img.shields.io/badge/deps-tokio%20%7C%20stdlib%20only-success)
![methodology](https://img.shields.io/badge/sequences-identical%20across%20languages-8A2BE2)

> *"I almost rewrote my cache in Rust. I benchmarked the hypothesis
> instead. Rust won by 10x - and it changed the system by 0.006%."*

The fourth piece of the Cosmos DB AI toolkit - and the one that keeps the
other three honest about language choice:

| Project | Role |
|---|---|
| [QuasarAI](../cosmos-quasar-ai) | async cache **engine** (Python) |
| [NebulaMind](../cosmos-nebula-mind) | **semantic LLM cache** (Python) |
| [OrbitBench AI](../cosmos-orbit-bench) | cache **backends + honest benchmarks** (Python) |
| **CosmoTwin** *(this repo)* | the **rewrite-hypothesis experiment**: is the Python worth replacing? |

## The result (2026-09-05, full tables in [docs/RESULTS.md](docs/RESULTS.md))

| | Rust (tokio) | Python (asyncio) | Delta |
|---|---|---|---|
| read_heavy throughput | **3,298,420 ops/s** | 333,848 ops/s | **Rust 9.9x** |
| read_heavy p50 | 0.4 µs | 0.4 µs | tie |
| stampede: 10k concurrent, generations | **1** (14.4 ms) | **1** (105.9 ms) | correctness: tie |
| **Cosmos backend (reference)** | - | **73 ops/s, p50 23.6 ms** | **the actual system** |

**Verdict:** Rust's 10x is real. The system would get ~0.006% faster,
because the store is ~10,000x slower than either language's cache logic.
The rewrite hypothesis is refuted *by measurement* - which is the only
honest way to end that argument.

## Quick start

```bash
# Rust side (needs cargo, nothing else)
cargo run --release -- bench --ops 200000 --concurrency 8 --seed 42 --json rust_results.json

# Python side (needs nothing - stdlib only)
python python_twin/twin_bench.py bench --ops 200000 --concurrency 8 --seed 42 --json python_results.json

# prove the twins replay identical ops (must print the same vector)
cargo run --release -- selftest
python python_twin/twin_bench.py selftest
```

## Documentation

- [docs/RESULTS.md](docs/RESULTS.md) - measured tables + findings F1-F4 + verdict
- [docs/METHODOLOGY.md](docs/METHODOLOGY.md) - what is measured, what is not, declared asymmetries
- [docs/DECISIONS.md](docs/DECISIONS.md) - seven ADRs (duplicated harness, shared PRNG, kept runtime asymmetry, no network, ...)

## License

Portfolio demonstration project.

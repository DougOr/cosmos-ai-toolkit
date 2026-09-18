# OrbitBench AI - Results

Generated: 2026-09-05 11:10:06

| meta | value |
|---|---|
| ops | 2000 |
| concurrency | 8 |
| seed | 42 |
| endpoint | https://localhost:8081/ |
| unavailable | [] |

| backend | scenario | ops | errors | hit% | ops/s | mean ms | p50 ms | p95 ms | p99 ms |
|---|---|---|---|---|---|---|---|---|---|
| memory | read_heavy | 2000 | 0 | 100% | 607921 | 0.001 | 0.000 | 0.001 | 0.001 |
| memory | write_heavy | 2000 | 0 | 100% | 446399 | 0.001 | 0.001 | 0.001 | 0.001 |
| memory | mixed | 2000 | 0 | 100% | 536466 | 0.001 | 0.001 | 0.001 | 0.001 |
| memory | hot_key | 2000 | 0 | 100% | 764672 | 0.000 | 0.000 | 0.000 | 0.000 |
| cosmos | read_heavy | 2000 | 22 | 99% | 73 | 104.311 | 23.626 | 550.365 | 1009.143 |
| cosmos | write_heavy | 2000 | 21 | 98% | 36 | 211.750 | 72.628 | 899.248 | 1454.128 |
| cosmos | mixed | 2000 | 11 | 99% | 47 | 156.695 | 42.660 | 676.535 | 1248.953 |
| cosmos | hot_key | 2000 | 15 | 99% | 82 | 91.165 | 17.449 | 534.675 | 1047.441 |

Methodology: prefilled key space (untimed), per-worker seeded RNG,
per-op latency, errors counted not swallowed. Reproduce with
`orbitbench run --md RESULTS.md`.

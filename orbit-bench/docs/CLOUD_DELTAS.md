# Cloud Deltas: what the emulator cannot show

OrbitBench AI's Cosmos backend runs on the local emulator. The benchmark
methodology itself is environment-agnostic; here is what changes with a real
account:

| Cloud capability | Emulator status | OrbitBench impact |
|---|---|---|
| Request-charge (RU) accounting | emulator reports 0 RUs | the natural next metric column: `RU/s` alongside `ops/s` - the hook is `CosmosBackend` (the SDK returns charge per response) |
| Integrated cache / dedicated gateway | not available | would be benchmarked as just another backend (`cosmos-cached`) |
| Multi-region read latency | single node | the `hot_key` scenario becomes genuinely interesting |
| Autoscale throughput | fixed provision | throughput ceilings become visible in ops/s cliffs |
| RBAC auth | key only | `CosmosBackend.create` credential swap |
| Serverless | not available | nothing - scenarios unchanged |

## Honest framing for talks

The v1 caching harness claimed "17.9x faster with cache" from a benchmark
that measured its own simulated sleep against a localhost read. OrbitBench
AI exists to make numbers like that reproducible and dissectable: prefill
untimed, seeded workloads, percentiles, error columns, control-group
backend. The emulator's limits are documented; the *methodology* is the
transferable asset, and it runs identically against a cloud account.

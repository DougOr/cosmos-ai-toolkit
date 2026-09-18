# Running OrbitBench AI on the Azure Cosmos DB Emulator (Windows)

## Setup

1. Install + start the [Cosmos DB emulator](https://learn.microsoft.com/azure/cosmos-db/local-emulator)
   (Windows MSI). It listens on `https://localhost:8081`.
2. `uv sync` in this repo.
3. `uv run orbitbench check` - TLS guard, emulator reachability, backend
   availability in one shot.

The Cosmos key in `.env.example` is the well-known **public** emulator key.
TLS verification is skipped only for localhost endpoints and the config
fails fast otherwise (`Settings.tls_guard()`) - same guard as the other
toolkit repos.

## First run

```bash
uv run orbitbench run --backend memory --backend cosmos --ops 1000 --md RESULTS.md
```

Expected console table (values will differ by machine; format is fixed):

```
backend  scenario   ops  errors  hit%  ops/s  mean  p50  p95  p99
--------------------------------------------------------------------
memory   read_heavy ...
cosmos   read_heavy ...
...
```

Notes:

- The first `cosmos` run creates `OrbitBenchDB.orbit-bench` (a few seconds);
  subsequent runs reuse it.
- Default behaviour **purges** the container before each run for isolation.
  `--no-purge` keeps entries (numbers become load-dependent - your call).
- Redis backend: `uv sync --extra redis` + a local Redis, then
  `--backend redis`.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `NOT REACHABLE` | start the emulator, wait ~20 s |
| `401 Unauthorized` | restore the well-known emulator key |
| `tls guard : FAILED` | endpoint is off-localhost while verification is off - intended |
| Slow first cosmos scenario | container provisioning + JIT compile; run twice, report the second |

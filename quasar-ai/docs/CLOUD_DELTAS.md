# Cloud Deltas: what changes with a real Azure Cosmos DB account

QuasarAI is built and demoed **entirely on the local emulator**. This file is
the honest ledger of what the emulator cannot show, and exactly what code
would change if you pointed it at the cloud. Nothing here is hidden.

## What is identical

The entire data plane: container creation, partition keys, point reads,
upserts, TTL (container `default_ttl` + per-item `ttl`), parameterized SQL
queries, delete, and the `azure.cosmos.aio` SDK surface. `CosmosResources`
is the only module that touches connection details.

## What the emulator cannot demo

| Cloud feature | Why the emulator can't | What QuasarAI would need |
|---|---|---|
| Integrated cache (dedicated gateway) | Requires the cloud dedicated gateway endpoint | Front-door reads via `DedicatedGatewayEndpoint`; engine code unchanged |
| RBAC data-plane auth (Entra ID) | Emulator supports key auth only | Swap `credential=cosmos_key` for `DefaultAzureCredential()` via `azure-identity` |
| Multi-region writes / failover | Single instance | `preferred_locations`; application-level conflict policy becomes real |
| Serverless accounts | Emulator is provisioned-throughput only | None - engine code unchanged |
| Native vector search | Emulator lacks the vector indexing policy | NebulaMind could move its app-side cosine scan into container queries |
| 99.999% SLA, 25 GB+ containers | Emulator caps around 25 GB and one node | Nothing - but the static partition key becomes a real scaling decision |

## Deliberate design choices that become *decisions* in the cloud

1. **Static partition key (`/pk = "primary"`)** - kept from v1 for 1:1
   comparability. In the cloud you would partition by tenant or key hash
   prefix; `docs/DECISIONS.md` ADR-004 covers this.
2. **Per-key in-process locks** - perfect for one service instance. Multiple
   instances need a distributed lock (or accept duplicate generation and let
   upsert converge - already safe in QuasarAI).
3. **Mock LLM as the generator** - swap `MockLLM` for any async provider;
   NebulaMind (the sibling repo) implements the real-LLM version of exactly
   this.

## How to point QuasarAI at the cloud anyway

```env
COSMOS_ENDPOINT=https://<account>.documents.azure.com:443/
COSMOS_KEY=<real key - do not commit>
VERIFY_EMULATOR_TLS=true   # verifies the real cert; guard passes
```

No code changes. The guard exists so that skipping verification stays a
localhost-only accident waiting to be had.

# Cloud Deltas: what the emulator cannot show

NebulaMind runs entirely on the local Cosmos DB emulator. The data plane
(container CRUD, point reads, upserts, TTL, parameterized queries) is
identical in the cloud. What is *not* available on the emulator, and what
would change:

| Cloud capability | Emulator status | What NebulaMind would do |
|---|---|---|
| **Native vector search** (vector indexing policy + `VectorDistance`) | not available | `engine.search` replaces the app-side cosine scan with a container query - the stored `embedding` field is already in the exact shape the policy expects |
| Integrated cache (dedicated gateway) | not available | front-door point reads; engine unchanged |
| RBAC data-plane auth | key auth only | `DefaultAzureCredential()` instead of the key |
| Multi-region | single node | `preferred_locations`; conflict policy matters with multi-writer upserts |
| Serverless | provisioned only | nothing |

## The two honest limitations (also content, not shame)

1. **App-side similarity scan.** `engine.search` pulls the 100 most recent
   entries and computes cosine in Python. That is a deliberate,
   documented trade-off: the emulator cannot demo vector indexes, and for
   demo scales (< thousands of entries) it is fast. The scan boundary is
   one function - the cloud swap is contained.
2. **Lexical default embeddings.** `hash-lexical` embeddings measure
   vocabulary overlap, not meaning. They are labeled `semantic=false` in
   every API response and in the data itself, so nobody mistakes a lexical
   hit for a semantic one. Flip to Ollama (still offline) for true
   embeddings.

## Pointing at the cloud anyway

```env
COSMOS_ENDPOINT=https://<account>.documents.azure.com:443/
COSMOS_KEY=<real key - never commit>
VERIFY_EMULATOR_TLS=true
```

No code changes required; the TLS guard passes because verification is on.

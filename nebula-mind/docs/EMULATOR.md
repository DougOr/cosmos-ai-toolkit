# Running NebulaMind on the Azure Cosmos DB Emulator (Windows)

NebulaMind talks to the **local emulator only** (`https://localhost:8081`).
With the default providers (`LLM_PROVIDER=mock`, `EMBEDDING_PROVIDER=hash`)
nothing else is needed - no LLM API key, no Ollama, no cloud.

## 1. Emulator

1. Install the Azure Cosmos DB Emulator (Windows MSI) - see
   <https://learn.microsoft.com/azure/cosmos-db/local-emulator>.
2. Start it and keep it running on `https://localhost:8081`.
3. The key in `.env.example` is the well-known **public** emulator key. It is
   not a secret and only opens your local emulator.
4. TLS verification is skipped for the self-signed cert, and the config
   **fails fast if the endpoint is not localhost** while verification is
   skipped (`Settings.tls_guard()`).

## 2. Preflight

```bash
uv sync
uv run nebula-mind check
```

`check` reports the TLS guard, emulator reachability, and - depending on
provider choice - Ollama reachability or missing API keys, with a non-zero
exit code when something required is missing.

## 3. Provider matrix (all local, zero cloud)

| LLM_PROVIDER | EMBEDDING_PROVIDER | Needs | Semantic search quality |
|---|---|---|---|
| `mock` (default) | `hash` (default) | nothing | lexical (vocabulary overlap) - honest fallback |
| `ollama` | `ollama` | [Ollama](https://ollama.com) running locally + models pulled | true embeddings, still 100% offline |
| `openai_compatible` | `hash`/`ollama` | an API key (Z.AI / OpenAI / vLLM ...) | depends on embedder; cloud involved - documented, not default |

Example switch to fully-local real LLM + real embeddings:

```env
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3.2
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=nomic-embed-text
SIMILARITY_THRESHOLD=0.85
```

(`ollama pull llama3.2 nomic-embed-text` first. Thresholds differ: true
embedding similarity lives at 0.85+, lexical at ~0.6.)

## 4. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `emulator : NOT REACHABLE` | emulator not running | start it, wait ~20 s |
| `401 Unauthorized` | key changed | restore the well-known key |
| `tls guard : FAILED` | endpoint off-localhost with verification off | intended - see `CLOUD_DELTAS.md` |
| Ollama timeouts | model not pulled / Ollama asleep | `ollama pull ...`, `ollama list` |
| `openai_compat : NO API KEY` | `.env` missing the key | set `OPENAI_COMPAT_API_KEY` (never commit it) |

# NebulaMind Architecture

## Component map

```
        FastAPI (lifespan)                      CLI
   ┌──────────────────────────┐        ┌────────────────────┐
   │ api.py                   │◀───────│ cli.py serve       │
   │  /llm/cache  get-or-gen  │        │ cli.py check       │
   │  /llm/search similarity  │        └────────────────────┘
   │  /llm/entries/{id}       │
   │  /benchmark  /health     │
   └────────────┬─────────────┘
                │ app.state.engine
   ┌────────────▼─────────────┐        ┌─────────────────────────────┐
   │ engine.py                │        │ providers/                  │
   │ SemanticCacheEngine      │───────▶│ LLMProvider                 │
   │  exact: request_hash     │        │  mock | ollama | openai     │
   │  gen:   LLMProvider      │        │ EmbeddingProvider           │
   │  store: embed + upsert   │        │  hash-lexical | ollama      │
   │  search: app-side cosine │        └─────────────────────────────┘
   └────────────┬─────────────┘
   ┌────────────▼─────────────┐
   │ cosmos.py  (aio client)  │   keys.py: request_hash      embeddings.py:
   └────────────┬─────────────┘   sha256 over canonical        hash_embedding,
                │ azure.cosmos.aio json (prompt,system,        cosine
   ┌────────────▼─────────────┐   model,temp,max_tokens)
   │ Cosmos DB emulator       │
   └──────────────────────────┘
```

## Two cache layers

1. **Exact layer.** `request_hash` = sha256 over canonical JSON of
   `(prompt, system, model, temperature, max_tokens)`. Identical request →
   identical hash → point read → instant answer. Per-key `asyncio.Lock`
   prevents stampede (inherited from QuasarAI's design).
2. **Similarity layer.** `POST /llm/search` embeds the query and cosines it
   against stored entry embeddings (app-side, top-100-recent scan).
   It never fabricates answers - it returns *candidates with scores*.

## Document shape (`nebula-cache`)

```json
{
  "id": "<request_hash>",
  "pk": "primary",
  "prompt_preview": "Explain quantum computing...",
  "system_prompt": null,
  "temperature": 0.7,
  "max_tokens": 1000,
  "model": "mock",
  "answer": { "content": "...", "model": "mock", "usage": { }, "latency_ms": 152.3 },
  "embedding": [0.012, -0.044, "..."],
  "embedding_provider": "hash-lexical",
  "embedding_semantic": false,
  "created_at": "2026-09-05T12:00:00+00:00",
  "ttl_value": 3600,
  "ttl": 3600
}
```

`embedding_semantic` is stored **with the data** so any future reader can
tell lexical fallbacks from true embeddings.

## Provider matrix

| Provider | Where it runs | semantic |
|---|---|---|
| `mock` + `hash-lexical` (default) | process-local | false (lexical) |
| `ollama` + `ollama` | localhost:11434 | true |
| `openai_compatible` | external API | depends on embedder |

Swapping providers is config-only; `build_providers()` is the single wiring
point and every provider implements the same ABCs (`providers/base.py`).

## Why the search scan is bounded and honest

`SELECT TOP 100 ... ORDER BY created_at DESC` - the emulator has no vector
index, so similarity runs app-side over recent entries. For demo scale this
is milliseconds; the boundary is one method (`engine.search`). Full ledger:
`CLOUD_DELTAS.md`.

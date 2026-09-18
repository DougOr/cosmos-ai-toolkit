# NebulaMind 🌌

**Real-LLM semantic cache on Azure Cosmos DB.**
Exact hits by canonical request hash, similarity hits with scores - and the
default configuration runs **100% offline** (mock LLM + lexical embeddings),
so the demo works anywhere. Flip one env var to go fully-local-real with
Ollama, or bring your own OpenAI-compatible API.

![python](https://img.shields.io/badge/python-3.11%2B-blue)
![uv](https://img.shields.io/badge/managed%20with-uv-purple)
![scope](https://img.shields.io/badge/scope-local%20emulator%20only-green)
![offline](https://img.shields.io/badge/default%20config-100%25%20offline-brightgreen)

> **Your LLM never answers the same question twice.**

Part of the three-piece Cosmos DB AI toolkit:

| Project | Role |
|---|---|
| [QuasarAI](../cosmos-quasar-ai) | async cache **engine** primitives (stampede locks, parallel bulk, TTL) |
| **NebulaMind** *(this repo)* | **semantic LLM cache**: exact + similarity hits, pluggable providers |
| [OrbitBench AI](../cosmos-orbit-bench) | cache **backends + honest benchmarks** |

## The problem it solves

LLM caching fails two ways. Key-based caches (v1 harness style) serve stale
answers when the caller reuses a key for different prompts. Naive semantic
caches serve *confidently wrong* answers for similar-but-different questions.
NebulaMind takes the safe path through both:

- **Exact layer** - the key is a sha256 over *everything that changes the
  answer* (prompt, system prompt, model, temperature, max_tokens). A hit is
  provably the answer you would have gotten. No caller-invented keys.
- **Similarity layer** - search returns *scored candidates*, never stitched
  answers. You decide what to do with a 0.83 match. The embedder's honesty
  flag (`semantic: true/false`) travels with every response and is stored in
  the data itself.

## Providers (all defaults offline, zero cloud)

| LLM_PROVIDER | EMBEDDING_PROVIDER | Needs | Similarity quality |
|---|---|---|---|
| `mock` *(default)* | `hash` *(default)* | **nothing** | lexical (vocabulary overlap) |
| `ollama` | `ollama` | Ollama running locally | true embeddings, still 100% local |
| `openai_compatible` | either | API key (Z.AI/OpenAI/...) | depends on embedder |

## Quick start

Prerequisites: [uv](https://docs.astral.sh/uv/) + the
[Azure Cosmos DB Emulator](https://learn.microsoft.com/azure/cosmos-db/local-emulator)
running on `https://localhost:8081`. Nothing else for the default config.

```bash
cd cosmos-nebula-mind

uv sync                    # creates .venv, resolves everything
uv run nebula-mind check   # preflight: TLS guard + emulator + providers
uv run nebula-mind serve   # FastAPI on http://127.0.0.1:8002  (Swagger: /docs)
```

Try it:

```bash
# first call generates, second is an exact hit
curl -X POST http://127.0.0.1:8002/llm/cache \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Explain quantum computing in simple terms"}'

curl -X POST http://127.0.0.1:8002/llm/cache \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Explain quantum computing in simple terms"}'

# rephrased question -> similarity search with scores
curl -X POST http://127.0.0.1:8002/llm/search \
  -H "Content-Type: application/json" \
  -d '{"query": "quantum computing explained simply"}'
```

End-to-end demo without HTTP:

```bash
uv run python demo/demo_nebula.py
```

## API

| Method | Path | What it does |
|---|---|---|
| `POST` | `/llm/cache` | get-or-generate: exact hit or LLM call (cached) |
| `POST` | `/llm/search` | similarity search: scored candidates + threshold flags |
| `GET` | `/llm/entries/{entry_id}` | inspect a cached entry (embedding stripped) |
| `DELETE` | `/llm/cache` | clear all entries |
| `GET` | `/benchmark` | generate vs exact-hit latencies + speedup |
| `GET` | `/health` | emulator + provider + embedding-honesty status |

## Configuration

See [.env.example](.env.example) for the full table (provider selection,
Ollama endpoints/models, embedding dim, similarity thresholds per embedder
type, TTL). The Cosmos section is identical to QuasarAI: well-known public
emulator key, TLS guard that refuses non-localhost when verification is off.

## Tests

```bash
uv run pytest              # unit suite - hermetic, no emulator needed
uv run pytest -m emulator  # end-to-end vs the emulator (offline providers)
```

Headline unit test: `test_concurrent_misses_generate_once` - 8 concurrent
identical requests hit the LLM exactly once. And
`test_search_labels_lexical_provider_honestly` - the honesty flag is part of
the contract, tested.

## Benchmark

```bash
curl http://127.0.0.1:8002/benchmark
```

**Measured on this machine** (2026-09-05, Azure Cosmos DB Windows emulator,
mock LLM at 150 ms simulated latency, hash-lexical embeddings):

| Probe | Result |
|---|---|
| Generated (LLM call + embed + store) | 239.3 ms |
| Exact hit (content-hash point read) | 12.1 ms |
| **Speedup** | **20x** |
| Rephrased question → similarity search | score **0.727**, above lexical threshold (0.6) |

Exact hits are the honest speedup number (generation is mocked at a
configurable latency). The 0.727 rephrase score is *lexical* similarity by
the honest default embedder - switch `EMBEDDING_PROVIDER=ollama` (still 100%
local) for true semantic scores. Cross-backend bake-offs live in
[OrbitBench AI](../cosmos-orbit-bench).

## Documentation

- [docs/EMULATOR.md](docs/EMULATOR.md) - setup + provider matrix (all local)
- [docs/CLOUD_DELTAS.md](docs/CLOUD_DELTAS.md) - native vector search, RBAC, and what would change
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - two cache layers, provider matrix, document shape
- [docs/DECISIONS.md](docs/DECISIONS.md) - eight ADRs (content-hash keys, honest lexical fallbacks, candidates-not-answers, ...)

## License

Portfolio demonstration project. Emulator key = well-known public dev key.
If you set `OPENAI_COMPAT_API_KEY`, `.env` is gitignored - keep it that way.

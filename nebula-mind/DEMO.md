# DEMO - NebulaMind in 6 minutes

**Audience:** anyone shipping LLM features (and paying for them twice).
**One-line takeaway:** *"Your LLM never answers the same question twice -
and when the words change but the question doesn't, it shows you the
candidates and their scores instead of guessing."*

Default configuration is 100% offline (mock LLM + lexical embeddings) - the
only infrastructure needed is the local Cosmos DB emulator.

---

## Before the audience arrives (~3 minutes)

1. Start the **Azure Cosmos DB Emulator**, wait ~20 s.
2. Terminal 1:

   ```powershell
   cd nebula-mind
   uv sync
   uv run nebula-mind check      # emulator REACHABLE, mock + hash providers OK
   uv run python demo/demo_nebula.py   # warm-up run (absorbs first-touch cost)
   uv run nebula-mind serve      # http://127.0.0.1:8002
   ```

3. Open **http://127.0.0.1:8002/docs** in the browser.

---

## Act 1 - Pay once (2 min)

In Swagger: **POST `/llm/cache`**, body (Try it out → Execute), **twice**:

```json
{ "prompt": "Explain quantum computing in simple terms" }
```

**First call:** `status: "generated"`, `latency_ms ≈ 239` - the mock LLM
answers, the answer + its embedding are stored.

**Second call:** `status: "exact_hit"`, `latency_ms ≈ 12`,
`similarity: 1.0` - **identical answer content, 20x faster**.

> **Say:** "The exact-match key is a sha256 over the *entire request* -
> prompt, system prompt, model, temperature, max tokens. A hit is provably
> the answer you would have gotten. Caller-invented cache keys are how LLM
> caches serve stale wrong answers; this design makes that bug impossible."

## Act 2 - Different words, same question (90 seconds)

Nobody asks the same question twice with identical wording. **POST
`/llm/search`**:

```json
{ "query": "quantum computing explained simply" }
```

Result: `score ≈ 0.727`, `above_threshold: true`, entry points back to the
cached answer. Latency ~15 ms.

> **Say:** "Rephrase the question and the exact layer misses - so the
> similarity layer shows you the candidates *with scores*. It never
> fabricates a stitched answer for a question nobody asked. A 0.73 match
> means 'possibly the same question'; you decide, with a threshold."

## Act 3 - The honesty engineering (90 seconds)

**GET `/health`**: note `"embedding_provider": "hash-lexical"`,
`"embedding_semantic": false`.

> **Say:** "The default embedder measures vocabulary overlap, not meaning -
> and the cache *says so*: in the health endpoint, in every search response,
> and stored inside every document. Switching to true semantic embeddings is
> one env var - `EMBEDDING_PROVIDER=ollama` - still 100% local. The demo
> never lies about what kind of similarity it's doing."

Optional proof: **GET `/llm/entries/{entry_id}`** (copy the id from Act 1)
- the stored document itself carries `embedding_semantic: false`.

## Act 4 (optional, advanced) - Real LLM, still zero cloud (2 min)

Only if Ollama is installed locally. Stop the server, edit `.env`:

```env
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3.2
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=nomic-embed-text
SIMILARITY_THRESHOLD=0.85
```

`uv run nebula-mind serve` → `/health` now shows `llm: ollama` → repeat
Act 1 with a real model generating real answers. Same code, one config
change - that is the provider abstraction as a live demo.

---

## Contingency plans

| Problem | Fallback |
|---|---|
| Emulator down | `uv run pytest` - the full engine suite runs on fakes; narrate from README's measured table |
| Act 2 score below threshold | Lexical scoring varies by wording - try "quantum computing simple explanation"; or raise the moment by explaining the threshold design |
| Act 4: Ollama slow first call | Model cold-start; say "first call loads the model" and rerun |

## Reset between runs

```powershell
Invoke-RestMethod -Method Delete "http://127.0.0.1:8002/llm/cache"
```

# NebulaMind Decision Record

## ADR-001: Content-hash keys, not caller-supplied keys

**Decision:** the exact-match key is `sha256(canonical(prompt, system, model,
temperature, max_tokens))`.

**Why:** the v1 harness let the caller invent `cache_key` strings, so the
same key could silently serve a stale answer for a different prompt - the
classic key-collision correctness bug in LLM caches. Hashing everything that
changes the answer makes hits provably correct. (Float noise handled by
rounding temperature to 3 decimals.)

## ADR-002: Pluggable providers behind ABCs, mock by default

**Decision:** `LLMProvider` / `EmbeddingProvider` ABCs; `mock` + `hash-lexical`
default; `ollama` and `openai_compatible` optional.

**Why:** the "Real LLM" in the pitch must not *require* cloud or even a GPU.
The default pair runs anywhere in milliseconds, keeps CI hermetic, and the
same engine code is exercised that would run against a real model. Providers
are config-only swaps via one factory.

## ADR-003: Lexical fallback embeddings, labeled everywhere

**Decision:** the offline embedder hashes words + char-trigrams (lexical
similarity). It self-reports `name="hash-lexical"`, `semantic=False`, and
that flag is stored in each document and returned in every search response.

**Why:** the alternative - pretending hash vectors are semantic - would make
the demo lie. Honest labeling turns a limitation into a documented boundary,
and the upgrade path (Ollama, still zero cloud) is one env change.

## ADR-004: App-side cosine, bounded scan

**Decision:** similarity search = embed query, pull `TOP 100` recent entries,
cosine in Python, sort, threshold.

**Why:** the emulator has no native vector search. The scan is bounded,
fast at demo scale, and quarantined in one method for the cloud swap
(`VectorDistance` + vector index policy). Ledger: `CLOUD_DELTAS.md`.

## ADR-005: Search returns candidates, never fabricates answers

**Decision:** `search` returns scored references to *existing* cached
answers; it does not synthesize a stitched answer.

**Why:** similarity below 1.0 means "possibly the same question". Returning
"the answer" for a similar-but-different question is how semantic caches
become confidently wrong. Callers decide what to do with score + threshold
(the API marks `above_threshold` per hit).

## ADR-006: Prompt previews, capped at 200 chars

**Decision:** documents store `prompt_preview = prompt[:200]`, full prompt
never persisted.

**Why:** prompts are the most sensitive artifact in an LLM stack; the cache
needs previews for humans, not archives. (Cloud delta note: for regulated
workloads, this is also where you would plug DLP.)

## ADR-007: Emulator-only defaults with a TLS guard

**Decision:** same guarded pattern as QuasarAI - skipped TLS verification
only ever applies to localhost; `Settings.tls_guard()` fails fast otherwise.

**Why:** the emulator shortcut must not be able to leak into a cloud
configuration by accident.

## ADR-008: Inherited QuasarAI mechanics

**Decision:** async SDK only, per-key locks, upsert over create,
timezone-aware timestamps, `-1` = never expire, parameterized queries.

**Why:** no reason to re-litigate - each is an ADR in
`cosmos-quasar-ai/docs/DECISIONS.md` with the v1 failure that motivated it.
Consistency across the toolkit is a feature.

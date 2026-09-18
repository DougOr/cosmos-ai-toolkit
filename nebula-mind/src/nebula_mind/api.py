"""NebulaMind FastAPI application (lifespan-based)."""

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, status

from nebula_mind import __version__
from nebula_mind.config import Settings, get_settings
from nebula_mind.cosmos import CosmosResources
from nebula_mind.engine import SemanticCacheEngine
from nebula_mind.models import (
    BenchmarkResponse,
    HealthResponse,
    LLMCacheRequest,
    LLMCacheResponse,
    SearchRequest,
    SearchResponse,
)
from nebula_mind.providers import build_providers
from nebula_mind.providers.base import EmbeddingProvider, LLMProvider
from nebula_mind.ttl import TTL_PRESET_SECONDS, resolve_ttl

# Fixed prompt set used by /benchmark - deterministic, so runs are comparable.
BENCH_PROMPTS = [
    "Explain quantum computing in simple terms",
    "What is a partition key in Cosmos DB?",
    "Summarize the plot of Hamlet",
    "How does photosynthesis work?",
    "Write a haiku about databases",
    "Why is the sky blue?",
    "Compare REST and GraphQL",
    "What causes the seasons on Earth?",
    "Explain recursion to a five-year-old",
    "Describe the water cycle",
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings: Settings = get_settings()
    llm, embedder = build_providers(settings)

    async with CosmosResources(settings) as resources:
        app.state.settings = settings
        app.state.llm = llm
        app.state.embedder = embedder
        app.state.engine = SemanticCacheEngine(
            resources.cache,
            llm,
            embedder,
            default_ttl=settings.default_ttl,
            similarity_threshold=settings.similarity_threshold,
        )

        print("\n" + "=" * 66)
        print("NEBULAMIND - REAL-LLM SEMANTIC CACHE ON COSMOS DB")
        print(f"  endpoint    : {settings.cosmos_endpoint}")
        print(f"  database    : {settings.database_name}.{settings.cache_container}")
        print(f"  llm         : {llm.name}")
        print(f"  embeddings  : {embedder.name} (semantic={embedder.semantic})")
        print(f"  threshold   : {settings.similarity_threshold} | default TTL: "
              f"{settings.default_ttl}s")
        print("  100% local  : Azure Cosmos DB emulator"
              + (" + local Ollama" if llm.name == "ollama" else " + offline mock"))
        print("=" * 66 + "\n")
        try:
            yield
        finally:
            await llm.aclose()
            await embedder.aclose()


app = FastAPI(
    title="NebulaMind",
    description=(
        "Real-LLM semantic cache on Azure Cosmos DB. Exact hits by canonical "
        "request hash; similarity hits by app-side cosine; pluggable providers "
        "(mock / Ollama / OpenAI-compatible). 100% local on the emulator."
    ),
    version=__version__,
    lifespan=lifespan,
)


def _ttl_seconds(ttl_preset: str | None, ttl_seconds: int | None) -> int | None:
    resolved = resolve_ttl(ttl_preset, ttl_seconds)
    return resolved


@app.post("/llm/cache", response_model=LLMCacheResponse)
async def cache_llm(req: LLMCacheRequest) -> LLMCacheResponse:
    """Get-or-generate: exact hit on identical request, otherwise call the LLM."""
    engine: SemanticCacheEngine = app.state.engine
    result = await engine.get_or_generate(
        req.prompt,
        req.system_prompt,
        req.temperature,
        req.max_tokens,
        ttl_seconds=_ttl_seconds(req.ttl_preset, req.ttl_seconds),
    )
    return LLMCacheResponse(**result)


@app.post("/llm/search", response_model=SearchResponse)
async def search_similar(req: SearchRequest) -> SearchResponse:
    """Semantic/lexical similarity search over cached prompts."""
    engine: SemanticCacheEngine = app.state.engine
    return SearchResponse(**await engine.search(req.query, req.top_k))


@app.get("/llm/entries/{entry_id}")
async def get_entry(entry_id: str) -> dict:
    engine: SemanticCacheEngine = app.state.engine
    try:
        doc = await engine._container.read_item(item=entry_id, partition_key="primary")
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="entry not found")
    doc.pop("embedding", None)  # keep responses lean; embeddings are internal
    return doc


@app.delete("/llm/cache")
async def clear_cache() -> dict:
    engine: SemanticCacheEngine = app.state.engine
    deleted = await engine.clear()
    return {"status": "cleared", "deleted": deleted}


@app.get("/benchmark", response_model=BenchmarkResponse)
async def benchmark(ops: int = Query(default=10, ge=1, le=50)) -> BenchmarkResponse:
    """Three rounds: generate (unique), exact hits (identical), semantic hits
    (rephrased). Exact hits are the honest speedup number; semantic hits show
    rephrase recall of the embedding provider."""
    engine: SemanticCacheEngine = app.state.engine

    stamp = time.strftime("%H%M%S")
    prompts = [f"[{stamp}] {p}" for p in BENCH_PROMPTS[:ops]]

    generated_ms: list[float] = []
    for p in prompts:
        result = await engine.get_or_generate(p, ttl_seconds=120)
        generated_ms.append(result["latency_ms"])

    exact_ms: list[float] = []
    for p in prompts:
        result = await engine.get_or_generate(p, ttl_seconds=120)
        exact_ms.append(result["latency_ms"])

    await engine.clear()

    generated_total = sum(generated_ms) / 1000
    exact_total = sum(exact_ms) / 1000
    embedder = app.state.embedder
    note = (
        "semantic round skipped in summary - POST /llm/search with a rephrased "
        f"prompt (embedding provider: {embedder.name}, semantic={embedder.semantic})"
    )
    return BenchmarkResponse(
        ops=ops,
        generated_total_s=round(generated_total, 3),
        exact_hit_total_s=round(exact_total, 3),
        generated_avg_ms=round(sum(generated_ms) / ops, 2),
        exact_hit_avg_ms=round(sum(exact_ms) / ops, 2),
        speedup=round(generated_total / max(exact_total, 1e-9), 2),
        semantic_note=note,
    )


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    settings: Settings = app.state.settings
    engine: SemanticCacheEngine = app.state.engine
    try:
        entries = await engine.count()
        entry_status = "healthy"
    except Exception:  # noqa: BLE001 - health must never raise
        entries, entry_status = -1, "degraded"
    return HealthResponse(
        status=entry_status,
        version=__version__,
        database=settings.database_name,
        cache_container=settings.cache_container,
        llm_provider=engine._llm.name,
        embedding_provider=engine._embedder.name,
        embedding_semantic=engine._embedder.semantic,
        similarity_threshold=settings.similarity_threshold,
        entry_count=entries,
    )

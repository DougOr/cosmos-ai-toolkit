"""FastAPI application (lifespan-based - the deprecated on_event hook is gone)."""

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, status

from quasar_ai import __version__
from quasar_ai.config import Settings, get_settings
from quasar_ai.cosmos import CosmosResources
from quasar_ai.engine import AsyncCacheEngine, CacheResult, GenericStore
from quasar_ai.generators import MockLLM
from quasar_ai.models import (
    BenchmarkResponse,
    BulkRequest,
    BulkResponse,
    CachePutRequest,
    GenericPutRequest,
    HealthResponse,
    InvalidateResponse,
    WarmRequest,
)
from quasar_ai.ttl import TTL_PRESET_SECONDS, resolve_ttl


def _ttl_from(ttl_preset: str | None, ttl_seconds: int | None) -> int | None:
    """Map request TTL fields onto the engine convention (<=0 = never expire)."""
    resolved = resolve_ttl(ttl_preset, ttl_seconds)
    if resolved is None:
        return None
    return resolved  # -1 (indefinite) flows through; engine treats <=0 as never


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings: Settings = get_settings()
    async with CosmosResources(settings) as resources:
        app.state.settings = settings
        app.state.engine = AsyncCacheEngine(resources.intelligent, settings.default_ttl)
        app.state.generic = GenericStore(resources.generic, settings.default_ttl)
        app.state.mock = MockLLM(settings.simulated_latency_seconds)

        print("\n" + "=" * 66)
        print("QUASARAI - ASYNC-FIRST COSMOS DB CACHE ENGINE")
        print(f"  endpoint    : {settings.cosmos_endpoint}")
        print(f"  database    : {settings.database_name}")
        print(f"  containers  : {settings.intelligent_container}, {settings.generic_container}")
        print(f"  default TTL : {settings.default_ttl}s | mock latency: "
              f"{settings.simulated_latency_seconds}s")
        print("  100% local  : Azure Cosmos DB emulator, zero cloud")
        print("=" * 66 + "\n")
        yield


app = FastAPI(
    title="QuasarAI",
    description=(
        "Async-first Azure Cosmos DB caching engine for LLM workloads. "
        "Stampede-protected get-or-generate, genuine parallel bulk ops, "
        "TTL presets, parameterized invalidation. 100% local on the emulator."
    ),
    version=__version__,
    lifespan=lifespan,
)


@app.post("/cache", status_code=status.HTTP_201_CREATED)
async def put_cache(req: CachePutRequest) -> dict:
    """Generate with the mock LLM and cache the result under `cache_key`."""
    engine: AsyncCacheEngine = app.state.engine
    mock: MockLLM = app.state.mock

    async def generator(key: str) -> dict:
        return await mock.generate(req.user_prompt, req.system_prompt)

    result = await engine.get_or_generate(
        req.cache_key, generator, ttl_seconds=_ttl_from(req.ttl_preset, req.ttl_seconds)
    )
    return result.as_dict() | {"forced": True}


@app.get("/cache/{cache_key}")
async def get_cache(cache_key: str) -> dict:
    """Get-or-generate: first call is a miss (generates + caches), then a hit."""
    engine: AsyncCacheEngine = app.state.engine
    mock: MockLLM = app.state.mock
    result = await engine.get_or_generate(cache_key, mock.generate_for_key)
    return result.as_dict()


@app.delete("/cache/{cache_key}")
async def delete_cache(cache_key: str) -> dict:
    engine: AsyncCacheEngine = app.state.engine
    if not await engine.invalidate(cache_key):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"cache key '{cache_key}' not found")
    return {"status": "deleted", "cache_key": cache_key}


@app.post("/cache/bulk", status_code=status.HTTP_201_CREATED)
async def bulk_cache(req: BulkRequest) -> BulkResponse:
    engine: AsyncCacheEngine = app.state.engine
    mock: MockLLM = app.state.mock
    results = await engine.bulk_get_or_generate(
        [(item.cache_key, _ttl_from(item.ttl_preset, item.ttl_seconds)) for item in req.items],
        mock.generate_for_key,
    )
    return BulkResponse(
        results=[r.as_dict() for r in results],
        total=len(results),
        successful=len(results),
        failed=0,
    )


@app.post("/cache/warm", status_code=status.HTTP_201_CREATED)
async def warm_cache(req: WarmRequest) -> dict:
    """Pre-generate common keys so real traffic starts on hits."""
    engine: AsyncCacheEngine = app.state.engine
    mock: MockLLM = app.state.mock
    started = time.perf_counter()
    keys = [f"common_{p}" for p in (
        "greeting", "faq", "help", "support", "docs", "tutorial",
        "getting_started", "troubleshooting", "best_practices", "api_reference",
        "examples", "templates", "config",
    )[: req.count]]
    results = await engine.bulk_get_or_generate(
        [(k, _ttl_from(req.ttl_preset, None)) for k in keys], mock.generate_for_key
    )
    return {
        "warmed": len(results),
        "keys": keys,
        "duration_ms": round((time.perf_counter() - started) * 1000, 2),
    }


@app.delete("/cache/invalidate")
async def invalidate_cache(pattern: str = Query(default="")) -> InvalidateResponse:
    engine: AsyncCacheEngine = app.state.engine
    deleted = await engine.invalidate(pattern or None)
    return InvalidateResponse(status="invalidated", pattern=pattern or None, deleted=deleted)


@app.post("/generic", status_code=status.HTTP_201_CREATED)
async def put_generic(req: GenericPutRequest) -> dict:
    store: GenericStore = app.state.generic
    ttl_remaining = await store.set(
        req.key, req.data, ttl_seconds=_ttl_from(req.ttl_preset, req.ttl_seconds)
    )
    return {"status": "created", "key": req.key, "ttl_remaining": ttl_remaining}


@app.get("/generic/{key}")
async def get_generic(key: str) -> dict:
    store: GenericStore = app.state.generic
    found = await store.get(key)
    if found is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"'{key}' not found")
    data, remaining = found
    return {"status": "hit", "key": key, "data": data, "ttl_remaining": remaining}


@app.delete("/generic/{key}")
async def delete_generic(key: str) -> dict:
    store: GenericStore = app.state.generic
    if not await store.delete(key):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"'{key}' not found")
    return {"status": "deleted", "key": key}


@app.get("/benchmark")
async def benchmark(ops: int = Query(default=25, ge=1, le=200)) -> BenchmarkResponse:
    """Miss-then-hit race with p95s. The deep bake-off lives in OrbitBench AI."""
    engine: AsyncCacheEngine = app.state.engine
    mock: MockLLM = app.state.mock

    stamp = time.strftime("%Y%m%d%H%M%S")
    miss_latencies: list[float] = []
    for i in range(ops):
        result = await engine.get_or_generate(f"bench_{stamp}_{i}", mock.generate_for_key)
        miss_latencies.append(result.latency_ms)

    hit_key = f"bench_{stamp}_0"
    hit_latencies: list[float] = []
    for _ in range(ops):
        result = await engine.get_or_generate(hit_key, mock.generate_for_key)
        hit_latencies.append(result.latency_ms)

    miss_total = sum(miss_latencies) / 1000
    hit_total = sum(hit_latencies) / 1000

    def p95(samples: list[float]) -> float:
        ordered = sorted(samples)
        return ordered[min(len(ordered) - 1, int(0.95 * len(ordered)))]

    await engine.invalidate("bench_")
    return BenchmarkResponse(
        ops=ops,
        miss_total_s=round(miss_total, 3),
        hit_total_s=round(hit_total, 3),
        miss_avg_ms=round(sum(miss_latencies) / ops, 2),
        hit_avg_ms=round(sum(hit_latencies) / ops, 2),
        miss_p95_ms=round(p95(miss_latencies), 2),
        hit_p95_ms=round(p95(hit_latencies), 2),
        speedup=round(miss_total / max(hit_total, 1e-9), 2),
    )


@app.get("/health")
async def health() -> HealthResponse:
    settings: Settings = app.state.settings
    engine: AsyncCacheEngine = app.state.engine
    try:
        entries = await engine.count()
        entry_status = "healthy"
    except Exception:  # noqa: BLE001 - health must never raise
        entries, entry_status = -1, "degraded"
    return HealthResponse(
        status=entry_status,
        version=__version__,
        database=settings.database_name,
        intelligent_container=settings.intelligent_container,
        generic_container=settings.generic_container,
        default_ttl=settings.default_ttl,
        ttl_presets=list(TTL_PRESET_SECONDS),
        entry_count=entries,
    )

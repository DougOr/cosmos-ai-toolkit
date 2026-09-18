"""OrbitBench AI FastAPI app - run benchmark suites over HTTP."""

import time
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from orbitbench import __version__
from orbitbench.backends import AVAILABLE_BACKENDS, backend_available, create_backend
from orbitbench.config import Settings, get_settings
from orbitbench.metrics import Stats, console_table
from orbitbench.report import save_json, save_markdown
from orbitbench.runner import run_scenario
from orbitbench.workloads import SCENARIOS, Scenario


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings: Settings = get_settings()
    app.state.settings = settings
    print("\n" + "=" * 66)
    print("ORBITBENCH AI - PLUGGABLE CACHE BACKENDS + HONEST BENCHMARKS")
    print(f"  endpoint : {settings.cosmos_endpoint}")
    print(f"  backends : {', '.join(b for b in AVAILABLE_BACKENDS if backend_available(b))}")
    print("  100% local: Azure Cosmos DB emulator, zero cloud")
    print("=" * 66 + "\n")
    yield


app = FastAPI(
    title="OrbitBench AI",
    description=(
        "Every cache backend in orbit around one protocol; every number on "
        "record. Deterministic scenarios, per-op latency, p50/p95/p99."
    ),
    version=__version__,
    lifespan=lifespan,
)


class BenchRunRequest(BaseModel):
    backends: list[Literal["memory", "cosmos", "redis"]] = ["memory", "cosmos"]
    scenarios: list[str] = ["read_heavy", "write_heavy", "mixed", "hot_key"]
    ops: int = 1000
    concurrency: int = 8
    seed: int = 42
    purge: bool = True
    save_md: str | None = None
    save_json: str | None = None


@app.post("/bench/run")
async def run_benchmark(req: BenchRunRequest) -> dict:
    """Fresh backend instances, prefilled key spaces, per-op stats."""
    for name in req.backends:
        if not backend_available(name):
            raise HTTPException(status_code=400, detail=f"backend '{name}' unavailable")
    for name in req.scenarios:
        if name not in SCENARIOS:
            raise HTTPException(
                status_code=400, detail=f"unknown scenario '{name}' - "
                f"available: {', '.join(SCENARIOS)}"
            )

    req.ops = min(req.ops, 50_000)
    req.concurrency = min(max(req.concurrency, 1), 64)

    started = time.perf_counter()
    results: list[Stats] = []
    skipped: list[dict] = []
    settings: Settings = app.state.settings

    for backend_name in req.backends:
        try:
            backend = await create_backend(backend_name, settings, purge=req.purge)
        except Exception as exc:  # noqa: BLE001 - skip cleanly, keep other numbers
            skipped.append({"backend": backend_name, "error": str(exc)})
            continue
        try:
            for scenario_name in req.scenarios:
                base = SCENARIOS[scenario_name]
                scenario = Scenario(
                    name=base.name,
                    ops=req.ops,
                    read_ratio=base.read_ratio,
                    key_space=base.key_space,
                    concurrency=req.concurrency,
                    value_bytes=base.value_bytes,
                    ttl_seconds=base.ttl_seconds,
                )
                results.append(await run_scenario(backend, scenario, req.seed))
        finally:
            await backend.close()

    duration_s = time.perf_counter() - started
    meta = {
        "ops": req.ops,
        "concurrency": req.concurrency,
        "seed": req.seed,
        "purge": req.purge,
        "endpoint": settings.cosmos_endpoint,
    }

    saved = {}
    if req.save_md:
        saved["markdown"] = str(save_markdown(results, req.save_md, meta))
    if req.save_json:
        saved["json"] = str(save_json(results, req.save_json, meta))

    return {
        "duration_s": round(duration_s, 3),
        "meta": meta,
        "results": [s.as_dict() for s in results],
        "skipped": skipped,
        "table": console_table(results),
        "saved": saved,
    }


@app.get("/backends")
async def list_backends() -> dict:
    settings: Settings = app.state.settings
    info = {}
    for name in AVAILABLE_BACKENDS:
        entry = {"available": backend_available(name)}
        if entry["available"] and name in ("memory", "cosmos", "redis"):
            try:
                backend = await create_backend(name, settings, purge=False)
                entry["health"] = await backend.health()
                await backend.close()
            except Exception as exc:  # noqa: BLE001
                entry = {"available": False, "error": str(exc)}
        info[name] = entry
    return info


@app.get("/scenarios")
async def list_scenarios() -> dict:
    return {name: vars(scenario) for name, scenario in SCENARIOS.items()}


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy", "version": __version__,
            "backends": [b for b in AVAILABLE_BACKENDS if backend_available(b)]}

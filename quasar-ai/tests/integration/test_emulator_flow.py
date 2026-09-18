"""End-to-end engine flow against the real local emulator.

Self-skips when the emulator is not running, so `uv run pytest` is green
everywhere. Force them with:  uv run pytest -m emulator
"""

import warnings

import httpx
import pytest

from quasar_ai.config import WELL_KNOWN_EMULATOR_KEY, Settings
from quasar_ai.cosmos import CosmosResources
from quasar_ai.engine import AsyncCacheEngine, GenericStore
from quasar_ai.generators import MockLLM


def _emulator_up() -> bool:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            httpx.get("https://localhost:8081/", verify=False, timeout=1.5)
        return True
    except Exception:  # noqa: BLE001
        return False


pytestmark = [
    pytest.mark.emulator,
    pytest.mark.skipif(
        not _emulator_up(),
        reason="Azure Cosmos DB emulator not reachable on https://localhost:8081",
    ),
]


def test_settings() -> Settings:
    return Settings(
        cosmos_endpoint="https://localhost:8081/",
        cosmos_key=WELL_KNOWN_EMULATOR_KEY,
        database_name="QuasarTestDB",
        intelligent_container="t-intelligent",
        generic_container="t-generic",
        simulated_latency_seconds=0.0,
    )


async def test_miss_hit_invalidate_against_emulator():
    mock = MockLLM(latency_seconds=0.0)
    async with CosmosResources(test_settings()) as resources:
        engine = AsyncCacheEngine(resources.intelligent, default_ttl=120)

        miss = await engine.get_or_generate("e2e-key", mock.generate_for_key, ttl_seconds=300)
        assert miss.status == "miss"
        assert miss.ttl_remaining is not None and miss.ttl_remaining > 290

        hit = await engine.get_or_generate("e2e-key", mock.generate_for_key)
        assert hit.status == "hit"
        assert hit.payload == miss.payload
        assert hit.latency_ms <= miss.latency_ms

        assert await engine.invalidate("e2e-key") >= 1


async def test_generic_store_against_emulator():
    async with CosmosResources(test_settings()) as resources:
        store = GenericStore(resources.generic, default_ttl=120)

        await store.set("flags", {"beta": True}, ttl_seconds=60)
        found = await store.get("flags")
        assert found is not None
        data, remaining = found
        assert data == {"beta": True}
        assert remaining is not None and remaining > 50

        assert await store.delete("flags") is True
        assert await store.get("flags") is None


async def test_stampede_single_generation_against_emulator():
    mock = MockLLM(latency_seconds=0.0)
    async with CosmosResources(test_settings()) as resources:
        engine = AsyncCacheEngine(resources.intelligent, default_ttl=120)
        key = "e2e-stampede"

        first = await engine.get_or_generate(key, mock.generate_for_key)
        assert first.status == "miss"

        repeats = await asyncio_gather_hits(engine, key, mock)
        assert all(r.status == "hit" for r in repeats)


async def asyncio_gather_hits(engine: AsyncCacheEngine, key: str, mock: MockLLM):
    import asyncio

    return await asyncio.gather(*(engine.get_or_generate(key, mock.generate_for_key) for _ in range(8)))

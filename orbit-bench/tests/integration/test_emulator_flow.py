"""Cosmos backend CRUD + a small honest scenario vs the real emulator.

Self-skips when the emulator is down. Force: uv run pytest -m emulator
"""

import warnings

import httpx
import pytest

from orbitbench.backends.cosmos_backend import CosmosBackend
from orbitbench.config import WELL_KNOWN_EMULATOR_KEY, Settings
from orbitbench.runner import run_scenario
from orbitbench.workloads import SCENARIOS


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
        database_name="OrbitBenchTestDB",
        bench_container="t-orbit",
    )


async def test_cosmos_backend_roundtrip():
    backend = await CosmosBackend.create(test_settings())
    try:
        await backend.clear()

        assert await backend.get("roundtrip") is None
        await backend.set("roundtrip", {"v": 42}, ttl_seconds=120)
        assert await backend.get("roundtrip") == {"v": 42}
        assert await backend.delete("roundtrip") is True
        assert await backend.delete("roundtrip") is False
    finally:
        await backend.close()


async def test_cosmos_backend_small_scenario():
    from dataclasses import replace

    backend = await CosmosBackend.create(test_settings())
    try:
        await backend.clear()
        small = replace(SCENARIOS["read_heavy"], ops=60, key_space=20, concurrency=4)
        stats = await run_scenario(backend, small, seed=42)
        assert stats.ops == 60
        assert stats.errors == 0
        assert stats.hit_ratio > 0.8
    finally:
        await backend.close()

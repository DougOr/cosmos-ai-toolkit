"""End-to-end semantic-cache flow vs the emulator, using OFFLINE providers
(mock LLM + lexical hash embeddings) - so these tests prove the Cosmos side
without any network beyond localhost.

Self-skips when the emulator is down. Force: uv run pytest -m emulator
"""

import warnings

import httpx
import pytest

from nebula_mind.config import WELL_KNOWN_EMULATOR_KEY, Settings
from nebula_mind.cosmos import CosmosResources
from nebula_mind.engine import SemanticCacheEngine
from nebula_mind.providers.mock import HashEmbeddingProvider, MockLLMProvider


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
        database_name="NebulaTestDB",
        cache_container="t-nebula",
        simulated_latency_seconds=0.0,
    )


def make_engine(resources) -> SemanticCacheEngine:
    return SemanticCacheEngine(
        resources.cache,
        MockLLMProvider(0.0),
        HashEmbeddingProvider(dim=512),
        default_ttl=120,
        similarity_threshold=0.5,
    )


async def test_generate_exact_hit_and_search():
    async with CosmosResources(test_settings()) as resources:
        engine = make_engine(resources)
        try:
            generated = await engine.get_or_generate(
                "Explain quantum computing in simple terms", ttl_seconds=120
            )
            assert generated["status"] == "generated"

            exact = await engine.get_or_generate(
                "Explain quantum computing in simple terms", ttl_seconds=120
            )
            assert exact["status"] == "exact_hit"
            assert exact["similarity"] == 1.0

            search = await engine.search("quantum computing simple explanation")
            assert search["scanned"] >= 1
            assert search["hits"][0]["score"] > 0.3
        finally:
            await engine.clear()

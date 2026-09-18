"""Provider behaviour: mock determinism, factory wiring, bad combos."""

import pytest

from nebula_mind.config import Settings
from nebula_mind.providers import build_providers
from nebula_mind.providers.mock import HashEmbeddingProvider, MockLLMProvider


async def test_mock_llm_deterministic():
    llm = MockLLMProvider(latency_seconds=0.0)
    a = await llm.generate("same question")
    b = await llm.generate("same question")
    assert a.content == b.content
    assert a.usage == b.usage


async def test_mock_llm_respects_max_tokens_in_usage():
    llm = MockLLMProvider(latency_seconds=0.0)
    small = await llm.generate("q", max_tokens=10)
    assert small.usage["output_tokens"] <= 10


def test_factory_default_is_offline_pair():
    llm, embedder = build_providers(Settings(_env_file=None))
    assert isinstance(llm, MockLLMProvider)
    assert isinstance(embedder, HashEmbeddingProvider)
    assert embedder.semantic is False


def test_factory_unknown_provider_raises():
    settings = Settings(_env_file=None, llm_provider="skynet")
    with pytest.raises(ValueError, match="skynet"):
        build_providers(settings)


def test_factory_openai_requires_key():
    settings = Settings(_env_file=None, llm_provider="openai_compatible")
    with pytest.raises(ValueError, match="OPENAI_COMPAT_API_KEY is empty"):
        build_providers(settings)

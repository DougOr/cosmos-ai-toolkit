"""Engine behaviour on fakes: exact hits, single generation, search, clear."""

import asyncio

from nebula_mind.embeddings import cosine, hash_embedding
from nebula_mind.engine import SemanticCacheEngine

from .fakes import FakeContainer, FakeLLMProvider, FixedEmbeddingProvider


def make_engine(threshold: float = 0.5) -> tuple[SemanticCacheEngine, FakeContainer, FakeLLMProvider]:
    container = FakeContainer()
    llm = FakeLLMProvider()
    vocab = {
        "quantum": [1.0, 0.0, 0.0, 0.0],
        "computing": [0.0, 1.0, 0.0, 0.0],
        "cake": [0.0, 0.0, 1.0, 0.0],
        "recipe": [0.0, 0.0, 0.0, 1.0],
    }
    engine = SemanticCacheEngine(
        container,
        llm,
        FixedEmbeddingProvider(vocab),
        default_ttl=60,
        similarity_threshold=threshold,
    )
    return engine, container, llm


async def test_generated_then_exact_hit():
    engine, _, llm = make_engine()

    first = await engine.get_or_generate("Explain quantum computing", temperature=0.7)
    assert first["status"] == "generated"
    assert first["source"] == "fake-llm"
    assert first["similarity"] is None

    second = await engine.get_or_generate("Explain quantum computing", temperature=0.7)
    assert second["status"] == "exact_hit"
    assert second["source"] == "cache"
    assert second["similarity"] == 1.0
    assert second["answer"] == first["answer"]
    assert llm.calls == ["Explain quantum computing"]  # LLM called exactly once


async def test_different_params_are_different_entries():
    engine, container, llm = make_engine()
    await engine.get_or_generate("q", temperature=0.7)
    await engine.get_or_generate("q", temperature=0.9)
    assert len(container.docs) == 2
    assert len(llm.calls) == 2


async def test_concurrent_misses_generate_once():
    engine, _, llm = make_engine()
    results = await asyncio.gather(
        *(engine.get_or_generate("hot prompt") for _ in range(8))
    )
    assert llm.calls == ["hot prompt"]
    assert sum(1 for r in results if r["status"] == "generated") == 1
    assert all(r["answer"]["content"] == results[0]["answer"]["content"] for r in results)


async def test_search_ranks_semantic_over_unrelated():
    engine, container, _ = make_engine(threshold=0.5)
    await engine.get_or_generate("quantum computing", temperature=0.7)
    await engine.get_or_generate("cake recipe", temperature=0.7)

    result = await engine.search("quantum computing explained", top_k=2)

    assert result["scanned"] == 2
    hits = result["hits"]
    assert hits[0]["prompt_preview"].startswith("quantum computing")
    assert hits[0]["score"] > hits[1]["score"]
    assert hits[0]["above_threshold"] is True
    assert result["embedding_semantic"] is True  # FixedEmbeddingProvider flags true


async def test_search_labels_lexical_provider_honestly():
    container = FakeContainer()
    from nebula_mind.providers.mock import HashEmbeddingProvider, MockLLMProvider

    engine = SemanticCacheEngine(
        container, MockLLMProvider(0.0), HashEmbeddingProvider(dim=256), default_ttl=60
    )
    result = await engine.search("anything")
    assert result["embedding_provider"] == "hash-lexical"
    assert result["embedding_semantic"] is False


async def test_clear_and_count():
    engine, container, _ = make_engine()
    await engine.get_or_generate("one")
    await engine.get_or_generate("two")
    assert await engine.count() == 2
    assert await engine.clear() == 2
    assert await engine.count() == 0


async def test_ttl_written_correctly():
    engine, container, _ = make_engine()
    await engine.get_or_generate("t", ttl_seconds=300)
    doc = next(iter(container.docs.values()))
    assert doc["ttl_value"] == 300
    assert doc["ttl"] == 300
    await engine.get_or_generate("forever", ttl_seconds=-1)
    doc = [d for d in container.docs.values() if d["prompt_preview"] == "forever"][0]
    assert doc["ttl"] == -1

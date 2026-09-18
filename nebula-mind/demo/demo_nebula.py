"""NebulaMind end-to-end demo - run with the emulator up:

    uv run python demo/demo_nebula.py

Fully offline story (mock LLM + lexical hash embeddings):
  1. ask a question            -> generated
  2. ask the SAME question     -> exact hit (similarity 1.0)
  3. ask a REPHRASED question  -> found by /llm/search with a score
  4. switch .env to Ollama for true semantic embeddings (still zero cloud)
"""

import asyncio

from nebula_mind.config import get_settings
from nebula_mind.cosmos import CosmosResources
from nebula_mind.engine import SemanticCacheEngine
from nebula_mind.providers import build_providers


def banner(title: str) -> None:
    print(f"\n{'=' * 62}\n{title}\n{'=' * 62}")


async def main() -> None:
    settings = get_settings()
    llm, embedder = build_providers(settings)

    async with CosmosResources(settings) as resources:
        engine = SemanticCacheEngine(
            resources.cache,
            llm,
            embedder,
            default_ttl=settings.default_ttl,
            similarity_threshold=settings.similarity_threshold,
        )

        question = "Explain quantum computing in simple terms"

        banner(f"1. FIRST ASK (provider: {llm.name})")
        first = await engine.get_or_generate(question)
        print(f"status   : {first['status']}")
        print(f"latency  : {first['latency_ms']} ms")
        print(f"answer   : {first['answer']['content'][:90]}")

        banner("2. SAME ASK AGAIN")
        second = await engine.get_or_generate(question)
        print(f"status   : {second['status']} | similarity: {second['similarity']}")
        print(f"latency  : {second['latency_ms']} ms "
              f"({first['latency_ms'] / max(second['latency_ms'], 0.01):.0f}x faster)")
        assert second["answer"]["content"] == first["answer"]["content"]

        banner("3. REPHRASED ASK -> similarity search")
        search = await engine.search("quantum computing explained simply")
        print(f"provider : {search['embedding_provider']} (semantic={search['embedding_semantic']})")
        for hit in search["hits"][:3]:
            marker = "ABOVE threshold" if hit["above_threshold"] else "below threshold"
            print(f"  score {hit['score']:.3f} [{marker}] {hit['prompt_preview'][:60]}")

        banner("4. CLEANUP")
        print(f"cleared {await engine.clear()} entries - 100% local, zero cloud")


if __name__ == "__main__":
    asyncio.run(main())

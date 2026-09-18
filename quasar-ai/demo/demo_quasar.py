"""QuasarAI end-to-end demo - run with the emulator up:

    uv run python demo/demo_quasar.py

Shows the async engine's story: miss -> hit -> stampede -> parallel bulk ->
invalidate. All against the local Azure Cosmos DB emulator, zero cloud.
"""

import asyncio
import time

from quasar_ai.config import get_settings
from quasar_ai.cosmos import CosmosResources
from quasar_ai.engine import AsyncCacheEngine
from quasar_ai.generators import MockLLM


def banner(title: str) -> None:
    print(f"\n{'=' * 62}\n{title}\n{'=' * 62}")


async def main() -> None:
    settings = get_settings()
    mock = MockLLM(settings.simulated_latency_seconds)

    async with CosmosResources(settings) as resources:
        engine = AsyncCacheEngine(resources.intelligent, settings.default_ttl)

        banner("1. MISS then HIT")
        miss = await engine.get_or_generate("demo:quantum", mock.generate_for_key)
        hit = await engine.get_or_generate("demo:quantum", mock.generate_for_key)
        print(f"miss: {miss.latency_ms:8.2f} ms  ({miss.source})")
        print(f"hit : {hit.latency_ms:8.2f} ms  ({hit.source})")
        print(f"-> {miss.latency_ms / max(hit.latency_ms, 0.01):.0f}x faster on hit")

        banner("2. STAMPEDE - 20 concurrent requests, one key")
        gen_calls = {"n": 0}

        async def counting_gen(key: str) -> dict:
            gen_calls["n"] += 1
            return await mock.generate_for_key(key)

        started = time.perf_counter()
        results = await asyncio.gather(
            *(engine.get_or_generate("demo:stampede", counting_gen) for _ in range(20))
        )
        wall = time.perf_counter() - started
        print(f"20 requests in {wall * 1000:8.2f} ms | generations: {gen_calls['n']} (must be 1)")
        print(f"statuses: {results[0].status} + {sum(1 for r in results if r.status == 'hit')} hits")

        banner("3. PARALLEL BULK - 12 distinct keys")
        started = time.perf_counter()
        bulk = await engine.bulk_get_or_generate(
            [(f"demo:bulk:{i}", 300) for i in range(12)], mock.generate_for_key
        )
        wall = time.perf_counter() - started
        print(f"12 misses in {wall * 1000:8.2f} ms | avg {sum(r.latency_ms for r in bulk) / 12:.2f} ms")

        banner("4. INVALIDATE by pattern")
        deleted = await engine.invalidate("demo:")
        print(f"deleted {deleted} demo entries")

        banner("DONE - 100% local, zero cloud")


if __name__ == "__main__":
    asyncio.run(main())

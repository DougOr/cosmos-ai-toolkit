"""Diagnostic: what are the errors OrbitBench counts under concurrent load?"""

import asyncio
import collections

from azure.cosmos import exceptions

from orbitbench.backends.cosmos_backend import CosmosBackend
from orbitbench.config import get_settings
from orbitbench.workloads import build_value


async def main() -> None:
    backend = await CosmosBackend.create(get_settings())
    reasons = collections.Counter()
    total = 0
    try:
        await backend.clear()
        keys = [f"key-{i}" for i in range(500)]
        for i, key in enumerate(keys):
            await backend.set(key, build_value(512, i))

        async def worker(seed: int) -> None:
            nonlocal total
            for i in range(250):
                total += 1
                try:
                    await backend.get(keys[(seed * 31 + i) % len(keys)])
                except exceptions.CosmosHttpResponseError as exc:
                    reasons[(exc.status_code, str(exc.message)[:70])] += 1
                except Exception as exc:  # noqa: BLE001
                    reasons[(type(exc).__name__, str(exc)[:70])] += 1

        await asyncio.gather(*(worker(w) for w in range(8)))
    finally:
        await backend.close()

    print(f"error breakdown over {total} concurrent reads (8 workers):")
    if not reasons:
        print("  (no errors)")
    for reason, count in reasons.items():
        print(f"  {count:4d} x {reason}")


if __name__ == "__main__":
    asyncio.run(main())

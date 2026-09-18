"""The stampede proof - 20 concurrent GETs against a running QuasarAI server.

Start the server first:   uv run quasar-ai serve
Then in another terminal: uv run python demo/stampede_hit.py

Expected: exactly 1 "miss" (one generation) + 19 "hit" responses, because
the engine serializes cold-key misses behind a per-key asyncio lock.
"""

import asyncio
import sys
import time

import httpx

BASE_URL = "http://127.0.0.1:8001"
CONCURRENCY = 20


async def main() -> int:
    # time-stamped key: guaranteed cold, so the burst is a true miss storm
    key = f"demo:stampede:{time.strftime('%H%M%S')}"
    url = f"{BASE_URL}/cache/{key}"

    async with httpx.AsyncClient(timeout=30) as client:
        started = time.perf_counter()
        responses = await asyncio.gather(
            *(client.get(url) for _ in range(CONCURRENCY))
        )
        wall_ms = (time.perf_counter() - started) * 1000

    statuses = [response.json()["status"] for response in responses]
    misses = statuses.count("miss")
    hits = statuses.count("hit")

    print(f"{CONCURRENCY} concurrent requests in {wall_ms:.0f} ms")
    print(f"statuses: {misses} miss + {hits} hit")
    if misses == 1:
        print("generations: 1 (must be 1) - stampede protection confirmed")
        return 0
    print(f"UNEXPECTED: {misses} generations - lock failed or key was warm")
    return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

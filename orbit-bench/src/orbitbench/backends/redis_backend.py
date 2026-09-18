"""Redis backend - optional extra (`uv sync --extra redis`).

Import-guarded: the benchmark must run without redis installed as long as
you don't select the `redis` backend. Stored values are JSON-serialized
dicts (the protocol deals in dicts, not bytes).
"""

import json
import time

from orbitbench.backends.base import CacheBackend

PREFIX = "orbit:"


class RedisBackend(CacheBackend):
    name = "redis"

    def __init__(self, url: str) -> None:
        try:
            import redis.asyncio as aioredis  # noqa: PLC0415 - optional extra
        except ImportError as exc:  # pragma: no cover
            raise ValueError(
                "redis backend requires the extra: uv sync --extra redis"
            ) from exc
        self._redis = aioredis.from_url(url, decode_responses=True)

    def _k(self, key: str) -> str:
        return f"{PREFIX}{key}"

    async def get(self, key: str) -> dict | None:
        raw = await self._redis.get(self._k(key))
        if raw is None:
            return None
        return json.loads(raw)

    async def set(self, key: str, value: dict, ttl_seconds: int | None = None) -> None:
        raw = json.dumps(value)
        if ttl_seconds and ttl_seconds > 0:
            await self._redis.set(self._k(key), raw, ex=int(ttl_seconds))
        else:
            await self._redis.set(self._k(key), raw)

    async def delete(self, key: str) -> bool:
        return await self._redis.delete(self._k(key)) > 0

    async def clear(self) -> int:
        keys = [k async for k in self._redis.scan_iter(match=f"{PREFIX}*")]
        if not keys:
            return 0
        return await self._redis.delete(*keys)

    async def health(self) -> dict:
        try:
            started = time.perf_counter()
            await self._redis.ping()
            return {
                "backend": "redis",
                "status": "healthy",
                "ping_ms": round((time.perf_counter() - started) * 1000, 2),
            }
        except Exception as exc:  # noqa: BLE001
            return {"backend": "redis", "status": "degraded", "error": str(exc)}

    async def close(self) -> None:
        await self._redis.aclose()

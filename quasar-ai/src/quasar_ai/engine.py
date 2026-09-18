"""The async cache engine: stampede protection, upserts, TTL, invalidation.

Lessons from the v1 harness baked in:
- azure.cosmos.aio everywhere (v1 blocked the event loop with the sync SDK)
- per-key asyncio locks (v1 had cache-stampede on misses)
- upsert instead of create (v1 raised 409 on concurrent misses)
- timezone-aware timestamps (v1 mixed naive/aware datetimes)
- parameterized CONTAINS queries (v1 interpolated user input into SQL)
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

from azure.cosmos import exceptions
from azure.cosmos.aio import ContainerProxy

from quasar_ai.keys import doc_id

Generator = Callable[[str], Awaitable[dict]]

# TTL value stored on the document: -1 = never expires (Cosmos DB semantics)
NEVER_EXPIRE = -1

# Static partition key value (kept from v1 for comparability - ADR-004)
PARTITION_VALUE = "primary"


class CacheResult:
    __slots__ = ("status", "key", "payload", "source", "latency_ms", "ttl_remaining")

    def __init__(
        self,
        status: str,
        key: str,
        payload: dict,
        source: str,
        latency_ms: float,
        ttl_remaining: float | None = None,
    ) -> None:
        self.status = status
        self.key = key
        self.payload = payload
        self.source = source
        self.latency_ms = latency_ms
        self.ttl_remaining = ttl_remaining

    def as_dict(self) -> dict:
        return {
            "status": self.status,
            "cache_key": self.key,
            "payload": self.payload,
            "source": self.source,
            "latency_ms": self.latency_ms,
            "ttl_remaining": self.ttl_remaining,
        }


def ttl_remaining(created_at: str, ttl_value: int | None) -> float | None:
    """Seconds of TTL left for a document, or None if it does not expire.

    Timezone-aware end to end (v1 subtracted naive from aware datetimes and
    papered over the crash with a broad except).
    """
    if ttl_value is None or ttl_value <= 0:
        return None
    created = datetime.fromisoformat(created_at)
    elapsed = (datetime.now(timezone.utc) - created).total_seconds()
    remaining = ttl_value - max(0.0, elapsed)
    return round(remaining, 2) if remaining > 0 else None


class AsyncCacheEngine:
    """Get-or-generate cache over a Cosmos DB container (async SDK only)."""

    def __init__(self, container: ContainerProxy, default_ttl: int) -> None:
        self._container = container
        self._partition = PARTITION_VALUE
        self._default_ttl = default_ttl
        self._key_locks: dict[str, asyncio.Lock] = {}
        self._registry_lock = asyncio.Lock()

    async def _lock_for(self, key: str) -> asyncio.Lock:
        async with self._registry_lock:
            lock = self._key_locks.get(key)
            if lock is None:
                lock = asyncio.Lock()
                self._key_locks[key] = lock
            return lock

    async def get_or_generate(
        self, key: str, generator: Generator, ttl_seconds: int | None = None
    ) -> CacheResult:
        """Return the cached payload, or generate once, cache it, and return it.

        ttl_seconds=None means "use the container default"; a value <= 0 means
        never expire. Per-key locking means N concurrent misses produce exactly
        one generation call (single-process scope; see docs/DECISIONS.md).
        """
        started = time.perf_counter()
        id_ = doc_id(key)

        async with await self._lock_for(key):
            try:
                doc = await self._container.read_item(item=id_, partition_key=self._partition)
                return CacheResult(
                    status="hit",
                    key=key,
                    payload=doc["payload"],
                    source="cache",
                    latency_ms=round((time.perf_counter() - started) * 1000, 2),
                    ttl_remaining=ttl_remaining(doc["created_at"], doc.get("ttl_value")),
                )
            except exceptions.CosmosResourceNotFoundError:
                pass

            effective = self._default_ttl if ttl_seconds is None else ttl_seconds
            payload = await generator(key)
            now = datetime.now(timezone.utc).isoformat()
            document = {
                "id": id_,
                "pk": self._partition,
                "cache_key": key,
                "payload": payload,
                "created_at": now,
                "ttl_value": effective,
                # Cosmos DB: positive ttl = expires after N seconds, -1 = never
                "ttl": int(effective) if effective and effective > 0 else NEVER_EXPIRE,
            }
            # upsert: a racing writer overwrites instead of raising 409
            await self._container.upsert_item(body=document)

            return CacheResult(
                status="miss",
                key=key,
                payload=payload,
                source="generated",
                latency_ms=round((time.perf_counter() - started) * 1000, 2),
                ttl_remaining=float(effective) if effective and effective > 0 else None,
            )

    async def bulk_get_or_generate(
        self, items: list[tuple[str, int | None]], generator: Generator
    ) -> list[CacheResult]:
        """Concurrent get-or-generate. Genuinely parallel (v1 looped serially)."""
        return list(
            await asyncio.gather(
                *(self.get_or_generate(key, generator, ttl) for key, ttl in items)
            )
        )

    async def invalidate(self, pattern: str | None = None) -> int:
        """Delete entries whose cache_key contains the pattern (case-insensitive).

        Parameterized CONTAINS - no string interpolation reaches the query text.
        """
        if pattern:
            query = "SELECT c.id, c.cache_key FROM c WHERE CONTAINS(c.cache_key, @pat, true)"
            parameters: list[dict[str, Any]] | None = [{"name": "@pat", "value": pattern}]
        else:
            query = "SELECT c.id FROM c"
            parameters = None

        ids = [
            item["id"]
            async for item in self._container.query_items(
                query=query, parameters=parameters, partition_key=self._partition
            )
        ]

        deleted = 0
        for id_ in ids:
            try:
                await self._container.delete_item(item=id_, partition_key=self._partition)
                deleted += 1
            except exceptions.CosmosResourceNotFoundError:
                pass  # expired between query and delete - fine
        return deleted

    async def count(self) -> int:
        return len(
            [item async for item in self._container.query_items(
                query="SELECT VALUE c.id FROM c", partition_key=self._partition
            )]
        )


class GenericStore:
    """Arbitrary JSON documents with TTL, on a second container."""

    def __init__(self, container: ContainerProxy, default_ttl: int) -> None:
        self._container = container
        self._partition = PARTITION_VALUE
        self._default_ttl = default_ttl

    async def set(self, key: str, data: dict, ttl_seconds: int | None = None) -> float | None:
        effective = self._default_ttl if ttl_seconds is None else ttl_seconds
        document = {
            "id": doc_id(key),
            "pk": self._partition,
            "key": key,
            "data": data,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "ttl_value": effective,
            "ttl": int(effective) if effective and effective > 0 else NEVER_EXPIRE,
        }
        await self._container.upsert_item(body=document)
        return float(effective) if effective and effective > 0 else None

    async def get(self, key: str) -> tuple[dict, float | None] | None:
        try:
            doc = await self._container.read_item(item=doc_id(key), partition_key=self._partition)
        except exceptions.CosmosResourceNotFoundError:
            return None
        return doc["data"], ttl_remaining(doc["created_at"], doc.get("ttl_value"))

    async def delete(self, key: str) -> bool:
        try:
            await self._container.delete_item(item=doc_id(key), partition_key=self._partition)
            return True
        except exceptions.CosmosResourceNotFoundError:
            return False

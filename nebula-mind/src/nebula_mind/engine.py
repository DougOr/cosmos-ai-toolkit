"""The semantic cache engine.

Flow (get_or_generate):
    prompt+params -> request_hash -> point read
      hit  -> return cached answer (source=cache, similarity=1.0)
      miss -> LLM generate -> embed prompt -> upsert entry -> return

Flow (search):
    query -> embed -> cosine against recent entries (app-side; the emulator
    has no native vector search) -> top-k with scores.
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Any

from azure.cosmos import exceptions
from azure.cosmos.aio import ContainerProxy

from nebula_mind.embeddings import cosine
from nebula_mind.keys import request_hash
from nebula_mind.providers.base import EmbeddingProvider, LLMProvider

NEVER_EXPIRE = -1


def ttl_remaining(created_at: str, ttl_value: int | None) -> float | None:
    if ttl_value is None or ttl_value <= 0:
        return None
    created = datetime.fromisoformat(created_at)
    elapsed = (datetime.now(timezone.utc) - created).total_seconds()
    remaining = ttl_value - max(0.0, elapsed)
    return round(remaining, 2) if remaining > 0 else None


class SemanticCacheEngine:
    def __init__(
        self,
        container: ContainerProxy,
        llm: LLMProvider,
        embedder: EmbeddingProvider,
        default_ttl: int = 3600,
        similarity_threshold: float = 0.6,
    ) -> None:
        self._container = container
        self._llm = llm
        self._embedder = embedder
        self._default_ttl = default_ttl
        self._threshold = similarity_threshold
        self._partition = "primary"
        self._locks: dict[str, asyncio.Lock] = {}
        self._registry_lock = asyncio.Lock()

    async def _lock_for(self, key: str) -> asyncio.Lock:
        async with self._registry_lock:
            if key not in self._locks:
                self._locks[key] = asyncio.Lock()
            return self._locks[key]

    async def get_or_generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        ttl_seconds: int | None = None,
    ) -> dict[str, Any]:
        started = time.perf_counter()
        key = request_hash(prompt, system_prompt, self._llm.name, temperature, max_tokens)

        async with await self._lock_for(key):
            try:
                doc = await self._container.read_item(item=key, partition_key=self._partition)
                return {
                    "status": "exact_hit",
                    "entry_id": key,
                    "prompt_preview": doc.get("prompt_preview", ""),
                    "answer": doc["answer"],
                    "source": "cache",
                    "similarity": 1.0,
                    "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                    "ttl_remaining": ttl_remaining(doc["created_at"], doc.get("ttl_value")),
                }
            except exceptions.CosmosResourceNotFoundError:
                pass

            effective = self._default_ttl if ttl_seconds is None else ttl_seconds
            result = await self._llm.generate(prompt, system_prompt, temperature, max_tokens)
            embedding = await self._embedder.embed(prompt)
            now = datetime.now(timezone.utc).isoformat()

            document = {
                "id": key,
                "pk": self._partition,
                "prompt_preview": prompt[:200],
                "system_prompt": system_prompt,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "model": result.model,
                "answer": {
                    "content": result.content,
                    "model": result.model,
                    "finish_reason": result.finish_reason,
                    "usage": result.usage,
                    "latency_ms": result.latency_ms,
                },
                "embedding": embedding,
                "embedding_provider": self._embedder.name,
                "embedding_semantic": self._embedder.semantic,
                "created_at": now,
                "ttl_value": effective,
                "ttl": int(effective) if effective and effective > 0 else NEVER_EXPIRE,
            }
            await self._container.upsert_item(body=document)

            return {
                "status": "generated",
                "entry_id": key,
                "prompt_preview": prompt[:200],
                "answer": document["answer"],
                "source": self._llm.name,
                "similarity": None,
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                "ttl_remaining": float(effective) if effective and effective > 0 else None,
            }

    async def search(self, query: str, top_k: int = 5) -> dict[str, Any]:
        """Similarity search over recent entries. App-side cosine by necessity
        (emulator has no vector search) - honest and documented."""
        started = time.perf_counter()
        query_vector = await self._embedder.embed(query)

        candidates = [
            doc
            async for doc in self._container.query_items(
                query="SELECT TOP 100 * FROM c ORDER BY c.created_at DESC",
                partition_key=self._partition,
            )
        ]

        scored: list[dict[str, Any]] = []
        for doc in candidates:
            vector = doc.get("embedding")
            if not vector:
                continue
            score = cosine(query_vector, vector)
            scored.append(
                {
                    "entry_id": doc["id"],
                    "prompt_preview": doc.get("prompt_preview", ""),
                    "content_preview": doc["answer"]["content"][:120],
                    "score": score,
                    "above_threshold": score >= self._threshold,
                }
            )

        scored.sort(key=lambda hit: hit["score"], reverse=True)
        return {
            "query": query,
            "embedding_provider": self._embedder.name,
            "embedding_semantic": self._embedder.semantic,
            "threshold": self._threshold,
            "scanned": len(candidates),
            "hits": scored[:top_k],
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        }

    async def clear(self) -> int:
        ids = [
            item["id"]
            async for item in self._container.query_items(
                query="SELECT c.id FROM c", partition_key=self._partition
            )
        ]
        deleted = 0
        for id_ in ids:
            try:
                await self._container.delete_item(item=id_, partition_key=self._partition)
                deleted += 1
            except exceptions.CosmosResourceNotFoundError:
                pass
        return deleted

    async def count(self) -> int:
        return len(
            [
                item
                async for item in self._container.query_items(
                    query="SELECT VALUE c.id FROM c", partition_key=self._partition
                )
            ]
        )

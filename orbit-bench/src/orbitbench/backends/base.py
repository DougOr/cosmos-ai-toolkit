"""The protocol every cache backend orbits around.

Async only. One dict in, one dict out, ttl optional, no backend-specific
concepts leak above this line - that is what makes benchmarks comparable.
"""

from abc import ABC, abstractmethod


class CacheBackend(ABC):
    name: str

    @abstractmethod
    async def get(self, key: str) -> dict | None:
        """Return the cached value dict, or None on miss/expiry."""

    @abstractmethod
    async def set(self, key: str, value: dict, ttl_seconds: int | None = None) -> None:
        """Store value; ttl_seconds <= 0 or None = never expires."""

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Remove one key. True if it existed."""

    @abstractmethod
    async def clear(self) -> int:
        """Remove everything. Returns the number of entries removed."""

    @abstractmethod
    async def health(self) -> dict:
        """Liveness + identity info (never raises; report degraded instead)."""

    async def close(self) -> None:
        """Release connections. Optional."""
        return None

"""In-process memory backend - the control group of every benchmark.

Same protocol, zero I/O: the delta between `memory` and any other backend in
the same table IS the storage cost, measured instead of guessed.
"""

import time

from orbitbench.backends.base import CacheBackend


class MemoryBackend(CacheBackend):
    name = "memory"

    def __init__(self) -> None:
        # key -> (expires_at_monotonic | None, value)
        self._data: dict[str, tuple[float | None, dict]] = {}

    async def get(self, key: str) -> dict | None:
        entry = self._data.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if expires_at is not None and time.monotonic() > expires_at:
            del self._data[key]
            return None
        return value

    async def set(self, key: str, value: dict, ttl_seconds: int | None = None) -> None:
        expires_at = time.monotonic() + ttl_seconds if ttl_seconds and ttl_seconds > 0 else None
        self._data[key] = (expires_at, value)

    async def delete(self, key: str) -> bool:
        return self._data.pop(key, None) is not None

    async def clear(self) -> int:
        count = len(self._data)
        self._data.clear()
        return count

    async def health(self) -> dict:
        return {"backend": "memory", "entries": len(self._data), "status": "healthy"}

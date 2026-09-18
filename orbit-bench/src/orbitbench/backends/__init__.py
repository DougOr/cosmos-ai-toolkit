"""Backend registry - the single place that maps names to implementations."""

import importlib.util

from orbitbench.backends.base import CacheBackend
from orbitbench.backends.cosmos_backend import CosmosBackend
from orbitbench.backends.memory import MemoryBackend
from orbitbench.config import Settings

AVAILABLE_BACKENDS = ["memory", "cosmos", "redis"]


def redis_installed() -> bool:
    return importlib.util.find_spec("redis") is not None


def backend_available(name: str) -> bool:
    if name in ("memory", "cosmos"):
        return True
    if name == "redis":
        return redis_installed()
    return False


async def create_backend(
    name: str, settings: Settings, purge: bool = False
) -> CacheBackend:
    """Build a fresh backend instance. `purge` clears persistent backends
    first so runs are isolated (recommended for comparable numbers)."""
    if name == "memory":
        return MemoryBackend()

    if name == "cosmos":
        backend = await CosmosBackend.create(settings)
        if purge:
            await backend.clear()
        return backend

    if name == "redis":
        if not redis_installed():
            raise ValueError("redis backend requires the extra: uv sync --extra redis")
        from orbitbench.backends.redis_backend import RedisBackend

        backend = RedisBackend(settings.redis_url)
        if purge:
            await backend.clear()
        return backend

    raise ValueError(
        f"Unknown backend '{name}'. Available: {', '.join(AVAILABLE_BACKENDS)}"
    )


__all__ = [
    "CacheBackend",
    "MemoryBackend",
    "CosmosBackend",
    "AVAILABLE_BACKENDS",
    "backend_available",
    "create_backend",
    "redis_installed",
]

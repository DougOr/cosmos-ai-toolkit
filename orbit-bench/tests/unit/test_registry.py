"""Backend registry: availability rules and unknown-name errors."""

import pytest

from orbitbench.backends import AVAILABLE_BACKENDS, backend_available, create_backend
from orbitbench.config import Settings


def test_memory_and_cosmos_always_available():
    assert backend_available("memory")
    assert backend_available("cosmos")


def test_redis_depends_on_extra():
    try:
        import redis  # noqa: F401

        assert backend_available("redis")
    except ImportError:
        assert not backend_available("redis")


async def test_create_memory_backend():
    settings = Settings(_env_file=None)
    backend = await create_backend("memory", settings)
    assert backend.name == "memory"
    await backend.close()


async def test_unknown_backend_raises():
    settings = Settings(_env_file=None)
    with pytest.raises(ValueError, match="Unknown backend"):
        await create_backend("oracle", settings)


def test_available_list_is_stable():
    assert AVAILABLE_BACKENDS == ["memory", "cosmos", "redis"]

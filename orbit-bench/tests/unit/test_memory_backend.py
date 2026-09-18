"""Memory backend: protocol behaviour + TTL expiry."""

import asyncio

from orbitbench.backends.memory import MemoryBackend


async def test_set_get_delete_roundtrip():
    backend = MemoryBackend()
    assert await backend.get("missing") is None

    await backend.set("k", {"v": 1})
    assert await backend.get("k") == {"v": 1}

    assert await backend.delete("k") is True
    assert await backend.delete("k") is False
    assert await backend.get("k") is None


async def test_ttl_expiry():
    backend = MemoryBackend()
    await backend.set("short", {"v": 1}, ttl_seconds=0.05)
    assert await backend.get("short") == {"v": 1}
    await asyncio.sleep(0.08)
    assert await backend.get("short") is None


async def test_no_ttl_never_expires():
    backend = MemoryBackend()
    await backend.set("forever", {"v": 1}, ttl_seconds=-1)
    await asyncio.sleep(0.02)
    assert await backend.get("forever") == {"v": 1}


async def test_clear_counts():
    backend = MemoryBackend()
    for i in range(5):
        await backend.set(f"k{i}", {"i": i})
    assert await backend.clear() == 5
    assert await backend.clear() == 0

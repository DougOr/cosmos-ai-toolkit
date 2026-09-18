"""Engine behaviour on a fake container: stampede, races, TTL, invalidation."""

import asyncio
import time
from datetime import datetime, timedelta, timezone

from quasar_ai.engine import AsyncCacheEngine, ttl_remaining
from quasar_ai.keys import doc_id

from .fakes import CountingGenerator, FakeContainer


def make_engine(default_ttl: int = 120) -> tuple[AsyncCacheEngine, FakeContainer]:
    container = FakeContainer()
    return AsyncCacheEngine(container, default_ttl=default_ttl), container


async def test_miss_then_hit():
    engine, _ = make_engine()
    gen = CountingGenerator()

    miss = await engine.get_or_generate("k", gen)
    assert miss.status == "miss"
    assert miss.source == "generated"

    hit = await engine.get_or_generate("k", gen)
    assert hit.status == "hit"
    assert hit.source == "cache"
    assert hit.payload == miss.payload
    assert gen.calls == 1  # generated exactly once
    assert hit.latency_ms <= miss.latency_ms


async def test_stampede_single_generation():
    engine, _ = make_engine()
    gen = CountingGenerator(delay=0.05)

    results = await asyncio.gather(*(engine.get_or_generate("hot", gen) for _ in range(10)))

    assert gen.calls == 1, "N concurrent misses must generate exactly once"
    statuses = [r.status for r in results]
    assert statuses.count("miss") == 1
    assert statuses.count("hit") == 9
    assert len({r.payload["value"] for r in results}) == 1


async def test_bulk_is_concurrent_and_correct():
    engine, _ = make_engine()
    gen = CountingGenerator(delay=0.05)
    items = [(f"k{i}", None) for i in range(20)]

    started = time.perf_counter()
    results = await engine.bulk_get_or_generate(items, gen)
    wall = time.perf_counter() - started

    assert gen.calls == 20
    assert {r.status for r in results} == {"miss"}
    # serial execution would need >= 1.0s; concurrency must beat that clearly
    assert wall < 1.0


async def test_upsert_race_never_conflicts():
    engine, container = make_engine()
    gen = CountingGenerator()

    # Simulate the v1 failure: two writers create the same doc concurrently.
    await asyncio.gather(
        *(engine.get_or_generate("race", gen) for _ in range(2)),
    )
    assert container.docs[doc_id("race")]["cache_key"] == "race"


async def test_ttl_remaining_math():
    engine, container = make_engine(default_ttl=120)
    await engine.get_or_generate("t", CountingGenerator())
    doc = container.docs[doc_id("t")]
    assert doc["ttl"] == 120

    remaining = ttl_remaining(doc["created_at"], 120)
    assert remaining is not None
    assert 110 <= remaining <= 120


async def test_expired_and_indefinite_have_no_remaining():
    past = (datetime.now(timezone.utc) - timedelta(seconds=200)).isoformat()
    assert ttl_remaining(past, 120) is None  # already expired
    assert ttl_remaining(datetime.now(timezone.utc).isoformat(), -1) is None  # indefinite


async def test_default_ttl_applied_when_unspecified():
    engine, container = make_engine(default_ttl=60)
    await engine.get_or_generate("d", CountingGenerator())
    doc = container.docs[doc_id("d")]
    assert doc["ttl_value"] == 60
    assert doc["ttl"] == 60


async def test_indefinite_ttl_never_expires():
    engine, container = make_engine(default_ttl=60)
    await engine.get_or_generate("forever", CountingGenerator(), ttl_seconds=-1)
    doc = container.docs[doc_id("forever")]
    assert doc["ttl"] == -1  # v1 wrongly stored the default here
    assert ttl_remaining(doc["created_at"], doc["ttl_value"]) is None


async def test_invalidate_pattern_parameterized():
    engine, _ = make_engine()
    for key in ("user:1", "user:2", "session:1"):
        await engine.get_or_generate(key, CountingGenerator())

    deleted = await engine.invalidate("user")
    assert deleted == 2

    everything = await engine.invalidate(None)
    assert everything == 1


async def test_ttl_change_applies_on_next_miss():
    engine, container = make_engine()
    await engine.get_or_generate("x", CountingGenerator(), ttl_seconds=60)
    assert container.docs[doc_id("x")]["ttl_value"] == 60

    # a warm key is a hit - it must NOT rewrite the TTL
    hit = await engine.get_or_generate("x", CountingGenerator(), ttl_seconds=3600)
    assert hit.status == "hit"
    assert container.docs[doc_id("x")]["ttl_value"] == 60

    # only a fresh miss (after invalidation) writes the new TTL
    await engine.invalidate("x")
    await engine.get_or_generate("x", CountingGenerator(), ttl_seconds=3600)
    assert container.docs[doc_id("x")]["ttl_value"] == 3600

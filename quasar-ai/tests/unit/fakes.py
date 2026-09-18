"""In-memory fake of the async Cosmos container surface used by the engine."""

from azure.cosmos import exceptions


class FakeContainer:
    """Mirrors the subset of azure.cosmos.aio.ContainerProxy the engine calls."""

    def __init__(self) -> None:
        self.docs: dict[str, dict] = {}

    async def read_item(self, item: str, partition_key: str) -> dict:
        if item not in self.docs:
            raise exceptions.CosmosResourceNotFoundError(404, "Not Found")
        return self.docs[item]

    async def upsert_item(self, body: dict) -> dict:
        self.docs[body["id"]] = body
        return body

    async def delete_item(self, item: str, partition_key: str) -> None:
        if item not in self.docs:
            raise exceptions.CosmosResourceNotFoundError(404, "Not Found")
        del self.docs[item]

    def query_items(self, query: str, parameters=None, partition_key=None):
        async def _iter():
            pattern = None
            for param in parameters or []:
                if param.get("name") == "@pat":
                    pattern = str(param["value"]).lower()
            for doc in list(self.docs.values()):
                if pattern is not None:
                    haystack = (doc.get("cache_key") or doc.get("key") or "").lower()
                    if pattern not in haystack:
                        continue
                yield doc

        return _iter()


class CountingGenerator:
    """Async (key) -> payload generator that counts calls, with optional delay."""

    def __init__(self, delay: float = 0.0) -> None:
        self.calls = 0
        self.keys: list[str] = []
        self.delay = delay

    async def __call__(self, key: str) -> dict:
        self.calls += 1
        self.keys.append(key)
        if self.delay:
            import asyncio

            await asyncio.sleep(self.delay)
        return {"value": key}

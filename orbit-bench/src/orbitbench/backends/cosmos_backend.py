"""Cosmos DB backend - the async SDK patterns from the toolkit, benched.

Same rules as QuasarAI/NebulaMind: azure.cosmos.aio only, sha256 ids,
upserts, timezone-aware timestamps, TLS-guarded emulator connection.
"""

import hashlib
from datetime import datetime, timezone

from azure.cosmos import PartitionKey, exceptions
from azure.cosmos.aio import ContainerProxy, CosmosClient

from orbitbench.backends.base import CacheBackend
from orbitbench.config import Settings

NEVER_EXPIRE = -1
PARTITION_VALUE = "bench"


def _doc_id(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


class CosmosBackend(CacheBackend):
    name = "cosmos"

    def __init__(self, client: CosmosClient, container: ContainerProxy, endpoint: str) -> None:
        self._client = client
        self._container = container
        self._endpoint = endpoint

    @classmethod
    async def create(cls, settings: Settings, default_ttl: int | None = None) -> "CosmosBackend":
        settings.tls_guard()
        effective_ttl = default_ttl if default_ttl is not None else settings.default_ttl

        client = CosmosClient(
            settings.cosmos_endpoint,
            credential=settings.cosmos_key,
            connection_verify=settings.verify_emulator_tls,
        )
        try:
            try:
                database = client.get_database_client(settings.database_name)
                await database.read()
            except exceptions.CosmosResourceNotFoundError:
                database = await client.create_database(settings.database_name)

            container = database.get_container_client(settings.bench_container)
            try:
                await container.read()
            except exceptions.CosmosResourceNotFoundError:
                container = await database.create_container(
                    id=settings.bench_container,
                    partition_key=PartitionKey(path="/pk"),
                    default_ttl=effective_ttl,
                )
        except BaseException:
            # never leak the aiohttp session when bootstrap fails (e.g. emulator down)
            await client.close()
            raise

        return cls(client, container, settings.cosmos_endpoint)

    async def get(self, key: str) -> dict | None:
        try:
            doc = await self._container.read_item(item=_doc_id(key), partition_key=PARTITION_VALUE)
        except exceptions.CosmosResourceNotFoundError:
            return None
        return doc["value"]

    async def set(self, key: str, value: dict, ttl_seconds: int | None = None) -> None:
        # bench container carries no container-level default; None = never expire
        document = {
            "id": _doc_id(key),
            "pk": PARTITION_VALUE,
            "key": key,
            "value": value,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "ttl": int(ttl_seconds) if ttl_seconds and ttl_seconds > 0 else NEVER_EXPIRE,
        }
        await self._container.upsert_item(body=document)

    async def delete(self, key: str) -> bool:
        try:
            await self._container.delete_item(
                item=_doc_id(key), partition_key=PARTITION_VALUE
            )
            return True
        except exceptions.CosmosResourceNotFoundError:
            return False

    async def clear(self) -> int:
        ids = [
            item["id"]
            async for item in self._container.query_items(
                query="SELECT c.id FROM c", partition_key=PARTITION_VALUE
            )
        ]
        deleted = 0
        for id_ in ids:
            try:
                await self._container.delete_item(item=id_, partition_key=PARTITION_VALUE)
                deleted += 1
            except exceptions.CosmosResourceNotFoundError:
                pass
        return deleted

    async def health(self) -> dict:
        try:
            entries = len(
                [
                    item
                    async for item in self._container.query_items(
                        query="SELECT VALUE c.id FROM c", partition_key=PARTITION_VALUE
                    )
                ]
            )
            return {
                "backend": "cosmos",
                "endpoint": self._endpoint,
                "entries": entries,
                "status": "healthy",
            }
        except Exception as exc:  # noqa: BLE001 - health must never raise
            return {"backend": "cosmos", "endpoint": self._endpoint, "status": "degraded",
                    "error": str(exc)}

    async def close(self) -> None:
        await self._client.close()

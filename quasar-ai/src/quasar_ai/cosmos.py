"""Async Cosmos DB resource bootstrap (client, database, containers)."""

from types import TracebackType

from azure.cosmos import PartitionKey, exceptions
from azure.cosmos.aio import ContainerProxy, CosmosClient, DatabaseProxy

from quasar_ai.config import Settings

PARTITION_PATH = "/pk"
PARTITION_VALUE = "primary"


class CosmosResources:
    """Owns the async client lifecycle; use as an async context manager."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self.client: CosmosClient | None = None
        self.database: DatabaseProxy | None = None
        self.intelligent: ContainerProxy | None = None
        self.generic: ContainerProxy | None = None

    async def __aenter__(self) -> "CosmosResources":
        s = self._settings
        s.tls_guard()

        # connection_verify=False is required for the emulator's self-signed
        # certificate; the tls_guard above makes that safe on localhost only.
        self.client = CosmosClient(
            s.cosmos_endpoint,
            credential=s.cosmos_key,
            connection_verify=s.verify_emulator_tls,
        )

        try:
            self.database = self.client.get_database_client(s.database_name)
            await self.database.read()
        except exceptions.CosmosResourceNotFoundError:
            self.database = await self.client.create_database(s.database_name)

        self.intelligent = await self._get_or_create_container(
            s.intelligent_container, s.default_ttl
        )
        self.generic = await self._get_or_create_container(s.generic_container, s.default_ttl)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self.client is not None:
            await self.client.close()
            self.client = None

    async def _get_or_create_container(self, name: str, default_ttl: int) -> ContainerProxy:
        assert self.database is not None
        container = self.database.get_container_client(name)
        try:
            await container.read()
            return container
        except exceptions.CosmosResourceNotFoundError:
            return await self.database.create_container(
                id=name,
                partition_key=PartitionKey(path=PARTITION_PATH),
                default_ttl=default_ttl,
            )

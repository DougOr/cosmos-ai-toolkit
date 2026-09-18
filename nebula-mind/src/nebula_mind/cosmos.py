"""Async Cosmos DB bootstrap (same guarded pattern as QuasarAI)."""

from types import TracebackType

from azure.cosmos import PartitionKey, exceptions
from azure.cosmos.aio import ContainerProxy, CosmosClient, DatabaseProxy

from nebula_mind.config import Settings

PARTITION_PATH = "/pk"
PARTITION_VALUE = "primary"


class CosmosResources:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self.client: CosmosClient | None = None
        self.database: DatabaseProxy | None = None
        self.cache: ContainerProxy | None = None

    async def __aenter__(self) -> "CosmosResources":
        s = self._settings
        s.tls_guard()

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

        container = self.database.get_container_client(s.cache_container)
        try:
            await container.read()
            self.cache = container
        except exceptions.CosmosResourceNotFoundError:
            self.cache = await self.database.create_container(
                id=s.cache_container,
                partition_key=PartitionKey(path=PARTITION_PATH),
                default_ttl=s.default_ttl,
            )
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

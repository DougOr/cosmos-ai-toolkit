"""Typed configuration with an emulator TLS guard."""

from functools import lru_cache
from urllib.parse import urlparse

from pydantic_settings import BaseSettings, SettingsConfigDict

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}

# Well-known PUBLIC emulator key. Grants access to the LOCAL emulator only.
WELL_KNOWN_EMULATOR_KEY = (
    "C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw=="
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    cosmos_endpoint: str = "https://localhost:8081/"
    cosmos_key: str = WELL_KNOWN_EMULATOR_KEY
    database_name: str = "QuasarDB"
    intelligent_container: str = "quasar-intelligent"
    generic_container: str = "quasar-generic"

    default_ttl: int = 120
    simulated_latency_seconds: float = 0.3

    api_host: str = "127.0.0.1"
    api_port: int = 8001

    # False = skip TLS verification (required for the emulator's self-signed cert).
    verify_emulator_tls: bool = False

    @property
    def endpoint_host(self) -> str:
        return (urlparse(self.cosmos_endpoint).hostname or "").lower()

    @property
    def is_local_endpoint(self) -> bool:
        return self.endpoint_host in LOCAL_HOSTS

    def tls_guard(self) -> None:
        """Fail fast rather than silently sending an unverified request off-box."""
        if not self.verify_emulator_tls and not self.is_local_endpoint:
            raise ValueError(
                "Refusing to skip TLS verification for non-local endpoint "
                f"'{self.cosmos_endpoint}'. Point COSMOS_ENDPOINT at the local emulator, "
                "or set VERIFY_EMULATOR_TLS=true if you truly mean to verify a real cert."
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()

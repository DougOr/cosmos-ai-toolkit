"""Typed configuration with provider selection and the emulator TLS guard."""

from functools import lru_cache
from urllib.parse import urlparse

from pydantic_settings import BaseSettings, SettingsConfigDict

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}

WELL_KNOWN_EMULATOR_KEY = (
    "C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw=="
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Cosmos DB (emulator)
    cosmos_endpoint: str = "https://localhost:8081/"
    cosmos_key: str = WELL_KNOWN_EMULATOR_KEY
    database_name: str = "NebulaDB"
    cache_container: str = "nebula-cache"
    verify_emulator_tls: bool = False
    default_ttl: int = 3600

    # LLM provider
    llm_provider: str = "mock"  # mock | ollama | openai_compatible
    simulated_latency_seconds: float = 0.15

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    openai_compat_base_url: str = "https://open.bigmodel.cn/api/paas/v4/"
    openai_compat_api_key: str = ""
    openai_compat_model: str = "glm-4.7"

    # Embeddings
    embedding_provider: str = "hash"  # hash | ollama
    embedding_model: str = "nomic-embed-text"
    embedding_dim: int = 512
    similarity_threshold: float = 0.6

    # API
    api_host: str = "127.0.0.1"
    api_port: int = 8002

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

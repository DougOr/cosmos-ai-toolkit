"""Provider factory: one place wires settings into concrete providers."""

from nebula_mind.config import Settings
from nebula_mind.providers.base import EmbeddingProvider, LLMProvider
from nebula_mind.providers.mock import HashEmbeddingProvider, MockLLMProvider
from nebula_mind.providers.ollama import OllamaEmbeddingProvider, OllamaLLMProvider
from nebula_mind.providers.openai_compatible import (
    OpenAICompatibleEmbeddingProvider,
    OpenAICompatibleProvider,
)


def build_providers(settings: Settings) -> tuple[LLMProvider, EmbeddingProvider]:
    """Wire (LLM, embedder) from settings. Raises ValueError on bad combos."""
    llm: LLMProvider
    embedder: EmbeddingProvider

    if settings.llm_provider == "mock":
        llm = MockLLMProvider(settings.simulated_latency_seconds)
    elif settings.llm_provider == "ollama":
        llm = OllamaLLMProvider(settings.ollama_base_url, settings.ollama_model)
    elif settings.llm_provider == "openai_compatible":
        llm = OpenAICompatibleProvider(
            settings.openai_compat_base_url,
            settings.openai_compat_api_key,
            settings.openai_compat_model,
        )
    else:
        raise ValueError(
            f"Unknown LLM_PROVIDER '{settings.llm_provider}' "
            "(expected mock | ollama | openai_compatible)"
        )

    if settings.embedding_provider == "hash":
        embedder = HashEmbeddingProvider(settings.embedding_dim)
    elif settings.embedding_provider == "ollama":
        embedder = OllamaEmbeddingProvider(
            settings.ollama_base_url, settings.embedding_model
        )
    else:
        raise ValueError(
            f"Unknown EMBEDDING_PROVIDER '{settings.embedding_provider}' "
            "(expected hash | ollama)"
        )

    return llm, embedder


__all__ = [
    "build_providers",
    "LLMProvider",
    "EmbeddingProvider",
    "LLMResult",
    "MockLLMProvider",
    "HashEmbeddingProvider",
    "OllamaLLMProvider",
    "OllamaEmbeddingProvider",
    "OpenAICompatibleProvider",
    "OpenAICompatibleEmbeddingProvider",
]

"""Provider protocols: NebulaMind caches ANY LLM, generates with one of these."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class LLMResult:
    content: str
    model: str
    finish_reason: str = "stop"
    usage: dict = field(default_factory=dict)
    latency_ms: float = 0.0


class LLMProvider(ABC):
    """Async text generator (mock, Ollama, OpenAI-compatible, ...)."""

    name: str

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> LLMResult: ...

    async def aclose(self) -> None:  # optional cleanup
        return None


class EmbeddingProvider(ABC):
    """Async text -> vector. `semantic` flags whether vectors carry true
    semantics (documented and surfaced in API responses) or are lexical."""

    name: str
    semantic: bool

    @abstractmethod
    async def embed(self, text: str) -> list[float]: ...

    async def aclose(self) -> None:
        return None

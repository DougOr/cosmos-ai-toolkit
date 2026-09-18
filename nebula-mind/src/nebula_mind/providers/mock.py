"""Offline providers: deterministic mock LLM + lexical hash embeddings.

The default pair. They make the whole demo and test suite run with zero
network access - no emulator dependency for the providers themselves, no
API keys, no Ollama install.
"""

import asyncio
import hashlib
import time

from nebula_mind.embeddings import hash_embedding
from nebula_mind.providers.base import EmbeddingProvider, LLMResult, LLMProvider


class MockLLMProvider(LLMProvider):
    name = "mock"

    def __init__(self, latency_seconds: float = 0.15) -> None:
        self.latency_seconds = latency_seconds

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> LLMResult:
        started = time.perf_counter()
        if self.latency_seconds > 0:
            await asyncio.sleep(self.latency_seconds)

        seed = hashlib.sha256(f"{system_prompt or ''}|{prompt}|{temperature}".encode()).hexdigest()
        input_tokens = max(1, len(prompt.split()))
        output_tokens = min(max_tokens, 48)
        return LLMResult(
            content=f"[mock:{seed[:12]}] Simulated answer to: {prompt[:80]}",
            model="mock",
            usage={
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
            },
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
        )


class HashEmbeddingProvider(EmbeddingProvider):
    name = "hash-lexical"
    semantic = False  # lexical similarity, labeled honestly everywhere

    def __init__(self, dim: int = 512) -> None:
        self.dim = dim

    async def embed(self, text: str) -> list[float]:
        return hash_embedding(text, self.dim)

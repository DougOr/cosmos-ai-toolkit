"""Offline mock LLM used as the auto-generation source on cache misses.

Deterministic on purpose: the same prompt always produces the same "tokens",
so cache-hit demos and benchmarks are reproducible.
"""

import asyncio
import hashlib
import time
from datetime import datetime, timezone


class MockLLM:
    def __init__(self, latency_seconds: float = 0.3) -> None:
        self.latency_seconds = latency_seconds

    async def generate_for_key(self, key: str) -> dict:
        """Generator adapter matching the engine's `async (key) -> payload` hook."""
        return await self.generate(prompt=f"auto-generated for cache key: {key}")

    async def generate(self, prompt: str, system_prompt: str | None = None) -> dict:
        started = time.perf_counter()

        if self.latency_seconds > 0:
            await asyncio.sleep(self.latency_seconds)

        seed = hashlib.sha256(f"{system_prompt or ''}|{prompt}".encode("utf-8")).hexdigest()
        input_tokens = max(1, len(prompt.split()))

        return {
            "content": f"[mock-llm:{seed[:12]}] Simulated answer to: {prompt[:80]}",
            "model": "mock-llm",
            "finish_reason": "stop",
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": 32,
                "total_tokens": input_tokens + 32,
            },
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "generation_ms": round((time.perf_counter() - started) * 1000, 2),
        }

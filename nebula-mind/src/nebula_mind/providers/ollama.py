"""Ollama providers - true local LLM + true semantic embeddings, zero cloud."""

import time

import httpx

from nebula_mind.providers.base import EmbeddingProvider, LLMResult, LLMProvider


class OllamaLLMProvider(LLMProvider):
    name = "ollama"

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.2",
                 timeout: float = 60.0) -> None:
        self.model = model
        self._http = httpx.AsyncClient(base_url=base_url, timeout=timeout)

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> LLMResult:
        started = time.perf_counter()
        payload: dict = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        if system_prompt:
            payload["system"] = system_prompt

        response = await self._http.post("/api/generate", json=payload)
        response.raise_for_status()
        data = response.json()

        return LLMResult(
            content=data.get("response", ""),
            model=self.model,
            finish_reason=data.get("done_reason", "stop"),
            usage={
                "input_tokens": data.get("prompt_eval_count", 0),
                "output_tokens": data.get("eval_count", 0),
                "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
            },
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    async def reachable(self) -> bool:
        try:
            response = await self._http.get("/api/tags", timeout=2.0)
            return response.status_code == 200
        except httpx.HTTPError:
            return False


class OllamaEmbeddingProvider(EmbeddingProvider):
    name = "ollama"
    semantic = True

    def __init__(self, base_url: str = "http://localhost:11434",
                 model: str = "nomic-embed-text", timeout: float = 30.0) -> None:
        self.model = model
        self._http = httpx.AsyncClient(base_url=base_url, timeout=timeout)

    async def embed(self, text: str) -> list[float]:
        # modern endpoint first, legacy fallback
        response = await self._http.post("/api/embed", json={"model": self.model, "input": text})
        if response.status_code == 404:
            response = await self._http.post(
                "/api/embeddings", json={"model": self.model, "prompt": text}
            )
        response.raise_for_status()
        data = response.json()
        if "embeddings" in data:  # /api/embed shape: {"embeddings": [[...]]}
            return data["embeddings"][0]
        return data["embedding"]  # /api/embeddings shape: {"embedding": [...]}

    async def aclose(self) -> None:
        await self._http.aclose()

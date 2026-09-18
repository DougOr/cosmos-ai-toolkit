"""OpenAI-compatible chat provider (Z.AI BigModel, OpenAI, vLLM, ...).

Used only when LLM_PROVIDER=openai_compatible. The API key is read from the
environment by pydantic-settings and is never logged or persisted.
"""

import time

import httpx

from nebula_mind.providers.base import EmbeddingProvider, LLMResult, LLMProvider


class OpenAICompatibleProvider(LLMProvider):
    name = "openai_compatible"

    def __init__(self, base_url: str, api_key: str, model: str,
                 timeout: float = 60.0) -> None:
        if not api_key:
            raise ValueError("OPENAI_COMPAT_API_KEY is empty - set it in .env to use this provider")
        self.model = model
        self._http = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
        )

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> LLMResult:
        started = time.perf_counter()
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await self._http.post(
            "/chat/completions",
            json={
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )
        response.raise_for_status()
        data = response.json()
        choice = data["choices"][0]

        return LLMResult(
            content=choice["message"]["content"],
            model=data.get("model", self.model),
            finish_reason=choice.get("finish_reason", "stop"),
            usage=data.get("usage", {}),
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
        )

    async def aclose(self) -> None:
        await self._http.aclose()


class OpenAICompatibleEmbeddingProvider(EmbeddingProvider):
    name = "openai_compatible"
    semantic = True

    def __init__(self, base_url: str, api_key: str, model: str,
                 timeout: float = 30.0) -> None:
        if not api_key:
            raise ValueError("OPENAI_COMPAT_API_KEY is empty - set it in .env to use this provider")
        self.model = model
        self._http = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
        )

    async def embed(self, text: str) -> list[float]:
        response = await self._http.post(
            "/embeddings", json={"model": self.model, "input": text}
        )
        response.raise_for_status()
        return response.json()["data"][0]["embedding"]

    async def aclose(self) -> None:
        await self._http.aclose()

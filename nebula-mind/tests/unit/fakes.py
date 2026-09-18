"""Fakes for the NebulaMind unit suite: container, LLM, embedder."""

from azure.cosmos import exceptions

from nebula_mind.providers.base import EmbeddingProvider, LLMResult, LLMProvider


class FakeContainer:
    """Mirrors the subset of azure.cosmos.aio.ContainerProxy the engine calls."""

    def __init__(self) -> None:
        self.docs: dict[str, dict] = {}

    async def read_item(self, item: str, partition_key: str) -> dict:
        if item not in self.docs:
            raise exceptions.CosmosResourceNotFoundError(404, "Not Found")
        return self.docs[item]

    async def upsert_item(self, body: dict) -> dict:
        self.docs[body["id"]] = body
        return body

    async def delete_item(self, item: str, partition_key: str) -> None:
        if item not in self.docs:
            raise exceptions.CosmosResourceNotFoundError(404, "Not Found")
        del self.docs[item]

    def query_items(self, query: str, parameters=None, partition_key=None):
        async def _iter():
            # FakeContainer returns docs newest-last; the engine's real query
            # is ORDER BY created_at DESC - emulate newest-first ordering.
            for doc in reversed(list(self.docs.values())):
                yield doc

        return _iter()


class FakeLLMProvider(LLMProvider):
    name = "fake-llm"

    def __init__(self) -> None:
        self.calls: list[str] = []

    async def generate(self, prompt, system_prompt=None, temperature=0.7, max_tokens=1000):
        self.calls.append(prompt)
        return LLMResult(
            content=f"answer:{prompt[:40]}",
            model=self.name,
            usage={"input_tokens": 3, "output_tokens": 5, "total_tokens": 8},
            latency_ms=1.0,
        )


class FixedEmbeddingProvider(EmbeddingProvider):
    """Maps a fixed vocabulary to vectors; anything unknown -> zero vector."""

    name = "fixed"
    semantic = True

    def __init__(self, vocab: dict[str, list[float]]) -> None:
        self.vocab = vocab

    async def embed(self, text: str) -> list[float]:
        dim = len(next(iter(self.vocab.values()))) if self.vocab else 4
        vector = [0.0] * dim
        for word in text.lower().split():
            if word in self.vocab:
                for i, v in enumerate(self.vocab[word]):
                    vector[i] += v
        norm = sum(v * v for v in vector) ** 0.5 or 1.0
        return [v / norm for v in vector]

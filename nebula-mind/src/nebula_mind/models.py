"""Pydantic v2 request/response models."""

from typing import Any

from pydantic import BaseModel, Field

from nebula_mind.ttl import TTL_PRESET_SECONDS

TTL_PRESET_HELP = ", ".join(TTL_PRESET_SECONDS)


class LLMCacheRequest(BaseModel):
    prompt: str = Field(min_length=1)
    system_prompt: str | None = None
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1000, ge=1)
    ttl_preset: str | None = Field(default=None, description=f"One of: {TTL_PRESET_HELP}")
    ttl_seconds: int | None = Field(default=None, ge=-1)


class LLMCacheResponse(BaseModel):
    status: str  # exact_hit | generated
    entry_id: str
    prompt_preview: str
    answer: dict[str, Any]
    source: str
    similarity: float | None = None
    latency_ms: float
    ttl_remaining: float | None = None


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=25)


class SearchResponse(BaseModel):
    query: str
    embedding_provider: str
    embedding_semantic: bool
    threshold: float
    scanned: int
    hits: list[dict[str, Any]]
    latency_ms: float


class BenchmarkResponse(BaseModel):
    ops: int
    generated_total_s: float
    exact_hit_total_s: float
    generated_avg_ms: float
    exact_hit_avg_ms: float
    speedup: float
    semantic_note: str


class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
    cache_container: str
    llm_provider: str
    embedding_provider: str
    embedding_semantic: bool
    similarity_threshold: float
    entry_count: int

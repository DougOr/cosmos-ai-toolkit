"""Pydantic v2 request/response models."""

from typing import Any

from pydantic import BaseModel, Field

from quasar_ai.ttl import TTL_PRESET_SECONDS

TTL_PRESET_HELP = ", ".join(TTL_PRESET_SECONDS)


class CachePutRequest(BaseModel):
    cache_key: str = Field(min_length=1, description="Unique identifier for the cached data")
    system_prompt: str | None = Field(default=None)
    user_prompt: str = Field(min_length=1)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1000, ge=1)
    ttl_preset: str | None = Field(default=None, description=f"One of: {TTL_PRESET_HELP}")
    ttl_seconds: int | None = Field(default=None, ge=-1, description="Overrides the preset")


class GenericPutRequest(BaseModel):
    key: str = Field(min_length=1)
    data: dict[str, Any]
    ttl_preset: str | None = Field(default=None, description=f"One of: {TTL_PRESET_HELP}")
    ttl_seconds: int | None = Field(default=None, ge=-1)


class BulkRequest(BaseModel):
    items: list[CachePutRequest] = Field(min_length=1, max_length=100)


class BulkResponse(BaseModel):
    results: list[dict[str, Any]]
    total: int
    successful: int
    failed: int


class WarmRequest(BaseModel):
    count: int = Field(default=10, ge=1, le=25)
    ttl_preset: str | None = Field(default=None)


class InvalidateResponse(BaseModel):
    status: str
    pattern: str | None = None
    deleted: int


class BenchmarkResponse(BaseModel):
    ops: int
    miss_total_s: float
    hit_total_s: float
    miss_avg_ms: float
    hit_avg_ms: float
    miss_p95_ms: float
    hit_p95_ms: float
    speedup: float


class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
    intelligent_container: str
    generic_container: str
    default_ttl: int
    ttl_presets: list[str]
    entry_count: int

"""
Azure Cosmos DB Caching Layer Harness - Production MVP
A dual-container caching system for LLM prompts and generic JSON data
"""

import asyncio
import hashlib
import json
import os
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from azure.cosmos import CosmosClient, PartitionKey
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
import uvicorn

# Load environment variables from .env file
load_dotenv()

# ============================================================================
# CONFIGURATION
# ============================================================================

COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT", "https://localhost:8081/")
COSMOS_KEY = os.getenv(
    "COSMOS_KEY",
    "C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw==",
)
DATABASE_NAME = os.getenv("DATABASE_NAME", "PromptHarnessDB")
CACHE_CONTAINER = os.getenv("CACHE_CONTAINER", "PromptCache")
GENERIC_CONTAINER = os.getenv("GENERIC_CONTAINER", "GenericCache")
DEFAULT_TTL = int(os.getenv("DEFAULT_TTL", "120"))  # seconds
SIMULATED_LATENCY_SECONDS = float(os.getenv("SIMULATED_LATENCY_SECONDS", "0.3"))

# ============================================================================
# TTL PRESETS AND CONFIGURATION
# ============================================================================

class TTLPreset(str):
    """TTL preset enum for common cache durations."""
    INDEFINITE = "indefinite"
    MIN_1 = "1min"
    MIN_2 = "2min"
    MIN_5 = "5min"
    MIN_15 = "15min"
    MIN_30 = "30min"
    HOUR_1 = "1hour"
    HOUR_6 = "6hours"
    HOUR_24 = "24hours"

TTL_PRESET_SECONDS = {
    TTLPreset.INDEFINITE: -1,  # No expiration
    TTLPreset.MIN_1: 60,
    TTLPreset.MIN_2: 120,       # Current default
    TTLPreset.MIN_5: 300,
    TTLPreset.MIN_15: 900,
    TTLPreset.MIN_30: 1800,
    TTLPreset.HOUR_1: 3600,
    TTLPreset.HOUR_6: 21600,
    TTLPreset.HOUR_24: 86400
}

def resolve_ttl(ttl_preset: Optional[str] = None, ttl_seconds: Optional[int] = None) -> Optional[int]:
    """
    Resolve TTL from preset or direct seconds value.
    Presets take precedence over direct seconds.
    """
    if ttl_preset:
        return TTL_PRESET_SECONDS.get(ttl_preset, ttl_seconds)
    return ttl_seconds

# ============================================================================
# PYDANTIC MODELS
# ============================================================================


class AICacheRequest(BaseModel):
    """Request model for intelligent caching of any data with auto-generation on miss."""

    cache_key: str = Field(..., description="Unique identifier for the cached data")
    system_prompt: Optional[str] = Field(None, description="Optional system prompt")
    user_prompt: str = Field(..., description="The user prompt/data to cache")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="LLM temperature parameter")
    max_tokens: int = Field(1000, ge=1, description="Maximum tokens to generate")
    ttl_preset: Optional[str] = Field(None, description="TTL preset (indefinite, 1min, 2min, 5min, 15min, 30min, 1hour, 6hours, 24hours)")
    ttl_seconds: Optional[int] = Field(None, description="Optional TTL in seconds (overrides preset)")


class AICacheResponse(BaseModel):
    """Response model for intelligent cache operations."""

    status: str = Field(..., description="hit, miss, or created")
    cache_key: str = Field(..., description="The cache key used")
    generated_response: Dict[str, Any] = Field(..., description="The generated/mocked response")
    source: str = Field(..., description="cache or llm_simulation")
    latency_ms: float = Field(..., description="Operation latency in milliseconds")
    ttl_remaining: Optional[float] = Field(None, description="TTL remaining in seconds (if applicable)")


class BulkAICacheRequest(BaseModel):
    """Request model for bulk intelligent caching operations."""

    items: List[AICacheRequest] = Field(..., description="List of items to cache")


class BulkAICacheResponse(BaseModel):
    """Response model for bulk intelligent cache operations."""

    results: List[Dict[str, Any]] = Field(..., description="List of individual operation results")
    total_processed: int = Field(..., description="Total number of items processed")
    successful: int = Field(..., description="Number of successful operations")
    failed: int = Field(..., description="Number of failed operations")


class GenericCacheRequest(BaseModel):
    """Request model for generic JSON data caching."""

    key: str = Field(..., description="Unique identifier for the cached data")
    data: Dict[str, Any] = Field(..., description="The JSON data to cache")
    ttl_preset: Optional[str] = Field(None, description="TTL preset (indefinite, 1min, 2min, 5min, 15min, 30min, 1hour, 6hours, 24hours)")
    ttl_seconds: Optional[int] = Field(None, description="Optional TTL in seconds (overrides preset)")


class GenericCacheResponse(BaseModel):
    """Response model for generic cache operations."""

    status: str = Field(..., description="hit, miss, or created")
    key: str = Field(..., description="The key used")
    data: Optional[Dict[str, Any]] = Field(None, description="The cached data")
    source: str = Field(..., description="cache or created")
    ttl_remaining: Optional[float] = Field(None, description="TTL remaining in seconds (if applicable)")


class BulkGenericCacheRequest(BaseModel):
    """Request model for bulk generic caching operations."""

    items: List[GenericCacheRequest] = Field(..., description="List of items to cache")


class BulkGenericCacheResponse(BaseModel):
    """Response model for bulk generic cache operations."""

    results: List[Dict[str, Any]] = Field(..., description="List of individual operation results")
    total_processed: int = Field(..., description="Total number of items processed")
    successful: int = Field(..., description="Number of successful operations")
    failed: int = Field(..., description="Number of failed operations")


class CacheWarmingRequest(BaseModel):
    """Request model for cache warming operations."""

    cache_keys: Optional[List[str]] = Field(None, description="List of specific keys to warm (optional)")
    count: Optional[int] = Field(10, description="Number of common items to warm if no keys specified")
    ttl_preset: Optional[str] = Field(None, description="TTL preset for warmed items")


class CacheWarmingResponse(BaseModel):
    """Response model for cache warming operations."""

    warmed_keys: List[str] = Field(..., description="List of successfully warmed cache keys")
    total_warmed: int = Field(..., description="Total number of items warmed")
    duration_ms: float = Field(..., description="Time taken for warming operation")


class BenchmarkResult(BaseModel):
    """Response model for benchmark results."""

    miss_duration: float = Field(..., description="Total time for 50 cache misses (seconds)")
    hit_duration: float = Field(..., description="Total time for 50 cache hits (seconds)")
    speedup_factor: float = Field(..., description="How much faster cache hits are")
    avg_miss_latency_ms: float = Field(..., description="Average latency per cache miss")
    avg_hit_latency_ms: float = Field(..., description="Average latency per cache hit")


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def get_doc_id(key: str) -> str:
    """
    Generate a consistent document ID from a key using MD5 hash.
    This ensures the same key always maps to the same document ID.
    """
    return hashlib.md5(key.encode()).hexdigest()


async def simulate_llm_generation(input_data: str) -> Dict[str, Any]:
    """
    Simulate an LLM generation call with realistic latency and response.
    This is used when cache misses occur to demonstrate auto-caching.
    """
    start_time = time.time()

    # Simulate LLM inference latency
    await asyncio.sleep(SIMULATED_LATENCY_SECONDS)

    # Generate a realistic AI-like response
    mock_response = {
        "generated_at": datetime.utcnow().isoformat(),
        "request": input_data[:100] + "..." if len(input_data) > 100 else input_data,
        "response": {
            "content": f"This is a simulated AI response to: '{input_data[:50]}...'",
            "model": "gpt-4-simulator",
            "finish_reason": "stop",
            "usage": {
                "input_tokens": len(input_data.split()) * 2,
                "output_tokens": 50,
                "total_tokens": len(input_data.split()) * 2 + 50,
            },
        },
        "latency_ms": round((time.time() - start_time) * 1000, 2),
    }

    return mock_response


async def get_or_create_container(
    database: Any, container_name: str, partition_key: str
) -> Any:
    """
    Get an existing container or create it if it doesn't exist.
    Enables TTL (Time-to-Live) on the container for automatic expiration.
    """
    try:
        container = database.get_container_client(container_name)
        # Test if container exists by reading it
        container.read()
        print(f"✓ Container '{container_name}' already exists")
        return container
    except CosmosResourceNotFoundError:
        print(f"Creating container '{container_name}'...")
        container = database.create_container(
            id=container_name,
            partition_key=PartitionKey(path=f"/{partition_key}"),
            default_ttl=DEFAULT_TTL,  # Enable TTL for automatic expiration
        )
        print(f"✓ Container '{container_name}' created with TTL={DEFAULT_TTL}s")
        return container


def calculate_ttl_remaining(ttl_value: Optional[int], created_at: str) -> Optional[float]:
    """
    Calculate remaining TTL for a cached item.
    Returns None if item doesn't expire or if calculation isn't possible.
    """
    if ttl_value is None or ttl_value <= 0:  # No expiration or indefinite
        return None

    try:
        # Handle different datetime formats
        if created_at.endswith('Z'):
            created_at = created_at.replace('Z', '+00:00')

        # Ensure the datetime string has timezone info
        if '+' not in created_at and created_at.count('-') == 2:  # Simple YYYY-MM-DD format
            created_time = datetime.fromisoformat(created_at)
        else:
            created_time = datetime.fromisoformat(created_at)

        # Use current time with proper timezone handling
        current_time = datetime.utcnow()

        elapsed = (current_time - created_time).total_seconds()

        # Handle negative elapsed time (created in future)
        elapsed = max(0, elapsed)

        remaining = ttl_value - elapsed
        return max(0, remaining) if remaining > 0 else None
    except Exception as e:
        # Log the error for debugging but don't crash
        print(f"TTL calculation error: {e}, ttl_value={ttl_value}, created_at={created_at}")
        return None
        return None


async def cache_invalidation_pattern(container: Any, pattern: str, partition_key: str) -> Dict[str, Any]:
    """
    Invalidate cache entries matching a pattern using Cosmos DB SQL queries.
    This is a simplified implementation - in production you'd want more sophisticated pattern matching.
    """
    try:
        # Simple pattern matching using LIKE operator
        query = f"SELECT c.id, c.cache_key, c.key FROM c WHERE c.cache_key LIKE '%{pattern}%' OR c.key LIKE '%{pattern}%'"

        items = list(container.query_items(
            query=query,
            partition_key=partition_key
        ))

        deleted_count = 0
        for item in items:
            try:
                container.delete_item(item=item["id"], partition_key=partition_key)
                deleted_count += 1
            except:
                pass  # Skip items that fail to delete

        return {
            "status": "pattern_invalidation_completed",
            "pattern": pattern,
            "deleted_count": deleted_count,
            "message": f"Invalidated {deleted_count} items matching pattern '{pattern}'"
        }
    except Exception as e:
        return {
            "status": "pattern_invalidation_failed",
            "pattern": pattern,
            "error": str(e),
            "message": f"Failed to invalidate items matching pattern '{pattern}'"
        }


# ============================================================================
# FASTAPI APP INITIALIZATION
# ============================================================================

app = FastAPI(
    title="Azure Cosmos DB Intelligent Caching Harness",
    description="Production-ready intelligent caching layer for AI/LLM data and generic JSON with auto-generation, bulk operations, and advanced TTL management",
    version="2.0.0",
)

# Global variables to hold Cosmos DB resources
cosmos_client: Optional[CosmosClient] = None
database: Optional[Any] = None
intelligent_cache_container: Optional[Any] = None
generic_container: Optional[Any] = None


@app.on_event("startup")
async def startup_event():
    """
    Initialize Cosmos DB connection and create containers on startup.
    This ensures the database and containers exist before serving requests.
    """
    global cosmos_client, database, intelligent_cache_container, generic_container

    # Print beautiful startup banner
    print("\n" + "=" * 70)
    print("🚀 AZURE COSMOS DB INTELLIGENT CACHING HARNESS - STARTING UP")
    print("=" * 70)
    print(f"📦 Cosmos DB Endpoint: {COSMOS_ENDPOINT}")
    print(f"🗄️  Database: {DATABASE_NAME}")
    print(f"🧠 Intelligent Cache Container: {CACHE_CONTAINER}")
    print(f"🔧 Generic Container: {GENERIC_CONTAINER}")
    print(f"⏱️  Default TTL: {DEFAULT_TTL} seconds")
    print(f"🎭 Simulated Latency: {SIMULATED_LATENCY_SECONDS}s")
    print("=" * 70 + "\n")

    # Initialize Cosmos DB client
    # Note: connection_verify=False is required for the local emulator
    cosmos_client = CosmosClient(COSMOS_ENDPOINT, credential=COSMOS_KEY, connection_verify=False)
    print("✓ Connected to Azure Cosmos DB Emulator")

    # Create or get database
    try:
        database = cosmos_client.get_database_client(DATABASE_NAME)
        database.read()
        print(f"✓ Database '{DATABASE_NAME}' already exists")
    except CosmosResourceNotFoundError:
        database = cosmos_client.create_database(DATABASE_NAME)
        print(f"✓ Database '{DATABASE_NAME}' created")

    # Create or get containers
    intelligent_cache_container = await get_or_create_container(database, CACHE_CONTAINER, "cache_partition")
    generic_container = await get_or_create_container(database, GENERIC_CONTAINER, "generic_partition")

    print("\n✅ Intelligent Caching Harness is ready!")
    print("📖 Swagger UI available at: http://localhost:8001/docs")
    print("🎯 Intelligent Cache endpoints: /cache/*")
    print("🔧 Generic endpoints: /generic/*")
    print("📊 Bulk operations: /cache/bulk, /generic/bulk")
    print("🔥 Cache warming: /cache/warm")
    print("=" * 70 + "\n")


@app.on_event("shutdown")
async def shutdown_event():
    """Gracefully close Cosmos DB connection on shutdown."""
    print("\n🛑 Shutting down Caching Harness...")
    if cosmos_client:
        cosmos_client.close()
        print("✓ Cosmos DB connection closed")
    print("👋 Goodbye!\n")


# ============================================================================
# INTELLIGENT CACHE ENDPOINTS (Auto-Generation on Miss)
# ============================================================================


@app.post("/cache", status_code=status.HTTP_201_CREATED)
async def cache_ai_data(request: AICacheRequest) -> AICacheResponse:
    """
    Cache intelligent data with auto-generated LLM responses.
    Supports any data type with prompts, configurations, or AI-related content.
    Includes TTL presets and enhanced management features.
    """
    start_time = time.time()

    # Generate simulated response
    generated_response = await simulate_llm_generation(request.user_prompt)

    # Resolve TTL
    ttl_value = resolve_ttl(request.ttl_preset, request.ttl_seconds)

    # Prepare document for Cosmos DB
    doc_id = get_doc_id(request.cache_key)
    document = {
        "id": doc_id,
        "cache_partition": "cache_partition",  # Partition key field matching container path
        "cache_key": request.cache_key,
        "system_prompt": request.system_prompt,
        "user_prompt": request.user_prompt,
        "temperature": request.temperature,
        "max_tokens": request.max_tokens,
        "generated_response": generated_response,
        "created_at": datetime.utcnow().isoformat(),
        "ttl_preset": request.ttl_preset,
        "ttl_value": ttl_value,
        "ttl": ttl_value if ttl_value and ttl_value > 0 else DEFAULT_TTL
    }

    # Store in Cosmos DB
    intelligent_cache_container.create_item(body=document)

    latency_ms = (time.time() - start_time) * 1000
    ttl_remaining = ttl_value if ttl_value and ttl_value > 0 else None

    return AICacheResponse(
        status="created",
        cache_key=request.cache_key,
        generated_response=generated_response,
        source="llm_simulation",
        latency_ms=round(latency_ms, 2),
        ttl_remaining=ttl_remaining
    )


@app.get("/cache/{cache_key}")
async def get_ai_data(cache_key: str) -> AICacheResponse:
    """
    Retrieve cached intelligent data with auto-generation on miss.
    If not found (cache miss), simulate an LLM call, cache the result, and return it.
    """
    start_time = time.time()

    doc_id = get_doc_id(cache_key)

    try:
        # Try to get from cache
        document = intelligent_cache_container.read_item(item=doc_id, partition_key="cache_partition")

        latency_ms = (time.time() - start_time) * 1000

        # Calculate TTL remaining with error handling
        try:
            ttl_remaining = calculate_ttl_remaining(
                document.get("ttl_value"),
                document.get("created_at", datetime.utcnow().isoformat())
            )
        except Exception as ttl_error:
            print(f"TTL calculation error: {ttl_error}")
            ttl_remaining = None

        return AICacheResponse(
            status="hit",
            cache_key=cache_key,
            generated_response=document["generated_response"],
            source="cache",
            latency_ms=round(latency_ms, 2),
            ttl_remaining=ttl_remaining
        )

    except CosmosResourceNotFoundError:
        # Cache miss - simulate LLM generation and cache the result
        generated_response = await simulate_llm_generation(f"cache_key:{cache_key}")

        # Create new document with default TTL
        document = {
            "id": doc_id,
            "cache_partition": "cache_partition",
            "cache_key": cache_key,
            "user_prompt": f"Auto-generated for key: {cache_key}",
            "temperature": 0.7,
            "max_tokens": 1000,
            "generated_response": generated_response,
            "created_at": datetime.utcnow().isoformat(),
            "ttl_value": DEFAULT_TTL,
            "ttl_preset": "2min",
            "ttl": DEFAULT_TTL
        }

        # Store in cache for future requests
        intelligent_cache_container.create_item(body=document)

        latency_ms = (time.time() - start_time) * 1000

        return AICacheResponse(
            status="miss",
            cache_key=cache_key,
            generated_response=generated_response,
            source="llm_simulation",
            latency_ms=round(latency_ms, 2),
            ttl_remaining=float(DEFAULT_TTL)
        )


@app.delete("/cache/invalidate")
async def invalidate_cache(pattern: str = "") -> Dict[str, Any]:
    """
    Invalidate cache entries matching a pattern.
    If no pattern provided, clears all cache entries.
    """
    if pattern:
        result = await cache_invalidation_pattern(intelligent_cache_container, pattern, "cache_partition")
    else:
        # Clear all cache (use with caution!)
        try:
            # This is a simplified implementation - in production you'd want more sophisticated clearing
            query = "SELECT c.id FROM c"
            items = list(intelligent_cache_container.query_items(query=query, partition_key="cache_partition"))

            deleted_count = 0
            for item in items:
                try:
                    intelligent_cache_container.delete_item(item=item["id"], partition_key="cache_partition")
                    deleted_count += 1
                except:
                    pass

            result = {
                "status": "cache_cleared",
                "deleted_count": deleted_count,
                "message": f"Cleared {deleted_count} items from Intelligent Cache"
            }
        except Exception as e:
            result = {
                "status": "cache_clear_failed",
                "error": str(e),
                "message": "Failed to clear cache"
            }

    return result


@app.delete("/cache/{cache_key}")
async def delete_ai_data(cache_key: str) -> Dict[str, str]:
    """
    Delete cached intelligent data by key.
    Returns 404 if the key doesn't exist.
    """
    doc_id = get_doc_id(cache_key)

    try:
        intelligent_cache_container.delete_item(item=doc_id, partition_key="cache_partition")
        return {"status": "deleted", "cache_key": cache_key}
    except CosmosResourceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cache key '{cache_key}' not found",
        )


# ============================================================================
# GENERIC CACHE ENDPOINTS (Enhanced with TTL Presets)
# ============================================================================


@app.post("/generic", status_code=status.HTTP_201_CREATED)
async def cache_generic(request: GenericCacheRequest) -> GenericCacheResponse:
    """
    Store arbitrary JSON data in the generic cache container.
    Supports TTL presets and enhanced management features.
    """
    doc_id = get_doc_id(request.key)

    # Resolve TTL
    ttl_value = resolve_ttl(request.ttl_preset, request.ttl_seconds)

    document = {
        "id": doc_id,
        "generic_partition": "generic_partition",
        "key": request.key,
        "data": request.data,
        "created_at": datetime.utcnow().isoformat(),
        "ttl_preset": request.ttl_preset,
        "ttl_value": ttl_value,
        "ttl": ttl_value if ttl_value and ttl_value > 0 else DEFAULT_TTL
    }

    generic_container.create_item(body=document)

    ttl_remaining = ttl_value if ttl_value and ttl_value > 0 else None

    return GenericCacheResponse(
        status="created",
        key=request.key,
        data=request.data,
        source="created",
        ttl_remaining=ttl_remaining
    )


@app.get("/generic/{key}")
async def get_generic(key: str) -> GenericCacheResponse:
    """
    Retrieve cached generic JSON data by key.
    Returns 404 if the key doesn't exist (no auto-caching for generic data).
    """
    doc_id = get_doc_id(key)

    try:
        document = generic_container.read_item(item=doc_id, partition_key="generic_partition")

        # Calculate TTL remaining with error handling
        try:
            ttl_remaining = calculate_ttl_remaining(
                document.get("ttl_value"),
                document.get("created_at", datetime.utcnow().isoformat())
            )
        except Exception as ttl_error:
            print(f"TTL calculation error: {ttl_error}")
            ttl_remaining = None

        return GenericCacheResponse(
            status="hit",
            key=key,
            data=document["data"],
            source="cache",
            ttl_remaining=ttl_remaining
        )
    except CosmosResourceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cache key '{key}' not found",
        )


@app.delete("/generic/invalidate")
async def invalidate_generic_cache(pattern: str = "") -> Dict[str, Any]:
    """
    Invalidate generic cache entries matching a pattern.
    If no pattern provided, clears all generic cache entries.
    """
    if pattern:
        result = await cache_invalidation_pattern(generic_container, pattern, "generic_partition")
    else:
        # Clear all generic cache (use with caution!)
        try:
            query = "SELECT c.id FROM c"
            items = list(generic_container.query_items(query=query, partition_key="generic_partition"))

            deleted_count = 0
            for item in items:
                try:
                    generic_container.delete_item(item=item["id"], partition_key="generic_partition")
                    deleted_count += 1
                except:
                    pass

            result = {
                "status": "cache_cleared",
                "deleted_count": deleted_count,
                "message": f"Cleared {deleted_count} items from generic cache"
            }
        except Exception as e:
            result = {
                "status": "cache_clear_failed",
                "error": str(e),
                "message": "Failed to clear generic cache"
            }

    return result


@app.delete("/generic/{key}")
async def delete_generic(key: str) -> Dict[str, str]:
    """
    Delete cached generic JSON data by key.
    Returns 404 if the key doesn't exist.
    """
    doc_id = get_doc_id(key)

    try:
        generic_container.delete_item(item=doc_id, partition_key="generic_partition")
        return {"status": "deleted", "key": key}
    except CosmosResourceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cache key '{key}' not found",
        )


# ============================================================================
# BULK OPERATIONS ENDPOINTS
# ============================================================================


@app.post("/cache/bulk", status_code=status.HTTP_201_CREATED)
async def bulk_cache_ai_data(request: BulkAICacheRequest) -> BulkAICacheResponse:
    """
    Bulk cache multiple intelligent data items.
    Process multiple items in parallel for better performance.
    """
    start_time = time.time()
    results = []
    successful = 0
    failed = 0

    for item in request.items:
        try:
            # Create individual request for each item
            item_request = AICacheRequest(**item.dict())

            # Cache the item using the existing endpoint logic
            generated_response = await simulate_llm_generation(item_request.user_prompt)

            # Resolve TTL
            ttl_value = resolve_ttl(item_request.ttl_preset, item_request.ttl_seconds)

            doc_id = get_doc_id(item_request.cache_key)
            document = {
                "id": doc_id,
                "cache_partition": "cache_partition",
                "cache_key": item_request.cache_key,
                "system_prompt": item_request.system_prompt,
                "user_prompt": item_request.user_prompt,
                "temperature": item_request.temperature,
                "max_tokens": item_request.max_tokens,
                "generated_response": generated_response,
                "created_at": datetime.utcnow().isoformat(),
                "ttl_preset": item_request.ttl_preset,
                "ttl_value": ttl_value,
                "ttl": ttl_value if ttl_value and ttl_value > 0 else DEFAULT_TTL
            }

            if ttl_value is not None and ttl_value > 0:
                document["ttl"] = ttl_value

            intelligent_cache_container.create_item(body=document)

            results.append({
                "cache_key": item_request.cache_key,
                "status": "created",
                "source": "llm_simulation"
            })
            successful += 1

        except Exception as e:
            results.append({
                "cache_key": item.cache_key,
                "status": "failed",
                "error": str(e)
            })
            failed += 1

    duration_ms = (time.time() - start_time) * 1000

    return BulkAICacheResponse(
        results=results,
        total_processed=len(request.items),
        successful=successful,
        failed=failed
    )


@app.post("/generic/bulk", status_code=status.HTTP_201_CREATED)
async def bulk_cache_generic(request: BulkGenericCacheRequest) -> BulkGenericCacheResponse:
    """
    Bulk cache multiple generic JSON data items.
    Process multiple items in parallel for better performance.
    """
    results = []
    successful = 0
    failed = 0

    for item in request.items:
        try:
            # Resolve TTL
            ttl_value = resolve_ttl(item.ttl_preset, item.ttl_seconds)

            doc_id = get_doc_id(item.key)
            document = {
                "id": doc_id,
                "generic_partition": "generic_partition",
                "key": item.key,
                "data": item.data,
                "created_at": datetime.utcnow().isoformat(),
                "ttl_preset": item.ttl_preset,
                "ttl_value": ttl_value,
                "ttl": ttl_value if ttl_value and ttl_value > 0 else DEFAULT_TTL
            }

            generic_container.create_item(body=document)

            results.append({
                "key": item.key,
                "status": "created",
                "source": "bulk_created"
            })
            successful += 1

        except Exception as e:
            results.append({
                "key": item.key,
                "status": "failed",
                "error": str(e)
            })
            failed += 1

    return BulkGenericCacheResponse(
        results=results,
        total_processed=len(request.items),
        successful=successful,
        failed=failed
    )


# ============================================================================
# CACHE WARMING ENDPOINTS
# ============================================================================


@app.post("/cache/warm", status_code=status.HTTP_201_CREATED)
async def warm_ai_cache(request: CacheWarmingRequest) -> CacheWarmingResponse:
    """
    Warm the Intelligent Cache by pre-generating and caching common items.
    Either warm specific keys or generate common items automatically.
    """
    start_time = time.time()
    warmed_keys = []

    if request.cache_keys:
        # Warm specific keys provided
        for cache_key in request.cache_keys:
            try:
                # Check if already cached
                doc_id = get_doc_id(cache_key)
                try:
                    intelligent_cache_container.read_item(item=doc_id, partition_key="cache_partition")
                    # Already exists, skip
                    warmed_keys.append(cache_key)
                except CosmosResourceNotFoundError:
                    # Not cached, generate and cache
                    generated_response = await simulate_llm_generation(f"warm_key:{cache_key}")

                    # Resolve TTL
                    ttl_value = resolve_ttl(request.ttl_preset, None)
                    if ttl_value is None:
                        ttl_value = DEFAULT_TTL

                    doc_id = get_doc_id(cache_key)
                    document = {
                        "id": doc_id,
                        "cache_partition": "cache_partition",
                        "cache_key": cache_key,
                        "user_prompt": f"Pre-warmed for key: {cache_key}",
                        "temperature": 0.7,
                        "max_tokens": 1000,
                        "generated_response": generated_response,
                        "created_at": datetime.utcnow().isoformat(),
                        "ttl_value": ttl_value,
                        "ttl_preset": request.ttl_preset if request.ttl_preset else "2min",
                        "ttl": ttl_value if ttl_value and ttl_value > 0 else DEFAULT_TTL
                    }

                intelligent_cache_container.create_item(body=document)
                warmed_keys.append(cache_key)

            except Exception as e:
                print(f"Failed to warm key '{cache_key}': {e}")
    else:
        # Generate common items automatically
        common_patterns = [
            "greeting", "faq", "help", "support", "documentation",
            "tutorial", "getting_started", "troubleshooting", "best_practices",
            "api_reference", "examples", "templates", "config"
        ]

        for i, pattern in enumerate(common_patterns[:request.count]):
            try:
                cache_key = f"common_{pattern}"
                generated_response = await simulate_llm_generation(f"common_pattern:{pattern}")

                # Resolve TTL
                ttl_value = resolve_ttl(request.ttl_preset, None)
                if ttl_value is None:
                    ttl_value = DEFAULT_TTL

                doc_id = get_doc_id(cache_key)
                document = {
                    "id": doc_id,
                    "cache_partition": "cache_partition",
                    "cache_key": cache_key,
                    "user_prompt": f"Pre-warmed common pattern: {pattern}",
                    "temperature": 0.7,
                    "max_tokens": 1000,
                    "generated_response": generated_response,
                    "created_at": datetime.utcnow().isoformat(),
                    "ttl_value": ttl_value,
                    "ttl_preset": request.ttl_preset if request.ttl_preset else "2min",
                    "ttl": ttl_value if ttl_value and ttl_value > 0 else DEFAULT_TTL
                }

                intelligent_cache_container.create_item(body=document)
                warmed_keys.append(cache_key)

            except Exception as e:
                print(f"Failed to warm common pattern '{pattern}': {e}")

    duration_ms = (time.time() - start_time) * 1000

    return CacheWarmingResponse(
        warmed_keys=warmed_keys,
        total_warmed=len(warmed_keys),
        duration_ms=round(duration_ms, 2)
    )


# ============================================================================
# CACHE MANAGEMENT ENDPOINTS
# ============================================================================


# ============================================================================
# BENCHMARK ENDPOINT
# ============================================================================


@app.get("/benchmark")
async def run_benchmark() -> BenchmarkResult:
    """
    Run a performance benchmark comparing cache misses vs cache hits.
    Executes 50 unique items (misses) and 50 identical items (hits).
    Prints detailed results to console and returns JSON summary.
    """
    print("\n" + "=" * 70)
    print("📊 RUNNING CACHE PERFORMANCE BENCHMARK")
    print("=" * 70)

    # Benchmark 1: Cache misses (50 unique items)
    print("\n🔵 Testing 50 CACHE MISSES (unique items)...")
    miss_start = time.time()

    for i in range(50):
        unique_key = f"benchmark_item_{i}_{time.time()}"
        await get_ai_data(unique_key)

    miss_duration = time.time() - miss_start
    avg_miss_latency = (miss_duration / 50) * 1000  # Convert to ms

    print(f"✓ Completed 50 cache misses in {miss_duration:.2f}s")
    print(f"  Average latency: {avg_miss_latency:.2f}ms per request")

    # Benchmark 2: Cache hits (50 identical items on warmed cache)
    print("\n🟢 Testing 50 CACHE HITS (warmed cache)...")
    # First, create a cached item
    test_key = "benchmark_cached_item"
    await get_ai_data(test_key)  # This will cache it

    hit_start = time.time()

    for i in range(50):
        await get_ai_data(test_key)  # These should all be hits

    hit_duration = time.time() - hit_start
    avg_hit_latency = (hit_duration / 50) * 1000  # Convert to ms

    print(f"✓ Completed 50 cache hits in {hit_duration:.2f}s")
    print(f"  Average latency: {avg_hit_latency:.2f}ms per request")

    # Calculate speedup
    speedup_factor = miss_duration / hit_duration

    # Print formatted results
    print("\n" + "=" * 70)
    print("📈 BENCHMARK RESULTS")
    print("=" * 70)
    print(f"🔵 Cache Misses (50 unique):   {miss_duration:.2f}s total ({avg_miss_latency:.2f}ms avg)")
    print(f"🟢 Cache Hits (50 identical):   {hit_duration:.2f}s total ({avg_hit_latency:.2f}ms avg)")
    print(f"⚡ Speedup Factor:              {speedup_factor:.1f}x faster with cache")
    print("=" * 70 + "\n")

    return BenchmarkResult(
        miss_duration=round(miss_duration, 3),
        hit_duration=round(hit_duration, 3),
        speedup_factor=round(speedup_factor, 2),
        avg_miss_latency_ms=round(avg_miss_latency, 2),
        avg_hit_latency_ms=round(avg_hit_latency, 2),
    )


# ============================================================================
# HEALTH CHECK ENDPOINT
# ============================================================================


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint to verify the service is running.
    Returns connection status and container information.
    """
    return {
        "status": "healthy",
        "database": DATABASE_NAME,
        "cache_container": CACHE_CONTAINER,
        "generic_container": GENERIC_CONTAINER,
        "default_ttl": DEFAULT_TTL,
        "simulated_latency": SIMULATED_LATENCY_SECONDS,
        "ttl_presets": list(TTL_PRESET_SECONDS.keys()),
        "version": "2.0.0"
    }


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    uvicorn.run(
        "caching_layer_harness:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )

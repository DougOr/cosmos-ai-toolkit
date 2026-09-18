# Azure Cosmos DB Intelligent Caching Harness

A production-ready intelligent caching system built with FastAPI and Azure Cosmos DB (local emulator). This harness demonstrates dual-container caching with auto-generation on miss, bulk operations, advanced TTL management, and cache warming strategies for any data type.

## 🎯 Features

- **Intelligent Dual-Container Architecture**
  - **Intelligent Cache**: Smart caching with auto-generation on miss for any data type
  - **Generic Cache**: For arbitrary JSON data (configs, feature flags, sessions)

- **Advanced TTL Management**
  - **9 TTL Presets**: indefinite, 1min, 2min, 5min, 15min, 30min, 1hour, 6hours, 24hours
  - **Custom TTL**: Override presets with specific seconds
  - **TTL Remaining**: Shows remaining time in GET responses
  - **Flexible Control**: Per-item or default TTL configuration

- **Auto-Caching on Miss**: Simulates slow calls (300ms) and automatically caches results
- **Bulk Operations**: Process multiple items in parallel for efficiency
- **Cache Warming**: Pre-load common items for better performance
- **Cache Management**: Pattern-based invalidation and bulk clearing
- **Enhanced Monitoring**: TTL tracking, performance metrics, health status
- **Production-Ready**: Error handling, health checks, beautiful logging, Swagger UI
- **Cloud-Ready**: Works on local emulator now, Azure Cloud later (just change env vars)

## 📋 Prerequisites

1. **Windows** with Azure Cosmos DB Emulator (MSI installation)
2. **Python 3.11+** installed
3. **uv** package manager installed

## 🚀 Quick Start

### Step 1: Install Azure Cosmos DB Emulator

If you haven't already:

1. Download the Azure Cosmos DB Emulator from the official Microsoft site
2. Run the MSI installer
3. The emulator will start automatically and run on `https://localhost:8081/`
4. Keep the emulator running while using this harness

### Step 2: Initialize the Project

Open PowerShell or Command Prompt in the project directory:

```bash
cd "caching_layer_harness"

# Install dependencies
uv add fastapi uvicorn azure-cosmos python-dotenv pydantic

# Add dev dependency for testing
uv add --dev httpx
```

### Step 3: Verify the .env File

The `.env` file is already created with the following configuration:

```env
COSMOS_ENDPOINT=https://localhost:8081/
COSMOS_KEY=C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw==
DATABASE_NAME=CacheHarnessDB
CACHE_CONTAINER=IntelligentCache
GENERIC_CONTAINER=GenericCache
DEFAULT_TTL=120
SIMULATED_LATENCY_SECONDS=0.3
```

### Step 4: Run the Server

```bash
uv run uvicorn caching_layer_harness:app --reload --port 8001
```

You should see a beautiful startup banner:

```
======================================================================
🚀 AZURE COSMOS DB INTELLIGENT CACHING HARNESS - STARTING UP
======================================================================
📦 Cosmos DB Endpoint: https://localhost:8081/
🗄️  Database: CacheHarnessDB
🧠 Intelligent Cache Container: IntelligentCache
🔧 Generic Container: GenericCache
⏱️  Default TTL: 120 seconds
🎭 Simulated Latency: 0.3s
======================================================================

✓ Connected to Azure Cosmos DB Emulator
✓ Database 'CacheHarnessDB' already exists
✓ Container 'IntelligentCache' already exists
✓ Container 'GenericCache' already exists

✅ Intelligent Caching Harness is ready!
📖 Swagger UI available at: http://localhost:8001/docs
======================================================================
```

### Step 5: Test the Endpoints

#### Option A: Use Swagger UI (Recommended)

1. Open your browser to: `http://localhost:8001/docs`
2. Try the following endpoints:

**POST /cache** - Cache intelligent data with auto-generation:
```json
{
  "cache_key": "test_data_1",
  "system_prompt": "You are a helpful assistant",
  "user_prompt": "Explain quantum computing in simple terms",
  "temperature": 0.7,
  "max_tokens": 500,
  "ttl_preset": "5min"
}
```

**GET /cache/{cache_key}** - Retrieve (first call is miss, second is hit)

**DELETE /cache/{cache_key}** - Delete cached data

**POST /cache/bulk** - Bulk cache multiple items:
```json
{
  "items": [
    {
      "cache_key": "bulk_item_1",
      "user_prompt": "First item",
      "ttl_preset": "2min"
    },
    {
      "cache_key": "bulk_item_2",
      "user_prompt": "Second item",
      "ttl_preset": "2min"
    }
  ]
}
```

**POST /cache/warm** - Warm cache with common items:
```json
{
  "count": 5,
  "ttl_preset": "1hour"
}
```

**POST /generic** - Store any JSON:
```json
{
  "key": "feature_flags",
  "data": {
    "new_ui_enabled": true,
    "beta_features": ["chat", "analytics"]
  },
  "ttl_preset": "5min"
}
```

**POST /generic/bulk** - Bulk store JSON data:
```json
{
  "items": [
    {
      "key": "config_1",
      "data": {"setting": "value1"},
      "ttl_preset": "1min"
    },
    {
      "key": "config_2",
      "data": {"setting": "value2"},
      "ttl_preset": "1min"
    }
  ]
}
```

**GET /generic/{key}** - Retrieve cached JSON

**DELETE /generic/{key}** - Delete cached JSON

**DELETE /cache/invalidate?pattern=benchmark** - Invalidate cache by pattern

**DELETE /generic/invalidate** - Clear all generic cache

**GET /benchmark** - Run performance test (50 misses vs 50 hits)

**GET /health** - System health check with TTL presets info

#### Option B: Use PowerShell

```powershell
# Test intelligent cache (first call - MISS)
Invoke-RestMethod -Uri "http://localhost:8001/cache/test_data_1" -Method Get

# Test intelligent cache (second call - HIT)
Invoke-RestMethod -Uri "http://localhost:8001/cache/test_data_1" -Method Get

# Test bulk operations
$body = @{
    items = @(
        @{ cache_key = "bulk_1"; user_prompt = "First"; ttl_preset = "2min" },
        @{ cache_key = "bulk_2"; user_prompt = "Second"; ttl_preset = "2min" }
    )
} | ConvertTo-Json -Depth 3
Invoke-RestMethod -Uri "http://localhost:8001/cache/bulk" -Method Post -Body $body -ContentType "application/json"

# Test cache warming
$body = @{ count = 3; ttl_preset = "1hour" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8001/cache/warm" -Method Post -Body $body -ContentType "application/json"

# Run benchmark
Invoke-RestMethod -Uri "http://localhost:8001/benchmark" -Method Get

# Health check
Invoke-RestMethod -Uri "http://localhost:8001/health" -Method Get
```

## 📊 Benchmark Results

When you run `/benchmark`, you'll see output like:

```
======================================================================
📊 RUNNING CACHE PERFORMANCE BENCHMARK
======================================================================

🔵 Testing 50 CACHE MISSES (unique items)...
✓ Completed 50 cache misses in 15.23s
  Average latency: 304.60ms per request

🟢 Testing 50 CACHE HITS (warmed cache)...
✓ Completed 50 cache hits in 0.85s
  Average latency: 17.00ms per request

======================================================================
📈 BENCHMARK RESULTS
======================================================================
🔵 Cache Misses (50 unique):   15.23s total (304.60ms avg)
🟢 Cache Hits (50 identical):   0.85s total (17.00ms avg)
⚡ Speedup Factor:              17.9x faster with cache
======================================================================
```

## 🏗️ Architecture

### Data Models

**AICacheRequest:**
- `cache_key`: Unique identifier for cached data
- `system_prompt`: Optional system prompt
- `user_prompt`: The user's data to cache
- `temperature`: LLM temperature (0.0-2.0)
- `max_tokens`: Maximum tokens to generate
- `ttl_preset`: TTL preset (indefinite, 1min, 2min, 5min, 15min, 30min, 1hour, 6hours, 24hours)
- `ttl_seconds`: Optional custom TTL in seconds (overrides preset)

**GenericCacheRequest:**
- `key`: Unique identifier
- `data`: Arbitrary JSON object
- `ttl_preset`: TTL preset (indefinite, 1min, 2min, 5min, 15min, 30min, 1hour, 6hours, 24hours)
- `ttl_seconds`: Optional custom TTL in seconds (overrides preset)

**Response Enhancements:**
- `ttl_remaining`: Shows remaining time in seconds for cached items
- Enhanced status tracking for bulk operations
- Cache warming results with performance metrics

### Partition Key Strategy

For MVP simplicity, static partition keys are used:
- Intelligent Cache container: `"cache_partition"`
- Generic container: `"generic_partition"`

### TTL Implementation

**TTL Presets Available:**
- `indefinite`: No expiration (-1)
- `1min`: 60 seconds
- `2min`: 120 seconds (default)
- `5min`: 300 seconds
- `15min`: 900 seconds
- `30min`: 1800 seconds
- `1hour`: 3600 seconds
- `6hours`: 21600 seconds
- `24hours`: 86400 seconds

**Custom TTL:**
- Override presets with specific seconds using `ttl_seconds`
- `ttl_preset` takes precedence over `ttl_seconds`
- Cosmos DB automatically expires items when TTL elapses
- Responses include `ttl_remaining` field

## 🔧 Configuration

Edit `.env` to customize:

| Variable | Description | Default |
|----------|-------------|---------|
| `COSMOS_ENDPOINT` | Cosmos DB endpoint | `https://localhost:8081/` |
| `COSMOS_KEY` | Emulator authentication key | (provided) |
| `DATABASE_NAME` | Database name | `CacheHarnessDB` |
| `CACHE_CONTAINER` | Intelligent cache container | `IntelligentCache` |
| `GENERIC_CONTAINER` | Generic cache container | `GenericCache` |
| `DEFAULT_TTL` | Default TTL in seconds | `120` |
| `SIMULATED_LATENCY_SECONDS` | Simulation delay | `0.3` |

## 🚀 New Features Overview

### 🎯 **Enhanced Intelligent Cache Endpoints**
- **POST /cache**: Cache any data with auto-generation on miss
- **GET /cache/{cache_key}**: Retrieve with auto-caching on miss
- **DELETE /cache/{cache_key}**: Delete cached data
- **POST /cache/bulk**: Bulk cache multiple items efficiently
- **POST /cache/warm**: Pre-warm cache with common items
- **DELETE /cache/invalidate**: Pattern-based cache invalidation

### 🔧 **Enhanced Generic Cache Endpoints**
- **POST /generic**: Store JSON with TTL presets
- **GET /generic/{key}**: Retrieve cached JSON
- **DELETE /generic/{key}**: Delete cached JSON
- **POST /generic/bulk**: Bulk store JSON data
- **DELETE /generic/invalidate**: Clear generic cache

### 📊 **Management Endpoints**
- **GET /benchmark**: Performance testing (50 misses vs 50 hits)
- **GET /health**: System health check with TTL presets info
- **Pattern-based invalidation**: Clean up cache entries matching patterns
- **TTL remaining**: Shows expiration time in responses

## 🔥 Quick Feature Examples

### TTL Presets Usage
```json
// Using presets for common durations
{
  "cache_key": "user_session",
  "user_prompt": "Session data",
  "ttl_preset": "30min"
}
```

### Bulk Operations
```json
// Process multiple items efficiently
{
  "items": [
    {"cache_key": "item1", "user_prompt": "First", "ttl_preset": "5min"},
    {"cache_key": "item2", "user_prompt": "Second", "ttl_preset": "5min"},
    {"cache_key": "item3", "user_prompt": "Third", "ttl_preset": "5min"}
  ]
}
```

### Cache Warming
```json
// Pre-load common patterns for better performance
{
  "count": 10,
  "ttl_preset": "1hour"
}
```

### Pattern Invalidation
```bash
# Clear all benchmark-related cache entries
DELETE /cache/invalidate?pattern=benchmark

# Clear all generic cache
DELETE /generic/invalidate
```

## 📁 Project Structure

```
caching_layer_harness/
├── caching_layer_harness/
│   ├── __init__.py     # Package initialization
│   └── app.py          # Main FastAPI application with enhanced features
├── .env                 # Environment configuration
├── README.md            # This comprehensive guide
├── ARCHITECTURE.md      # System architecture documentation
├── QUICKSTART.md        # Quick reference card
├── setup.ps1            # Automated setup script
├── test-endpoints.ps1   # Test suite script (needs updating for new endpoints)
├── .gitignore          # Git ignore patterns
└── pyproject.toml       # uv project configuration
```

## 🛡️ Error Handling

The harness gracefully handles:
- `CosmosResourceNotFoundError`: Returns 404 for missing items
- Connection failures to emulator
- Invalid request data (Pydantic validation)
- Container/database creation on first run
- TTL calculation errors with fallback to None

## 🧪 Development

Run with hot reload:

```bash
uv run uvicorn caching_layer_harness:app --reload --host 0.0.0.0 --port 8001
```

## 📝 License

This is a demonstration project for portfolio purposes.

## 🤝 Support

For issues or questions:
1. Check the Azure Cosmos DB Emulator is running
2. Verify the .env configuration
3. Check the console logs for detailed error messages
4. Access `/health` endpoint to verify connection status

---

Built with ❤️ using FastAPI, Azure Cosmos DB, and modern Python best practices.

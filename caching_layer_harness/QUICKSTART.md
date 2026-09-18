# Intelligent Caching Harness - Quick Start Card

## 🚀 Run in 30 Seconds

```powershell
# 1. Navigate to project
cd "caching_layer_harness"

# 2. Install dependencies
uv add fastapi uvicorn azure-cosmos python-dotenv pydantic

# 3. Run server
uv run uvicorn caching_layer_harness:app --reload --port 8001
```

## 📖 Key URLs

- **Swagger UI**: http://localhost:8001/docs
- **Health Check**: http://localhost:8001/health
- **Benchmark**: http://localhost:8001/benchmark

## 🎯 Core Endpoints

### Intelligent Cache (Auto-Generation on Miss)
- `POST /cache` - Cache with auto-generation
- `GET /cache/{key}` - Retrieve (auto-caches on miss)
- `DELETE /cache/{key}` - Delete cached data
- `POST /cache/bulk` - Bulk operations
- `POST /cache/warm` - Cache warming
- `DELETE /cache/invalidate` - Pattern invalidation

### Generic Cache (JSON Data)
- `POST /generic` - Store JSON data
- `GET /generic/{key}` - Retrieve cached JSON
- `DELETE /generic/{key}` - Delete cached JSON
- `POST /generic/bulk` - Bulk operations
- `DELETE /generic/invalidate` - Clear cache

## 🔨 Quick Test

```powershell
# Test intelligent cache (MISS, then HIT)
Invoke-RestMethod http://localhost:8001/cache/test1
Invoke-RestMethod http://localhost:8001/cache/test1

# Test bulk operations
$body = @{items = @(@{cache_key="bulk1";user_prompt="Test";ttl_preset="2min"})} | ConvertTo-Json -Depth 3
Invoke-RestMethod http://localhost:8001/cache/bulk -Method Post -Body $body -ContentType "application/json"

# Run benchmark
Invoke-RestMethod http://localhost:8001/benchmark
```

## 📊 Performance Expectations

- **Cache Miss**: ~300ms (simulated latency)
- **Cache Hit**: ~15-20ms (database read)
- **Speedup**: ~18x faster with cache

## 🔧 Environment Variables

```env
COSMOS_ENDPOINT=https://localhost:8081/
COSMOS_KEY=C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw==
DATABASE_NAME=CacheHarnessDB
CACHE_CONTAINER=IntelligentCache
GENERIC_CONTAINER=GenericCache
DEFAULT_TTL=120
SIMULATED_LATENCY_SECONDS=0.3
```

## 🎯 TTL Presets Available

- `indefinite` - No expiration
- `1min` - 60 seconds
- `2min` - 120 seconds (default)
- `5min` - 300 seconds
- `15min` - 900 seconds
- `30min` - 1800 seconds
- `1hour` - 3600 seconds
- `6hours` - 21600 seconds
- `24hours` - 86400 seconds

## 🔥 New Features

✅ **9 TTL Presets** for easy cache duration management
✅ **Bulk Operations** for efficient multi-item processing
✅ **Cache Warming** for pre-loading common data
✅ **Pattern Invalidation** for targeted cache cleanup
✅ **TTL Remaining** field shows cache expiration time
✅ **Enhanced Error Handling** with graceful fallbacks

---

Built for portfolio demonstration with production-quality code and architecture.

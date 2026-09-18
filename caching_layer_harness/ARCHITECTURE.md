# Architecture Documentation

## System Overview

The Azure Cosmos DB Caching Layer Harness implements a dual-container caching architecture optimized for intelligent data caching with auto-generation on miss, plus generic JSON data storage with flexible TTL management and advanced features.

```
┌─────────────────────────────────────────────────────────────────────┐
│                     FASTAPI APPLICATION                            │
│                                                                     │
│  ┌──────────────────┐         ┌──────────────────┐                │
│  │ Intelligent Cache│         │  Generic Cache   │                │
│  │  Endpoints       │         │  Endpoints       │                │
│  │                  │         │                  │                │
│  │  POST /cache     │         │  POST /generic   │                │
│  │  GET  /cache/{k} │         │  GET  /generic/{k}│               │
│  │                  │         │  DEL  /generic/{k}│               │
│  └────────┬─────────┘         └────────┬─────────┘                │
│           │                             │                           │
│           │                             │                           │
│           ▼                             ▼                           │
│  ┌──────────────────┐         ┌──────────────────┐                │
│  │ Auto-Caching     │         │ Direct CRUD      │                │
│  │ on Miss Logic    │         │ Operations       │                │
│  └────────┬─────────┘         └────────┬─────────┘                │
│           │                             │                           │
│           │    ┌────────────────┐       │                           │
│           └────►  LLM Simulator │◄──────┘                           │
│                │  (300ms delay) │                                 │
│                └────────────────┘                                  │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              │ Azure Cosmos DB SDK
                              │ connection_verify=False
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│              AZURE COSMOS DB (Local Emulator)                       │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │              Database: CacheHarnessDB                          │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌──────────────────────────┐   ┌──────────────────────────┐      │
│  │ IntelligentCache Cont.  │   │  GenericCache Container  │      │
│  │                          │   │                          │      │
│  │  Partition Key:          │   │  Partition Key:          │      │
│  │  /cache_partition        │   │  /generic_partition      │      │
│  │                          │   │                          │      │
│  │  TTL: 120s (default)     │   │  TTL: 120s (default)     │      │
│  │                          │   │  (customizable per item) │      │
│  │  Document Structure:     │   │  Document Structure:     │      │
│  │  ┌────────────────────┐  │   │  ┌────────────────────┐  │      │
│  │  │ id (MD5 hash)      │  │   │  │ id (MD5 hash)      │  │      │
│  │  │ cache_partition    │  │   │  │ generic_partition  │  │      │
│  │  │ cache_key         │  │   │  │ key                │  │      │
│  │  │ system_prompt     │  │   │  │ data (JSON)        │  │      │
│  │  │ user_prompt       │  │   │  │ ttl (optional)     │  │      │
│  │  │ temperature       │  │   │  │ created_at         │  │      │
│  │  │ max_tokens        │  │   │  └────────────────────┘  │      │
│  │  │ generated_response │  │   │                          │      │
│  │  │ created_at        │  │   │                          │      │
│  │  └────────────────────┘  │   │                          │      │
│  └──────────────────────────┘   └──────────────────────────┘      │
└─────────────────────────────────────────────────────────────────────┘
```

## Request Flow

### Cache Hit Scenario (Intelligent Cache)
```
Client Request
     │
     ▼
GET /cache/existing_key
     │
     ▼
FastAPI Endpoint
     │
     ├─► Calculate doc_id = MD5(cache_key)
     │
     ├─► Query Cosmos DB for document
     │
     ├─► Document Found? ───Yes──► Return cached response
     │                              (latency: ~15-20ms)
     │
     └──No──► [Proceed to Cache Miss Flow]
```

### Cache Miss Scenario (Intelligent Cache) - Auto-Caching
```
Client Request
     │
     ▼
GET /cache/new_key
     │
     ▼
FastAPI Endpoint
     │
     ├─► Document Not Found
     │
     ├─► Call simulate_llm_generation()
     │        │
     │        └─► asyncio.sleep(300ms)
     │
     ├─► Generate mock AI response
     │
     ├─► Create new document with:
     │      • MD5-hashed ID
     │      • Static partition key
     │      • Generated response
     │      • Timestamp
     │
     ├─► Store document in Cosmos DB
     │
     └─► Return response (latency: ~300ms)
           (NOW CACHED FOR NEXT REQUEST!)
```

## Data Models

### IntelligentCache Document
```json
{
  "id": "5d41402abc4b2a76b9719d911017c592",
  "cache_partition": "cache_partition",
  "cache_key": "explain_quantum_physics",
  "system_prompt": "You are a helpful science tutor",
  "user_prompt": "Explain quantum physics in simple terms",
  "temperature": 0.7,
  "max_tokens": 1000,
  "generated_response": {
    "generated_at": "2024-01-15T10:30:00.000Z",
    "request": "Explain quantum physics...",
    "response": {
      "content": "This is a simulated AI response...",
      "model": "gpt-4-simulator",
      "finish_reason": "stop",
      "usage": {
        "input_tokens": 25,
        "output_tokens": 50,
        "total_tokens": 75
      }
    },
    "latency_ms": 304.5
  },
  "created_at": "2024-01-15T10:30:00.000Z",
  "ttl": 120,
  "ttl_preset": "2min"
}
```

### GenericCache Document
```json
{
  "id": "7d793037a0760186574b0282f2f435e2",
  "generic_partition": "generic_partition",
  "key": "feature_flags_v1",
  "data": {
    "new_ui_enabled": true,
    "beta_features": ["chat", "analytics"],
    "user_segment": "beta_testers"
  },
  "created_at": "2024-01-15T10:30:00.000Z",
  "_ttl": 300
}
```

## Endpoint Matrix

| Method | Endpoint | Request Body | Response | Auto-Cache on Miss |
|--------|-----------|--------------|----------|-------------------|
| POST | `/cache` | AICacheRequest | AICacheResponse | No |
| GET | `/cache/{key}` | - | AICacheResponse | **Yes** |
| DELETE | `/cache/{key}` | - | Status | No |
| POST | `/cache/bulk` | BulkAICacheRequest | BulkAICacheResponse | No |
| POST | `/cache/warm` | CacheWarmingRequest | CacheWarmingResponse | No |
| DELETE | `/cache/invalidate` | - | Status | No |
| POST | `/generic` | GenericCacheRequest | GenericCacheResponse | No |
| GET | `/generic/{key}` | - | GenericCacheResponse | No |
| DELETE | `/generic/{key}` | - | Status | No |
| POST | `/generic/bulk` | BulkGenericCacheRequest | BulkGenericCacheResponse | No |
| DELETE | `/generic/invalidate` | - | Status | No |
| GET | `/benchmark` | - | BenchmarkResult | N/A |
| GET | `/health` | - | HealthStatus | N/A |

## Performance Characteristics

### Cache Miss (First Request)
- **Latency**: ~300ms (simulated LLM call)
- **Database Writes**: 1 (new document created)
- **Database Reads**: 1 (check for existing)
- **Total Operations**: 2

### Cache Hit (Subsequent Requests)
- **Latency**: ~15-20ms (database read only)
- **Database Writes**: 0
- **Database Reads**: 1 (fetch cached document)
- **Total Operations**: 1

### Benchmark Results (Typical)
```
50 Cache Misses:  ~15 seconds total (304ms avg per request)
50 Cache Hits:    ~0.85 seconds total (17ms avg per request)
Speedup Factor:   ~18x faster with cache
```

## TTL and Expiration

### Default TTL Behavior
- All containers have `default_ttl = 120` seconds
- Documents automatically expire after TTL period
- Expired documents are automatically removed by Cosmos DB

### Custom TTL (All Cache Types)
- Set `ttl_seconds` or `ttl_preset` in cache requests
- Overrides container default for specific item
- Example: Cache feature flags for 300 seconds instead of 120

### TTL Implementation
```python
# Container creation with default TTL
database.create_container(
    id="IntelligentCache",
    partition_key=PartitionKey(path="/cache_partition"),
    default_ttl=120  # Enable TTL with 120s default
)

# Custom TTL for specific document
document["ttl"] = 300  # Override for this document only
```

## Partition Key Strategy

### MVP Approach (Static Partition Keys)
- **Intelligent Cache Container**: `/cache_partition` (static value)
- **Generic Container**: `/generic_partition` (static value)

### Advantages for MVP
- Simple to implement and understand
- No need to manage complex partition key logic
- All data co-located for fast queries
- Predictable performance for demo

### Production Considerations (Future)
- For scale, consider:
  - User-based partitioning
  - Time-based partitioning
  - Hash-based distribution
  - Synthetic partition keys

## Error Handling

### CosmosResourceNotFoundError
```python
try:
    document = container.read_item(doc_id, partition_key)
except CosmosResourceNotFoundError:
    # Handle cache miss or 404
    return HTTPException(status_code=404)
```

### Connection Errors
- `connection_verify=False` required for local emulator
- Proper error messages if emulator not running
- Graceful degradation with helpful messages

### Validation Errors
- Pydantic models validate all input
- Clear error messages for invalid data
- Type safety enforced at runtime

## Security Considerations

### Local Development
- Emulator key is well-known (no security)
- No authentication required
- Suitable for development/demo

### Production Migration
When moving to Azure Cloud:
1. Use Managed Identity or Key Vault
2. Enable SSL/TLS for all connections
3. Implement proper access controls
4. Use Azure RBAC for authorization
5. Enable Cosmos DB firewall rules

## Monitoring and Observability

### Current Implementation
- Console logging for all operations
- Startup banner with configuration
- Benchmark endpoint for performance testing
- Health check endpoint

### Production Enhancements (Future)
- Application Insights integration
- Structured logging with correlation IDs
- Custom metrics for cache hit/miss rates
- Alerting for elevated error rates
- Performance counters for latency tracking

## Scalability Path

### Current MVP
- Single Cosmos DB container
- Static partition keys
- In-memory emulator
- Single region

### Production Scale
- Geo-replication for multi-region
- Custom partition keys for distribution
- Provisioned throughput or serverless
- Client-side in-memory caching layer
- Connection pooling and retry policies

## Integration Points

### Current
- FastAPI REST API
- Azure Cosmos DB SDK
- Simulated LLM latency

### Future Integrations
```python
# Semantic caching with embeddings
def get_embedding(text: str) -> List[float]:
    """Generate embedding for semantic similarity"""
    return openai.Embedding.create(text)

# LangChain integration
from langchain.cache import CosmosDBCache
cache = CosmosDBCache(cosmos_client, ...)

# Agent-to-Agent communication
class AgentMessage(BaseModel):
    from_agent: str
    to_agent: str
    message: Dict[str, Any]
    timestamp: datetime
```

This architecture provides a solid foundation for a production-ready caching layer while remaining simple enough for portfolio demonstration.

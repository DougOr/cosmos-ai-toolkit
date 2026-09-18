# Azure Cosmos DB Caching Layer Harness - Test Script
# This script demonstrates all the endpoints with PowerShell

$baseUrl = "http://localhost:8001"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Azure Cosmos DB Caching Harness - Test Suite" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Check if server is running
Write-Host "🔍 Checking if server is running..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/health" -Method Get -ErrorAction Stop
    Write-Host "✓ Server is running!" -ForegroundColor Green
    Write-Host "  Database: $($response.database)" -ForegroundColor White
    Write-Host "  Status: $($response.status)" -ForegroundColor White
} catch {
    Write-Host "❌ Server is not running!" -ForegroundColor Red
    Write-Host "  Start the server first: uv run uvicorn main:app --reload" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Test 1: POST /prompt - Cache a new prompt" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$promptData = @{
    prompt_key = "test_prompt_quantum"
    system_prompt = "You are a helpful science tutor"
    user_prompt = "Explain quantum entanglement in simple terms"
    temperature = 0.7
    max_tokens = 500
} | ConvertTo-Json

Write-Host "Sending prompt..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/prompt" -Method Post -Body $promptData -ContentType "application/json"
    Write-Host "✓ Prompt cached successfully!" -ForegroundColor Green
    Write-Host "  Status: $($response.status)" -ForegroundColor White
    Write-Host "  Source: $($response.source)" -ForegroundColor White
    Write-Host "  Latency: $($response.latency_ms)ms" -ForegroundColor White
    Write-Host "  Response snippet: $($response.generated_response.response.content.Substring(0,50))..." -ForegroundColor Cyan
} catch {
    Write-Host "❌ Failed to cache prompt" -ForegroundColor Red
    Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Start-Sleep -Seconds 1

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Test 2: GET /prompt/{prompt_key} - Cache HIT" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Retrieving cached prompt (should be a HIT)..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/prompt/test_prompt_quantum" -Method Get
    Write-Host "✓ Cache HIT!" -ForegroundColor Green
    Write-Host "  Status: $($response.status)" -ForegroundColor White
    Write-Host "  Source: $($response.source)" -ForegroundColor White
    Write-Host "  Latency: $($response.latency_ms)ms" -ForegroundColor White
    Write-Host "  Speedup: ~" + [math]::Round(300 / $response.latency_ms, 1) + "x faster" -ForegroundColor Cyan
} catch {
    Write-Host "❌ Failed to retrieve prompt" -ForegroundColor Red
}

Write-Host ""
Start-Sleep -Seconds 1

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Test 3: GET /prompt/{prompt_key} - Cache MISS" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Retrieving new prompt (should be a MISS)..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/prompt/new_unique_prompt_test" -Method Get
    Write-Host "✓ Cache MISS (auto-generated and cached)!" -ForegroundColor Green
    Write-Host "  Status: $($response.status)" -ForegroundColor White
    Write-Host "  Source: $($response.source)" -ForegroundColor White
    Write-Host "  Latency: $($response.latency_ms)ms" -ForegroundColor White
} catch {
    Write-Host "❌ Failed to retrieve prompt" -ForegroundColor Red
}

Write-Host ""
Start-Sleep -Seconds 1

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Test 4: POST /generic - Store JSON data" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$genericData = @{
    key = "feature_flags_v1"
    data = @{
        new_ui_enabled = $true
        beta_features = @("chat", "analytics", "export")
        user_segment = "beta_testers"
    }
    ttl_seconds = 300
} | ConvertTo-Json -Depth 3

Write-Host "Storing generic JSON data..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/generic" -Method Post -Body $genericData -ContentType "application/json"
    Write-Host "✓ Generic data cached!" -ForegroundColor Green
    Write-Host "  Status: $($response.status)" -ForegroundColor White
    Write-Host "  Key: $($response.key)" -ForegroundColor White
    Write-Host "  Data: $($response.data | ConvertTo-Json -Compress)" -ForegroundColor Cyan
} catch {
    Write-Host "❌ Failed to cache generic data" -ForegroundColor Red
}

Write-Host ""
Start-Sleep -Seconds 1

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Test 5: GET /generic/{key} - Retrieve JSON data" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Retrieving cached generic data..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/generic/feature_flags_v1" -Method Get
    Write-Host "✓ Generic data retrieved!" -ForegroundColor Green
    Write-Host "  Status: $($response.status)" -ForegroundColor White
    Write-Host "  Source: $($response.source)" -ForegroundColor White
    Write-Host "  Beta features: $($response.data.beta_features -join ', ')" -ForegroundColor Cyan
} catch {
    Write-Host "❌ Failed to retrieve generic data" -ForegroundColor Red
}

Write-Host ""
Start-Sleep -Seconds 1

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Test 6: DELETE /generic/{key} - Delete JSON data" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Deleting cached generic data..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/generic/feature_flags_v1" -Method Delete
    Write-Host "✓ Generic data deleted!" -ForegroundColor Green
    Write-Host "  Status: $($response.status)" -ForegroundColor White
    Write-Host "  Key: $($response.key)" -ForegroundColor White
} catch {
    Write-Host "❌ Failed to delete generic data" -ForegroundColor Red
}

Write-Host ""
Start-Sleep -Seconds 1

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Test 7: GET /benchmark - Performance test" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Running benchmark (this will take ~15-20 seconds)..." -ForegroundColor Yellow
Write-Host ""
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/benchmark" -Method Get
    Write-Host "✓ Benchmark complete!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📊 Results:" -ForegroundColor Cyan
    Write-Host "  Cache Misses (50 unique):    $($response.miss_duration)s total ($($response.avg_miss_latency_ms)ms avg)" -ForegroundColor White
    Write-Host "  Cache Hits (50 identical):   $($response.hit_duration)s total ($($response.avg_hit_latency_ms)ms avg)" -ForegroundColor White
    Write-Host "  Speedup Factor:              $($response.speedup_factor)x faster" -ForegroundColor Green
} catch {
    Write-Host "❌ Benchmark failed" -ForegroundColor Red
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "✅ Test Suite Complete!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "📖 Explore more endpoints at: $baseUrl/docs" -ForegroundColor Cyan
Write-Host ""

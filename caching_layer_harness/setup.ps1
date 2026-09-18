# Azure Cosmos DB Caching Layer Harness - Setup Script
# This script helps you set up and run the caching harness on Windows

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Azure Cosmos DB Caching Layer Harness - Setup Assistant" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Check if uv is installed
Write-Host "🔍 Checking for 'uv' package manager..." -ForegroundColor Yellow
$uvInstalled = $null -ne (Get-Command uv -ErrorAction SilentlyContinue)

if (-not $uvInstalled) {
    Write-Host "❌ 'uv' is not installed!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install 'uv' first:" -ForegroundColor Yellow
    Write-Host "1. Open PowerShell as Administrator" -ForegroundColor White
    Write-Host "2. Run: irm https://astral.sh/uv/install.ps1 | iex" -ForegroundColor Cyan
    Write-Host "3. Restart your terminal and run this script again" -ForegroundColor White
    Write-Host ""
    exit 1
}

Write-Host "✓ 'uv' is installed" -ForegroundColor Green
Write-Host ""

# Check if Cosmos DB Emulator is running
Write-Host "🔍 Checking for Azure Cosmos DB Emulator..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "https://localhost:8081/_explorer/index.html" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
    Write-Host "✓ Azure Cosmos DB Emulator is running" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Azure Cosmos DB Emulator may not be running!" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Please ensure the Azure Cosmos DB Emulator is installed and running:" -ForegroundColor Yellow
    Write-Host "1. Download from: https://aka.ms/cosmosdb-emulator" -ForegroundColor Cyan
    Write-Host "2. Run the MSI installer" -ForegroundColor White
    Write-Host "3. Start the emulator from the Start Menu" -ForegroundColor White
    Write-Host ""
    $continue = Read-Host "Continue anyway? (y/n)"
    if ($continue -ne "y") {
        exit 1
    }
}

Write-Host ""

# Initialize uv project
Write-Host "📦 Initializing uv project..." -ForegroundColor Yellow
if (Test-Path "pyproject.toml") {
    Write-Host "✓ Project already initialized (pyproject.toml exists)" -ForegroundColor Green
} else {
    uv init --no-readme
    Write-Host "✓ Project initialized" -ForegroundColor Green
}

Write-Host ""

# Install dependencies
Write-Host "📥 Installing dependencies with 'uv add'..." -ForegroundColor Yellow
$packages = @("fastapi", "uvicorn", "azure-cosmos", "python-dotenv", "pydantic")

foreach ($package in $packages) {
    Write-Host "  Adding $package..." -ForegroundColor Cyan
    uv add $package --quiet
}

Write-Host ""
Write-Host "✓ Dependencies installed" -ForegroundColor Green
Write-Host ""

# Add dev dependency
Write-Host "📥 Adding dev dependency (httpx)..." -ForegroundColor Yellow
uv add --dev httpx --quiet
Write-Host "✓ Dev dependencies installed" -ForegroundColor Green
Write-Host ""

# Verify .env file
Write-Host "🔍 Checking .env file..." -ForegroundColor Yellow
if (Test-Path ".env") {
    Write-Host "✓ .env file exists" -ForegroundColor Green
} else {
    Write-Host "⚠️  .env file not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "The .env file should contain:" -ForegroundColor Yellow
    Write-Host @"
COSMOS_ENDPOINT=https://localhost:8081/
COSMOS_KEY=C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw==
DATABASE_NAME=PromptHarnessDB
PROMPT_CONTAINER=PromptCache
GENERIC_CONTAINER=GenericCache
DEFAULT_TTL=120
SIMULATED_LATENCY_SECONDS=0.3
"@ -ForegroundColor White
    Write-Host ""
    exit 1
}

Write-Host ""

# Success message
Write-Host "============================================================" -ForegroundColor Green
Write-Host "✅ Setup Complete!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "To run the caching harness:" -ForegroundColor Yellow
Write-Host "  uv run uvicorn caching_layer_harness:app --reload" -ForegroundColor Cyan
Write-Host ""
Write-Host "Then visit:" -ForegroundColor Yellow
Write-Host "  📖 Swagger UI: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "  🏥 Health Check: http://localhost:8000/health" -ForegroundColor Cyan
Write-Host "  📊 Benchmark: http://localhost:8000/benchmark" -ForegroundColor Cyan
Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""

# Ask if user wants to run the server now
$runNow = Read-Host "Run the server now? (y/n)"
if ($runNow -eq "y") {
    Write-Host ""
    Write-Host "🚀 Starting server..." -ForegroundColor Green
    Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
    Write-Host ""
    uv run uvicorn caching_layer_harness:app --reload
}

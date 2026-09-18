"""
Script to delete PromptHarnessDB and create CacheHarnessDB with correct containers
"""
import os
from azure.cosmos import CosmosClient, PartitionKey
from dotenv import load_dotenv

load_dotenv()

COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT", "https://localhost:8081/")
COSMOS_KEY = os.getenv("COSMOS_KEY", "C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw==")

OLD_DATABASE_NAME = "PromptHarnessDB"
NEW_DATABASE_NAME = "CacheHarnessDB"
DEFAULT_TTL = 120

# Initialize Cosmos DB client
cosmos_client = CosmosClient(COSMOS_ENDPOINT, credential=COSMOS_KEY, connection_verify=False)

print("🗑️  RESETTING DATABASE STRUCTURE")
print("=" * 70)

# Delete old database
print(f"🗑️  Deleting old database: {OLD_DATABASE_NAME}")
try:
    cosmos_client.delete_database(OLD_DATABASE_NAME)
    print(f"  ✅ Deleted database: {OLD_DATABASE_NAME}")
except Exception as e:
    print(f"  ⚠️  Could not delete {OLD_DATABASE_NAME}: {e}")

# Create new database
print(f"\n🆕 Creating new database: {NEW_DATABASE_NAME}")
try:
    database = cosmos_client.create_database(NEW_DATABASE_NAME)
    print(f"  ✅ Created database: {NEW_DATABASE_NAME}")
except Exception as e:
    print(f"  ⚠️  Could not create {NEW_DATABASE_NAME}: {e}")
    database = cosmos_client.get_database_client(NEW_DATABASE_NAME)

# Create containers with correct configuration
print(f"\n🆕 Creating containers in {NEW_DATABASE_NAME}...")

# Create IntelligentCache container
try:
    intelligent_cache_container = database.create_container(
        id="IntelligentCache",
        partition_key=PartitionKey(path="/cache_partition"),
        default_ttl=DEFAULT_TTL
    )
    print(f"  ✅ Created container: IntelligentCache (partition: /cache_partition)")
except Exception as e:
    print(f"  ⚠️  Could not create IntelligentCache: {e}")

# Create GenericCache container  
try:
    generic_cache_container = database.create_container(
        id="GenericCache",
        partition_key=PartitionKey(path="/generic_partition"),
        default_ttl=DEFAULT_TTL
    )
    print(f"  ✅ Created container: GenericCache (partition: /generic_partition)")
except Exception as e:
    print(f"  ⚠️  Could not create GenericCache: {e}")

print("\n" + "=" * 70)
print("✅ Database reset complete!")
print("\n📋 New database structure:")
print(f"  📦 Database: {NEW_DATABASE_NAME}")
print(f"    🧠 IntelligentCache - partition key: /cache_partition")
print(f"    🔧 GenericCache - partition key: /generic_partition")
print("=" * 70)

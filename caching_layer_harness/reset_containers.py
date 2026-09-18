"""
Script to delete old containers and create new ones with correct names and partition keys
"""
import os
from azure.cosmos import CosmosClient, PartitionKey
from dotenv import load_dotenv

load_dotenv()

COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT", "https://localhost:8081/")
COSMOS_KEY = os.getenv("COSMOS_KEY", "C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw==")

DATABASE_NAME = "PromptHarnessDB"
DEFAULT_TTL = 120

# Initialize Cosmos DB client
cosmos_client = CosmosClient(COSMOS_ENDPOINT, credential=COSMOS_KEY, connection_verify=False)

print("🗑️  RESETTING COSMOS DB CONTAINERS")
print("=" * 70)

# Get database
database = cosmos_client.get_database_client(DATABASE_NAME)
print(f"📦 Working with database: {DATABASE_NAME}")

# List existing containers
containers = list(database.list_containers())
print(f"🔍 Found {len(containers)} existing container(s):")
for container in containers:
    container_name = container if isinstance(container, str) else container.get('id', 'Unknown')
    print(f"  - {container_name}")

# Delete old containers
print("\n🗑️  Deleting old containers...")
containers_to_delete = ["PromptCache", "GenericCache", "IntelligentCache"]

for container_name in containers_to_delete:
    try:
        database.delete_container(container_name)
        print(f"  ✅ Deleted container: {container_name}")
    except Exception as e:
        print(f"  ⚠️  Could not delete {container_name}: {e}")

# Create new containers with correct names and partition keys
print("\n🆕 Creating new containers with correct configuration...")

# Create IntelligentCache (for AI data)
try:
    intelligent_cache_container = database.create_container(
        id="IntelligentCache",
        partition_key=PartitionKey(path="/cache_partition"),
        default_ttl=DEFAULT_TTL
    )
    print(f"  ✅ Created container: IntelligentCache (partition: /cache_partition)")
except Exception as e:
    print(f"  ⚠️  Could not create IntelligentCache: {e}")

# Create GenericCache (for generic JSON data)  
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
print("✅ Container reset complete!")
print("\n📋 New container structure:")
print(f"  🧠 IntelligentCache - partition key: /cache_partition")
print(f"  🔧 GenericCache - partition key: /generic_partition")
print("=" * 70)

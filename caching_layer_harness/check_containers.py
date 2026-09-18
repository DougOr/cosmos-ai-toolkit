"""
Script to check existing containers in Azure Cosmos DB Emulator
"""
import os
from azure.cosmos import CosmosClient
from dotenv import load_dotenv

load_dotenv()

COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT", "https://localhost:8081/")
COSMOS_KEY = os.getenv("COSMOS_KEY", "C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw==")

# Initialize Cosmos DB client
cosmos_client = CosmosClient(COSMOS_ENDPOINT, credential=COSMOS_KEY, connection_verify=False)

print("🔍 Checking existing databases and containers in Azure Cosmos DB Emulator...")
print("=" * 70)

# List all databases
databases = list(cosmos_client.list_databases())
print(f"📊 Found {len(databases)} database(s):")
for db in databases:
    db_name = db if isinstance(db, str) else db.get('id', 'Unknown')
    print(f"  - {db_name}")

print("\n" + "=" * 70)
print("🔍 Checking containers in each database...")
print("=" * 70)

for db in databases:
    db_name = db if isinstance(db, str) else db.get('id', 'Unknown')
    database_client = cosmos_client.get_database_client(db_name)
    containers = list(database_client.list_containers())
    print(f"\n📦 Database '{db_name}' has {len(containers)} container(s):")
    
    for container in containers:
        container_name = container if isinstance(container, str) else container.get('id', 'Unknown')
        container_client = database_client.get_container_client(container_name)
        try:
            container_info = container_client.read()
            print(f"  - 📄 Container: {container_name}")
            print(f"     Partition Key: {container_info['partitionKey']['paths']}")
            print(f"     Default TTL: {container_info.get('defaultTtl', 'None')}")
        except Exception as e:
            print(f"  - 📄 Container: {container_name} (Error reading info: {e})")

print("\n" + "=" * 70)
print("✅ Container check complete!")

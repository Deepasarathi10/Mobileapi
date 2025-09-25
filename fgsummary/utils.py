from motor.motor_asyncio import AsyncIOMotorClient
from motor.motor_asyncio import AsyncIOMotorCollection

# Create async Mongo client
client = AsyncIOMotorClient("mongodb://admin:YenE580nOOUE6cDhQERP@194.233.78.90:27017/admin?appName=mongosh+2.1.1&authSource=admin&authMechanism=SCRAM-SHA-256&replicaSet=yenerp-cluster")
db = client["reactfluttertest"]  # Database name

def get_sfgtofgdata_collection() -> AsyncIOMotorCollection:
    return db["fg_summary"]

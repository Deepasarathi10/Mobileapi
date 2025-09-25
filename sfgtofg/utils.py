from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection

# Create async client
client = AsyncIOMotorClient("mongodb://admin:YenE580nOOUE6cDhQERP@194.233.78.90:27017/admin?appName=mongosh+2.1.1&authSource=admin&authMechanism=SCRAM-SHA-256&replicaSet=yenerp-cluster")
db = client["reactfluttertest"]  # Database name

def get_conversion_details_collection() -> AsyncIOMotorCollection:
    return db["conversion_details"]

def get_fgitems_collection() -> AsyncIOMotorCollection:
    return db["fg_items"]


from motor.motor_asyncio import AsyncIOMotorClient

# Create a global client instance (recommended instead of reconnecting every call)
client = AsyncIOMotorClient("mongodb://admin:YenE580nOOUE6cDhQERP@194.233.78.90:27017/admin?appName=mongosh+2.1.1&authSource=admin&authMechanism=SCRAM-SHA-256&replicaSet=yenerp-cluster")
db = client["reactfluttertest"]  # Adjust database name as per your MongoDB setup

def get_sfgItems_collection():
    return db["sfgItems"]


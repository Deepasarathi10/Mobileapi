from motor.motor_asyncio import AsyncIOMotorClient

# Single MongoDB client for all requests
client = AsyncIOMotorClient("mongodb://admin:YenE580nOOUE6cDhQERP@194.233.78.90:27017/admin?appName=mongosh+2.1.1&authSource=admin&authMechanism=SCRAM-SHA-256&replicaSet=yenerp-cluster")
db = client["reactfluttertest"]

def get_collection(name: str):
    return db[name]

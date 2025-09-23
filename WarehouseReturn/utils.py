from motor.motor_asyncio import AsyncIOMotorClient

# MongoDB connection (Motor async client)
client = AsyncIOMotorClient("mongodb://admin:YenE580nOOUE6cDhQERP@194.233.78.90:27017/admin?appName=mongosh+2.1.1&authSource=admin&authMechanism=SCRAM-SHA-256&replicaSet=yenerp-cluster")
db = client["reactfluttertest"]

# Async getter for warehouseReturn collection
def get_warehouse_return_collection():
    return db["warehouseReturn"]

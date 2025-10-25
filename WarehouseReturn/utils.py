from motor.motor_asyncio import AsyncIOMotorClient

# MongoDB connection (Motor async client)
client = AsyncIOMotorClient("mongodb://localhost:27017/")
db = client["reactfluttertest"]

# Async getter for warehouseReturn collection
def get_warehouse_return_collection():
    return db["warehouseReturn"]

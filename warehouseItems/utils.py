from motor.motor_asyncio import AsyncIOMotorClient

# Single MongoDB client for all requests
client = AsyncIOMotorClient("mongodb://localhost:27017")
db = client["warehouseitems"]

def get_collection(name: str):
    return db[name]

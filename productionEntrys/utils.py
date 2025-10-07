from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

# MongoDB connection and collection getter for item groups
def get_productionEntry_collection():
    client = AsyncIOMotorClient("mongodb://localhost:27017/")
    db = client["admin"]  
    return db['productionEntry']  
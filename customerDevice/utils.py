from pymongo import MongoClient
from bson import ObjectId
# utils.py
from pymongo import ReturnDocument
# MongoDB connection and collection getter for item groups
def get_customerDevice_collection():
    client = MongoClient("mongodb://admin:YenE580nOOUE6cDhQERP@194.233.78.90:27017/admin?appName=mongosh+2.1.1&authSource=admin&authMechanism=SCRAM-SHA-256&replicaSet=yenerp-cluster")
    db = client["reactfluttertest"]  # Adjust database name as per your MongoDB setup
    return db['customerDevice']  



async def next_counter(db, name: str) -> int:
    """Atomically bump and return the counter called *name*."""
    doc = await db.counters.find_one_and_update(
        {"_id": name},
        {"$inc": {"value": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,   # give the *new* number
    )
    return doc["value"]          # ← plain integer (1, 2, 3…)


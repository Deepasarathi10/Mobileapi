from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = "mongodb://admin:YenE580nOOUE6cDhQERP@194.233.78.90:27017/admin?appName=mongosh+2.1.1&authSource=admin&authMechanism=SCRAM-SHA-256&replicaSet=yenerp-cluster"
DB_NAME = "reactfluttertest"

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

def get_collection(name: str):
    if name == "reasons":
        return db["reasons"]
    else:
        raise HTTPException(status_code=400, detail="Invalid collection name")

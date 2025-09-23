from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.collection import Collection
import re
import math
from datetime import datetime
from bson import ObjectId
from fastapi import APIRouter, HTTPException

router = APIRouter()

# ✅ Use `AsyncIOMotorClient` instead of `MongoClient`
async def get_BirthdayCakeItem_collection():
    client = AsyncIOMotorClient(
        "mongodb://admin:YenE580nOOUE6cDhQERP@194.233.78.90:27017/admin?authSource=admin&authMechanism=SCRAM-SHA-256",
        serverSelectionTimeoutMS=60000  # 60 seconds timeout
    )
    db = client["reactfluttertest"]
    return db["birthdaycakeitem"]
    

# Utility function to convert data to strings or empty strings
def convert_to_string_or_emptys(data):
    if isinstance(data, list):
        return [convert_to_string_or_emptys(value) for value in data]
    elif isinstance(data, dict):
        return {key: convert_to_string_or_emptys(value) for key, value in data.items()}
    elif isinstance(data, (int, float)):
        return str(data)
    else:
        return str(data) if data is not None and data != "" else None

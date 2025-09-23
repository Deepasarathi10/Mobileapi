from typing import List
from fastapi import APIRouter, HTTPException,status
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from .models import orderType, orderTypePost

router = APIRouter()
client = AsyncIOMotorClient("mongodb://admin:YenE580nOOUE6cDhQERP@194.233.78.90:27017/admin?appName=mongosh+2.1.1&authSource=admin&authMechanism=SCRAM-SHA-256&replicaSet=yenerp-cluster")
db = client["reactfluttertest"]
order_type_collection = db["orderType"]

async def get_next_counter_value():
    counter_collection = db["counters"]
    counter = await counter_collection.find_one_and_update(
        {"_id": "orderTypeId"},
        {"$inc": {"sequence_value": 1}},
        upsert=True,
        return_document=True
    )
    return counter["sequence_value"]

async def reset_counter():
    counter_collection = db["counters"]
    await counter_collection.update_one(
        {"_id": "orderTypeId"},
        {"$set": {"sequence_value": 0}},
        upsert=True
    )

def generate_random_id(counter_value):
    return f"OT{counter_value:03d}"

@router.post("/", response_model=str,status_code=status.HTTP_201_CREATED)
async def create_orderType(order_type: orderTypePost):
    if await order_type_collection.count_documents({}) == 0:
        await reset_counter()

    counter_value = await get_next_counter_value()
    random_id = generate_random_id(counter_value)

    new_order_type_data = order_type.dict()
    new_order_type_data['randomId'] = random_id

    result = await order_type_collection.insert_one(new_order_type_data)
    return str(result.inserted_id)

@router.get("/", response_model=List[orderType])
async def get_all_orderType():
    order_types = await order_type_collection.find().to_list(None)
    return [orderType(**doc, orderTypeId=str(doc["_id"])) for doc in order_types]

@router.get("/{order_type_id}", response_model=orderType)
async def get_orderType_by_id(order_type_id: str):
    doc = await order_type_collection.find_one({"_id": ObjectId(order_type_id)})
    if doc:
        return orderType(**doc, orderTypeId=str(doc["_id"]))
    else:
        raise HTTPException(status_code=404, detail="orderType not found")

@router.put("/{order_type_id}", response_model=dict)
async def update_orderType(order_type_id: str, order_type: orderTypePost):
    update_data = order_type.dict(exclude_unset=True)
    result = await order_type_collection.update_one(
        {"_id": ObjectId(order_type_id)}, {"$set": update_data}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="orderType not found")
    return {"message": "orderType updated successfully"}

@router.patch("/{order_type_id}", response_model=orderType)
async def patch_orderType(order_type_id: str, order_type_patch: orderTypePost):
    existing_doc = await order_type_collection.find_one({"_id": ObjectId(order_type_id)})
    if not existing_doc:
        raise HTTPException(status_code=404, detail="orderType not found")

    update_data = {key: value for key, value in order_type_patch.dict(exclude_unset=True).items() if value is not None}
    result = await order_type_collection.update_one({"_id": ObjectId(order_type_id)}, {"$set": update_data})
    if result.modified_count == 0:
        raise HTTPException(status_code=500, detail="Failed to update orderType")

    updated_doc = await order_type_collection.find_one({"_id": ObjectId(order_type_id)})
    return orderType(**updated_doc, orderTypeId=str(updated_doc["_id"]))

@router.delete("/{order_type_id}", response_model=dict)
async def delete_orderType(order_type_id: str):
    result = await order_type_collection.delete_one({"_id": ObjectId(order_type_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="orderType not found")
    return {"message": "orderType deleted successfully"}

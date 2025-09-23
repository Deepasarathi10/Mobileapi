

from typing import List
from fastapi import APIRouter, HTTPException
from bson import ObjectId
from .models import DeviceCode, DeviceCodePost, DeviceCodePatch
from .utils import get_DeviceCode_collection

router = APIRouter()
item_group_counter = 0

def get_next_counter_value():
    counter_collection = get_DeviceCode_collection().database["counters"]
    counter = counter_collection.find_one_and_update(
        {"_id": "deviceCodeId"},
        {"$inc": {"sequence_value": 1}},
        upsert=True,
        return_document=True
    )
    return counter["sequence_value"]

def reset_counter():
    counter_collection = get_DeviceCode_collection().database["counters"]
    counter_collection.update_one(
        {"_id": "deviceCodeId"},
        {"$set": {"sequence_value": 0}},
        upsert=True
    )

def generate_random_id():
    counter_value = get_next_counter_value()
    return f"DC{counter_value:03d}"

@router.post("/", response_model=str)
async def create_DeviceCode(DeviceCode: DeviceCodePost):
    # Check if the collection is empty and reset counter if needed
    if get_DeviceCode_collection().count_documents({}) == 0:
        reset_counter()

    # Generate randomId
    random_id = generate_random_id()

    # Prepare data including randomId
    new_DeviceCode_data = DeviceCode.model_dump()
    new_DeviceCode_data['randomId'] = random_id

    # Insert into MongoDB
    result = get_DeviceCode_collection().insert_one(new_DeviceCode_data)
    return str(result.inserted_id)

@router.get("/", response_model=List[DeviceCode])
async def get_all_deviceCode():
    deviceCodes = list(get_DeviceCode_collection().find())
    formatted_deviceCode = [
        DeviceCode(**{**deviceCode, "deviceCodeId": str(deviceCode["_id"])}) for deviceCode in deviceCodes
    ]
    return formatted_deviceCode

@router.get("/{DeviceCode_id}", response_model=DeviceCode)
async def get_DeviceCode_by_id(DeviceCode_id: str):
    try:
        deviceCode = get_DeviceCode_collection().find_one({"_id": ObjectId(DeviceCode_id)})
    except:
        raise HTTPException(status_code=400, detail="Invalid DeviceCode ID")

    if deviceCode:
        deviceCode["deviceCodeId"] = str(deviceCode["_id"])
        return DeviceCode(**deviceCode)
    else:
        raise HTTPException(status_code=404, detail="DeviceCode not found")


@router.patch("/{DeviceCode_id}")
async def patch_DeviceCode(DeviceCode_id: str, DeviceCode_patch: DeviceCodePatch):
    try:
        existing_DeviceCode = get_DeviceCode_collection().find_one({"_id": ObjectId(DeviceCode_id)})
    except:
        raise HTTPException(status_code=400, detail="Invalid DeviceCode ID")

    if not existing_DeviceCode:
        raise HTTPException(status_code=404, detail="DeviceCode not found")

    updated_fields = {key: value for key, value in DeviceCode_patch.dict(exclude_unset=True).items() if value is not None}
    if updated_fields:
        result = get_DeviceCode_collection().update_one({"_id": ObjectId(DeviceCode_id)}, {"$set": updated_fields})
        if result.modified_count == 0:
            raise HTTPException(status_code=500, detail="Failed to update DeviceCode")

    updated_DeviceCode = get_DeviceCode_collection().find_one({"_id": ObjectId(DeviceCode_id)})
    updated_DeviceCode["_id"] = str(updated_DeviceCode["_id"])
    return updated_DeviceCode

@router.delete("/{DeviceCode_id}")
async def delete_DeviceCode(DeviceCode_id: str):
    try:
        result = get_DeviceCode_collection().delete_one({"_id": ObjectId(DeviceCode_id)})
    except:
        raise HTTPException(status_code=400, detail="Invalid DeviceCode ID")

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="DeviceCode not found")
    return {"message": "DeviceCode deleted successfully"}

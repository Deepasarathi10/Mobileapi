from fastapi import APIRouter, HTTPException, status
from typing import List, Optional
from bson import ObjectId
from .models import Hold, HoldPost
from .utils import get_hold_collection
from datetime import datetime

router = APIRouter()

# Get the collection
hold_collection = get_hold_collection('holds')

@router.post("/", response_model=str)
async def create_hold(hold: HoldPost):
    new_hold = hold.model_dump()
    result = await hold_collection.insert_one(new_hold)
    return str(result.inserted_id)

def convert_to_string_or_empty(data):
    if isinstance(data, list):
        return [str(value) if not isinstance(value, int) else str(value) for value in data]
    else:
        return str(data) if not isinstance(data, int) else str(data)

@router.get("/", response_model=List[Hold])
async def get_all_hold():
    holds = await hold_collection.find().to_list(None)
    return [Hold(holdId=str(hold.pop("_id")), **{key: convert_to_string_or_empty(value) for key, value in hold.items()}) for hold in holds]

@router.get("/{hold_id}", response_model=Hold)
async def get_hold_by_id(hold_id: str):
    hold = await hold_collection.find_one({"_id": ObjectId(hold_id)})
    if hold:
        hold["holdId"] = str(hold.pop("_id"))
        return Hold(**{key: convert_to_string_or_empty(value) for key, value in hold.items()})
    else:
        raise HTTPException(status_code=404, detail="Hold not found")

@router.put("/{hold_id}")
async def update_hold(hold_id: str, hold: HoldPost):
    updated_hold = hold.model_dump(exclude_unset=True)
    result = await hold_collection.update_one(
        {"_id": ObjectId(hold_id)}, {"$set": updated_hold}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Hold not found")
    return {"message": "Hold updated successfully"}

@router.patch("/{hold_id}")
async def update_hold_partial(hold_id: str, hold_patch: HoldPost):
    existing_hold = await hold_collection.find_one({"_id": ObjectId(hold_id)})
    if not existing_hold:
        raise HTTPException(status_code=404, detail="Hold not found")

    updated_fields = hold_patch.model_dump(exclude_unset=True)
    if updated_fields:
        result = await hold_collection.update_one(
            {"_id": ObjectId(hold_id)},
            {"$set": updated_fields}
        )
        if result.modified_count == 0:
            raise HTTPException(status_code=500, detail="Failed to update hold")

    # Fetch the updated hold
    updated_hold = await hold_collection.find_one({"_id": ObjectId(hold_id)})
    updated_hold["holdId"] = str(updated_hold.pop("_id"))
    return updated_hold

@router.delete("/{hold_id}")
async def delete_hold(hold_id: str):
    result = await hold_collection.delete_one({"_id": ObjectId(hold_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Hold not found")
    return {"message": "Hold deleted successfully"}

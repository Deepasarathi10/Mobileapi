from typing import List
from fastapi import APIRouter, HTTPException
from bson import ObjectId
from .models import asset, assetPost
from .utils import get_asset_collection, convert_to_string_or_none

router = APIRouter()

def get_next_counter_value():
    counter_collection = get_asset_collection().database["counters"]
    counter = counter_collection.find_one_and_update(
        {"_id": "assetId"},
        {"$inc": {"sequence_value": 1}},
        upsert=True,
        return_document=True
    )
    return counter["sequence_value"]

def reset_counter():
    counter_collection = get_asset_collection().database["counters"]
    counter_collection.update_one(
        {"_id": "assetId"},
        {"$set": {"sequence_value": 0}},
        upsert=True
    )

def generate_random_id():
    counter_value = get_next_counter_value()
    return f"Asset{counter_value:03d}"

@router.post("/", response_model=str)
async def create_asset(asset: assetPost):
    # Check if the collection is empty
    if get_asset_collection().count_documents({}) == 0:
        reset_counter()

    # Generate randomId
    random_id = generate_random_id()

    # Prepare data including randomId
    new_asset_data = asset.dict()
    new_asset_data['randomId'] = random_id

    # Insert into MongoDB
    result = get_asset_collection().insert_one(new_asset_data)
    return str(result.inserted_id)

@router.get("/", response_model=List[asset])
async def get_all_asset():
    try:
        itemasset = list(get_asset_collection().find())
        formatted_asset = []
        for assets in itemasset:
            for key, value in assets.items():
                assets[key] = convert_to_string_or_none(value)
            assets["assetId"] = str(assets["_id"])
            formatted_asset.append(asset(**assets))
        return formatted_asset
    except Exception as e:
        print(f"Error fetching assets: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/{asset_id}", response_model=asset)
async def get_asset_by_id(asset_id: str):
    try:
        asset_data = get_asset_collection().find_one({"_id": ObjectId(asset_id)})
        if asset_data:
            asset_data["assetId"] = str(asset_data["_id"])
            return asset(**asset_data)
        else:
            raise HTTPException(status_code=404, detail="asset not found")
    except Exception as e:
        print(f"Error fetching asset by ID: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.put("/{asset_id}")
async def update_asset(asset_id: str, asset: assetPost):
    updated_asset = asset.dict(exclude_unset=True)  # exclude_unset=True prevents sending None values to MongoDB
    result = get_asset_collection().update_one({"_id": ObjectId(asset_id)}, {"$set": updated_asset})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="asset not found")
    return {"message": "asset updated successfully"}

@router.patch("/{asset_id}")
async def patch_asset(asset_id: str, asset_patch: assetPost):
    existing_asset = get_asset_collection().find_one({"_id": ObjectId(asset_id)})
    if not existing_asset:
        raise HTTPException(status_code=404, detail="asset not found")

    updated_fields = {key: value for key, value in asset_patch.dict(exclude_unset=True).items() if value is not None}
    if updated_fields:
        result = get_asset_collection().update_one({"_id": ObjectId(asset_id)}, {"$set": updated_fields})
        if result.modified_count == 0:
            raise HTTPException(status_code=500, detail="Failed to update asset")

    updated_asset = get_asset_collection().find_one({"_id": ObjectId(asset_id)})
    updated_asset["_id"] = str(updated_asset["_id"])
    return updated_asset

# @router.delete("/{asset_id}")
# async def delete_asset(asset_id: str):
#     result = get_asset_collection().delete_one({"_id": ObjectId(asset_id)})
#     if result.deleted_count == 0:
#         raise HTTPException(status_code=404, detail="asset not found")
#     return {"message": "asset deleted successfully"}

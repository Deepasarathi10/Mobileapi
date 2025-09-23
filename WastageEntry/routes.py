from typing import List
from fastapi import APIRouter, HTTPException
from bson import ObjectId
from .models import WastageEntry, WastageEntryPost
from .utils import get_wastage_entry_collection

router = APIRouter()

@router.post("/", response_model=str)
async def create_wastage_entry(wastage_entry: WastageEntryPost):
    # Prepare data for insertion
    new_wastage_entry_data = wastage_entry.dict()

    # Insert into MongoDB
    result = await get_wastage_entry_collection().insert_one(new_wastage_entry_data)
    return str(result.inserted_id)

@router.get("/", response_model=List[WastageEntry])
async def get_all_wastage_entries():
    collection = get_wastage_entry_collection()

    # ✅ correct with Motor:
    cursor = collection.find()
    wastage_entries = await cursor.to_list(length=None)

    formatted_wastage_entries = []
    for entry in wastage_entries:
        entry["wastageId"] = str(entry["_id"])
        del entry["_id"]   # important, because ObjectId is not JSON serializable
        formatted_wastage_entries.append(WastageEntry(**entry))

    return formatted_wastage_entries


@router.get("/{wastage_entry_id}", response_model=WastageEntry)
async def get_warehouse_return_by_id(wastage_entry_id: str):
    entry = await get_wastage_entry_collection().find_one({"_id": ObjectId(wastage_entry_id)})
    if not entry:
        raise HTTPException(status_code=404, detail="wastage not found")

    entry["wastageId"] = str(entry["_id"])
    return WastageEntry(**entry)

@router.put("/{wastage_entry_id}")
async def update_wastage_entry(wastage_entry_id: str, wastage_entry: WastageEntryPost):
    updated_data = wastage_entry.dict(exclude_unset=True)
    result = await get_wastage_entry_collection().update_one(
        {"_id": ObjectId(wastage_entry_id)},
        {"$set": updated_data}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="wastage not found")

    return {"message": "wastage updated successfully"}

@router.patch("/{wastage_entry_id}")
async def patch_wastage_entry(wastage_entry_id: str, wastage_entry_patch: WastageEntryPost):
    collection = get_wastage_entry_collection()
    existing_entry = await collection.find_one({"_id": ObjectId(wastage_entry_id)})
    if not existing_entry:
        raise HTTPException(status_code=404, detail="wastage not found")

    updated_fields = {k: v for k, v in wastage_entry_patch.dict(exclude_unset=True).items() if v is not None}
    if updated_fields:
        result = await collection.update_one({"_id": ObjectId(wastage_entry_id)}, {"$set": updated_fields})
        if result.modified_count == 0:
            raise HTTPException(status_code=500, detail="Failed to update wastage return")

    updated_entry = await collection.find_one({"_id": ObjectId(wastage_entry_id)})
    updated_entry["wastageId"] = str(updated_entry["_id"])
    return updated_entry

@router.delete("/{wastage_entry_id}")
async def delete_wastage_entry(wastage_entry_id: str):
    result = await get_wastage_entry_collection().delete_one({"_id": ObjectId(wastage_entry_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Wastage entry not found")
    return {"message": "Wastage entry deleted successfully"}

from typing import List
from fastapi import APIRouter, HTTPException
from bson import ObjectId
from pymongo import DESCENDING
from datetime import datetime
from .models import WastageEntry, WastageEntryPost
from .utils import get_wastage_entry_collection

router = APIRouter()

# ------------------- CREATE -------------------
@router.post("/", response_model=WastageEntry)
async def create_wastage_entry(wastage_entry: WastageEntryPost):
    coll = get_wastage_entry_collection()

    # Get last inserted document (most recent) by _id
    last_doc = await coll.find_one(
        {"wastageEntryNumber": {"$exists": True}},
        sort=[("_id", DESCENDING)]
    )

    if last_doc and last_doc.get("wastageEntryNumber"):
        try:
            last_number = int(last_doc["wastageEntryNumber"][2:])  # skip "WE"
        except:
            last_number = 0
    else:
        last_number = 0

    next_number = last_number + 1
    wastage_entry_number = f"WE{str(next_number).zfill(4)}"

    # Prepare new document
    new_wastage = wastage_entry.dict()
    new_wastage["wastageEntryNumber"] = wastage_entry_number
    new_wastage["date"] = new_wastage.get("date", datetime.utcnow())

    # Insert into MongoDB
    result = await coll.insert_one(new_wastage)
    new_wastage["wastageId"] = str(result.inserted_id)

    return WastageEntry(**new_wastage)



# ------------------- GET ALL -------------------
@router.get("/", response_model=List[WastageEntry])
async def get_all_wastage_entries():
    coll = get_wastage_entry_collection()
    cursor = coll.find().sort("date", DESCENDING)
    entries = await cursor.to_list(length=None)

    formatted_entries = []
    for entry in entries:
        entry["wastageId"] = str(entry["_id"])
        del entry["_id"]
        formatted_entries.append(WastageEntry(**entry))

    return formatted_entries


# ------------------- GET BY ID -------------------
@router.get("/{wastage_entry_id}", response_model=WastageEntry)
async def get_wastage_entry_by_id(wastage_entry_id: str):
    coll = get_wastage_entry_collection()
    entry = await coll.find_one({"_id": ObjectId(wastage_entry_id)})

    if not entry:
        raise HTTPException(status_code=404, detail="Wastage entry not found")

    entry["wastageId"] = str(entry["_id"])
    return WastageEntry(**entry)


# ------------------- UPDATE (PUT) -------------------
@router.put("/{wastage_entry_id}")
async def update_wastage_entry(wastage_entry_id: str, wastage_entry: WastageEntryPost):
    coll = get_wastage_entry_collection()
    updated_data = wastage_entry.dict(exclude_unset=True)

    result = await coll.update_one(
        {"_id": ObjectId(wastage_entry_id)},
        {"$set": updated_data}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Wastage entry not found")

    return {"message": "Wastage entry updated successfully"}


# ------------------- PATCH -------------------
@router.patch("/{wastage_entry_id}", response_model=WastageEntry)
async def patch_wastage_entry(wastage_entry_id: str, wastage_entry_patch: WastageEntryPost):
    coll = get_wastage_entry_collection()
    existing_entry = await coll.find_one({"_id": ObjectId(wastage_entry_id)})

    if not existing_entry:
        raise HTTPException(status_code=404, detail="Wastage entry not found")

    updated_fields = {k: v for k, v in wastage_entry_patch.dict(exclude_unset=True).items() if v is not None}

    if updated_fields:
        result = await coll.update_one({"_id": ObjectId(wastage_entry_id)}, {"$set": updated_fields})
        if result.modified_count == 0:
            raise HTTPException(status_code=500, detail="Failed to update wastage entry")

    updated_entry = await coll.find_one({"_id": ObjectId(wastage_entry_id)})
    updated_entry["wastageId"] = str(updated_entry["_id"])

    return WastageEntry(**updated_entry)


# ------------------- DELETE -------------------
@router.delete("/{wastage_entry_id}")
async def delete_wastage_entry(wastage_entry_id: str):
    coll = get_wastage_entry_collection()
    result = await coll.delete_one({"_id": ObjectId(wastage_entry_id)})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Wastage entry not found")

    return {"message": "Wastage entry deleted successfully"}

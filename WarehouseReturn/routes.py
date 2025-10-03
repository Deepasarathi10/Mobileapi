from datetime import datetime
from typing import List
from fastapi import APIRouter, HTTPException
from bson import ObjectId
from pymongo import DESCENDING
from .models import WarehouseReturn, WarehouseReturnPost
from .utils import get_warehouse_return_collection

router = APIRouter()

# ------------------- CREATE -------------------
@router.post("/", response_model=WarehouseReturn)
async def create_warehouse_return(warehouse_return: WarehouseReturnPost):
    coll = get_warehouse_return_collection()

    # Get last inserted document (most recent) by _id
    last_doc = await coll.find_one(
        {"warehouseReturnNumber": {"$exists": True}},
        sort=[("_id", DESCENDING)]
    )

    if last_doc and last_doc.get("warehouseReturnNumber"):
        try:
            last_number = int(last_doc["warehouseReturnNumber"][2:])  # skip "WE"
        except:
            last_number = 0
    else:
        last_number = 0

    next_number = last_number + 1
    warehouse_return_number = f"RW{str(next_number).zfill(4)}"

    # Prepare new document
    new_return = warehouse_return.dict()
    new_return["warehouseReturnNumber"] = warehouse_return_number
    new_return["date"] = new_return.get("date", datetime.utcnow())

    # Insert into MongoDB
    result = await coll.insert_one(new_return)
    new_return["warehouseReturnId"] = str(result.inserted_id)

    return WarehouseReturn(**new_return)



# ------------------- GET ALL -------------------
@router.get("/", response_model=List[WarehouseReturn])
async def get_all_wastage_entries():
    coll = get_warehouse_return_collection()
    cursor = coll.find().sort("date", DESCENDING)
    entries = await cursor.to_list(length=None)

    formatted_entries = []
    for entry in entries:
        entry["warehouseReturnId"] = str(entry["_id"])
        del entry["_id"]
        formatted_entries.append(WarehouseReturn(**entry))

    return formatted_entries


# ------------------- GET BY ID -------------------
@router.get("/{warehouse_return_id}", response_model=WarehouseReturn)
async def get_wastage_entry_by_id(warehouse_return_id: str):
    coll = get_warehouse_return_collection()
    entry = await coll.find_one({"_id": ObjectId(warehouse_return_id)})

    if not entry:
        raise HTTPException(status_code=404, detail="warehouse return not found")

    entry["warehouseReturnId"] = str(entry["_id"])
    return WarehouseReturn(**entry)


# ------------------- UPDATE (PUT) -------------------
@router.put("/{warehouse_return_id}")
async def update_wastage_entry(warehouse_return_id: str, warehouse_return: WarehouseReturnPost):
    coll = get_warehouse_return_collection()
    updated_data = warehouse_return.dict(exclude_unset=True)

    result = await coll.update_one(
        {"_id": ObjectId(warehouse_return_id)},
        {"$set": updated_data}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="warehouse_return not found")

    return {"message": "warehouse_return updated successfully"}


# ------------------- PATCH -------------------
@router.patch("/{warehouse_return_id}", response_model=WarehouseReturn)
async def patch_wastage_entry(warehouse_return_id: str, warehouse_return_patch: WarehouseReturnPost):
    coll = get_warehouse_return_collection()
    existing_entry = await coll.find_one({"_id": ObjectId(warehouse_return_id)})

    if not existing_entry:
        raise HTTPException(status_code=404, detail="Warehouse Returnnot found")

    updated_fields = {k: v for k, v in warehouse_return_patch.dict(exclude_unset=True).items() if v is not None}

    if updated_fields:
        result = await coll.update_one({"_id": ObjectId(warehouse_return_id)}, {"$set": updated_fields})
        if result.modified_count == 0:
            raise HTTPException(status_code=500, detail="Failed to update Warehouse Return")

    updated_entry = await coll.find_one({"_id": ObjectId(warehouse_return_id)})
    updated_entry["warehouseReturnId"] = str(updated_entry["_id"])

    return WarehouseReturn(**updated_entry)


# ------------------- DELETE -------------------
@router.delete("/{warehouse_return_id}")
async def delete_wastage_entry(warehouse_return_id: str):
    coll = get_warehouse_return_collection()
    result = await coll.delete_one({"_id": ObjectId(warehouse_return_id)})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Warehouse Return not found")

    return {"message": "Warehouse Return deleted successfully"}

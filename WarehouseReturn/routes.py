from typing import List
from fastapi import APIRouter, HTTPException
from bson import ObjectId
from .models import WarehouseReturn, WarehouseReturnPost
from .utils import get_warehouse_return_collection

router = APIRouter()

@router.post("/", response_model=str)
async def create_warehouse_return(warehouse_return: WarehouseReturnPost):
    new_warehouse_return_data = warehouse_return.dict()
    result = await get_warehouse_return_collection().insert_one(new_warehouse_return_data)
    return str(result.inserted_id)


@router.get("/", response_model=List[WarehouseReturn])
async def get_all_warehouseReturn_entries():
    collection = get_warehouse_return_collection()
    cursor = collection.find({})
    warehouseReturn_entries = await cursor.to_list(length=None)

    formatted_entries = []
    for entry in warehouseReturn_entries:
        entry["warehouseReturnId"] = str(entry["_id"])
        formatted_entries.append(WarehouseReturn(**entry))
    return formatted_entries


@router.get("/{warehouse_return_id}", response_model=WarehouseReturn)
async def get_warehouse_return_by_id(warehouse_return_id: str):
    entry = await get_warehouse_return_collection().find_one({"_id": ObjectId(warehouse_return_id)})
    if not entry:
        raise HTTPException(status_code=404, detail="Warehouse return not found")

    entry["warehouseReturnId"] = str(entry["_id"])
    return WarehouseReturn(**entry)


@router.put("/{warehouse_return_id}")
async def update_warehouse_return(warehouse_return_id: str, warehouse_return: WarehouseReturnPost):
    updated_data = warehouse_return.dict(exclude_unset=True)
    result = await get_warehouse_return_collection().update_one(
        {"_id": ObjectId(warehouse_return_id)},
        {"$set": updated_data}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Warehouse return not found")

    return {"message": "Warehouse return updated successfully"}


@router.patch("/{warehouse_return_id}")
async def patch_warehouse_return(warehouse_return_id: str, warehouse_return_patch: WarehouseReturnPost):
    collection = get_warehouse_return_collection()
    existing_entry = await collection.find_one({"_id": ObjectId(warehouse_return_id)})
    if not existing_entry:
        raise HTTPException(status_code=404, detail="Warehouse return not found")

    updated_fields = {k: v for k, v in warehouse_return_patch.dict(exclude_unset=True).items() if v is not None}
    if updated_fields:
        result = await collection.update_one({"_id": ObjectId(warehouse_return_id)}, {"$set": updated_fields})
        if result.modified_count == 0:
            raise HTTPException(status_code=500, detail="Failed to update warehouse return")

    updated_entry = await collection.find_one({"_id": ObjectId(warehouse_return_id)})
    updated_entry["warehouseReturnId"] = str(updated_entry["_id"])
    return updated_entry


@router.delete("/{warehouse_return_id}")
async def delete_warehouseReturn_entry(warehouse_return_id: str):
    result = await get_warehouse_return_collection().delete_one({"_id": ObjectId(warehouse_return_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Warehouse return not found")
    return {"message": "Warehouse return deleted successfully"}

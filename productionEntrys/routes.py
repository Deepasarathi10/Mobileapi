from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from bson import ObjectId
from .models import ProductionEntry, ProductionEntryPost, get_iso_datetime
from .utils import get_productionEntry_collection
from datetime import datetime
from dateutil import parser as date_parser
from pymongo import DESCENDING

router = APIRouter()

@router.post("/", response_model=dict)
async def create_dispatch(dispatch: ProductionEntryPost):
    coll = get_productionEntry_collection()

    last_doc = await coll.find_one(
        {"productionEntryNumber": {"$exists": True}},
        sort=[("productionEntryNumber", DESCENDING)]
    )
    last_number = last_doc["productionEntryNumber"] if last_doc else 0
    next_dispatch_number = last_number + 1

    new_dispatch = dispatch.model_dump()
    new_dispatch["productionEntryNumber"] = next_dispatch_number

    result = await coll.insert_one(new_dispatch)
    return {
        "inserted_id": str(result.inserted_id),
        "date": new_dispatch.get("date", get_iso_datetime()),
        "productionEntryNumber": next_dispatch_number
    }


@router.post("/entry", response_model=str)
async def create_production_entry(production_entry: ProductionEntryPost):
    new_production_entry_data = production_entry.dict()
    result = await get_productionEntry_collection().insert_one(new_production_entry_data)
    return str(result.inserted_id)


@router.get("/", response_model=List[ProductionEntry])
async def get_all_production_entries(date: Optional[str] = Query(None)):
    coll = get_productionEntry_collection()
    query = {}

    if date:
        try:
            date_obj = datetime.strptime(date, "%d-%m-%Y")
            start_date = date_obj.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = date_obj.replace(hour=23, minute=59, second=59, microsecond=999999)
            query["date"] = {"$gte": start_date.isoformat(), "$lte": end_date.isoformat()}
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use DD-MM-YYYY.")

    cursor = coll.find(query)
    production_entries = await cursor.to_list(length=None)

    formatted = []
    for entry in production_entries:
        entry["productionEntryId"] = str(entry["_id"])
        entry.pop("_id", None)

        date_val = entry.get("date")
        if isinstance(date_val, str):
            try:
                entry["date"] = date_parser.parse(date_val)
            except Exception:
                entry["date"] = None
        elif isinstance(date_val, datetime):
            entry["date"] = date_val
        else:
            entry["date"] = None

        formatted.append(ProductionEntry(**entry))

    return formatted


@router.get("/{production_entry_id}", response_model=ProductionEntry)
async def get_production_entry_by_id(production_entry_id: str):
    entry = await get_productionEntry_collection().find_one({"_id": ObjectId(production_entry_id)})
    if not entry:
        raise HTTPException(status_code=404, detail="ProductionEntry not found")
    entry["productionEntryId"] = str(entry["_id"])
    return ProductionEntry(**entry)


@router.put("/{production_entry_id}")
async def update_production_entry(production_entry_id: str, production_entry: ProductionEntryPost):
    updated = production_entry.dict(exclude_unset=True)
    result = await get_productionEntry_collection().update_one(
        {"_id": ObjectId(production_entry_id)}, {"$set": updated}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="ProductionEntry not found")
    return {"message": "ProductionEntry updated successfully"}


@router.patch("/{production_entry_id}")
async def patch_production_entry(production_entry_id: str, production_entry_patch: ProductionEntryPost):
    coll = get_productionEntry_collection()
    existing = await coll.find_one({"_id": ObjectId(production_entry_id)})
    if not existing:
        raise HTTPException(status_code=404, detail="ProductionEntry not found")

    updated_fields = {
        k: v for k, v in production_entry_patch.dict(exclude_unset=True).items() if v is not None
    }
    if updated_fields:
        result = await coll.update_one({"_id": ObjectId(production_entry_id)}, {"$set": updated_fields})
        if result.modified_count == 0:
            raise HTTPException(status_code=500, detail="Failed to update ProductionEntry")

    updated_entry = await coll.find_one({"_id": ObjectId(production_entry_id)})
    updated_entry["_id"] = str(updated_entry["_id"])
    return updated_entry


@router.delete("/{production_entry_id}")
async def delete_production_entry(production_entry_id: str):
    result = await get_productionEntry_collection().delete_one({"_id": ObjectId(production_entry_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="ProductionEntry not found")
    return {"message": "ProductionEntry deleted successfully"}

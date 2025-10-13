from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from bson import ObjectId
from bson.errors import InvalidId
from datetime import datetime

from fastapi.encoders import jsonable_encoder
from .models import ItemType, ItemTypePost
from .utils import get_itemtransfer_collection

router = APIRouter()

# ------------------- CREATE -------------------
@router.post("/", response_model=str, status_code=status.HTTP_201_CREATED)
async def create_itemtransfer(itemtransfer: ItemTypePost):
    new_itemtransfer_data = itemtransfer.model_dump()
    result = await get_itemtransfer_collection().insert_one(new_itemtransfer_data)
    return str(result.inserted_id)


# ------------------- GET ALL WITH FILTERS -------------------
@router.get("/", response_model=List[ItemType])
async def get_all_itemtransfer(
    from_branch: Optional[str] = Query(None),
    to_branch: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    status: Optional[List[str]] = Query(None),
):
    base_query = {}

    # Branch filters
    if from_branch:
        base_query["fromBranch"] = from_branch
    if to_branch:
        base_query["toBranch"] = to_branch

    # Status filter
    if status:
        base_query["status"] = status[0] if len(status) == 1 else {"$in": status}

    # Build date filter if applicable
    date_filter = {}
    try:
        if start_date:
            start_dt = datetime.strptime(start_date, "%d-%m-%Y").replace(hour=0, minute=0, second=0, microsecond=0)
            date_filter["$gte"] = start_dt
        if end_date:
            end_dt = datetime.strptime(end_date, "%d-%m-%Y").replace(hour=23, minute=59, second=59, microsecond=999999)
            date_filter["$lte"] = end_dt
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use DD-MM-YYYY.")

    # Priority date fields
    datetime_fields = ["requestDateTime", "sentDateTime", "receiveDateTime"]

    for field in datetime_fields:
        query = base_query.copy()
        if date_filter:
            query[field] = date_filter
        results = await get_itemtransfer_collection().find(query).to_list(length=None)
        if results:
            for item in results:
                item["itemtransferId"] = str(item["_id"])
            return [ItemType(**item) for item in results]

    # No matching data
    return []


# ------------------- GET BY ID -------------------
@router.get("/{itemtransfer_id}", response_model=ItemType)
async def get_itemtransfer_by_id(itemtransfer_id: str):
    try:
        object_id = ObjectId(itemtransfer_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid itemtransfer_id")

    itemtransfer = await get_itemtransfer_collection().find_one({"_id": object_id})
    if itemtransfer:
        itemtransfer["itemtransferId"] = str(itemtransfer["_id"])
        return ItemType(**itemtransfer)
    else:
        raise HTTPException(status_code=404, detail="Itemtransfer not found")

@router.patch("/{itemtransfer_id}")
async def patch_itemtransfer(itemtransfer_id: str, itemtransfer_patch: ItemTypePost):
    try:
        object_id = ObjectId(itemtransfer_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid itemtransfer_id")

    existing_itemtransfer = await get_itemtransfer_collection().find_one({"_id": object_id})
    if not existing_itemtransfer:
        raise HTTPException(status_code=404, detail="Itemtransfer not found")

    updated_fields = {k: v for k, v in itemtransfer_patch.model_dump(exclude_unset=True).items() if v is not None}

    if updated_fields:
        await get_itemtransfer_collection().update_one({"_id": object_id}, {"$set": updated_fields})

    updated_itemtransfer = await get_itemtransfer_collection().find_one({"_id": object_id})
    updated_itemtransfer["_id"] = str(updated_itemtransfer["_id"])
    updated_itemtransfer["itemtransferId"] = str(updated_itemtransfer["_id"])

    return jsonable_encoder(updated_itemtransfer)
# ------------------- DELETE -------------------
@router.delete("/{itemtransfer_id}")
async def delete_itemtransfer(itemtransfer_id: str):
    try:
        object_id = ObjectId(itemtransfer_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid itemtransfer_id")

    result = await get_itemtransfer_collection().delete_one({"_id": object_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Itemtransfer not found")
    return {"message": "Itemtransfer deleted successfully"}

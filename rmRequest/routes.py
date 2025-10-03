from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from bson import ObjectId
from datetime import date, datetime, timedelta
from dateutil.parser import isoparse

#from SalesOrder.utils import get_salesOrder_collection
from rmRequest.models import RmRequest, RmRequestPost, get_iso_datetime
from rmRequest.utils import get_rmdispatch_collection

router = APIRouter()

async def get_next_request_number():
    collection = get_rmdispatch_collection()

    latest = collection.find(
        {"requestNumber": {"$regex": r"^\d{3}$"}},
        sort=[("requestNumber", -1)],
        limit=1,
    )

    latest_request = await latest.to_list(length=1)
    if latest_request:
        try:
            last_number = int(latest_request[0]["requestNumber"])
            next_number = last_number + 1
        except ValueError:
            next_number = 1
    else:
        next_number = 1

    return f"{next_number:03d}"



@router.post("/", response_model=dict)
async def create_dispatch(dispatch: RmRequestPost):
    # Convert request to dict
    new_dispatch_data = dispatch.dict()

    # Always set current datetime in ISO format, overriding any client value
    new_dispatch_data["date"] = get_iso_datetime()

    # Assign auto-incremented request number
    new_dispatch_data["requestNumber"] = await get_next_request_number()

    # Insert into MongoDB
    result = await  get_rmdispatch_collection().insert_one(new_dispatch_data)

    return {
        "inserted_id": str(result.inserted_id),
        "requestNumber": new_dispatch_data["requestNumber"],
        "date": new_dispatch_data["date"]  # ISO string with timezone offset
    }
    

# ---------- Get All ----------
@router.get("/", response_model=List[RmRequest])
async def get_all_dispatch_entries(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
):
    query = {"status": {"$ne": "Cancel"}}

    if start_date or end_date:
        try:
            date_filter = {}
            if start_date:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                date_filter["$gte"] = start_dt.isoformat()

            if end_date:
                end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(
                    hour=23, minute=59, second=59, microsecond=999999
                )
                date_filter["$lte"] = end_dt.isoformat()

            if date_filter:
                query["date"] = date_filter
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    cursor = get_rmdispatch_collection().find(query)
    dispatch_entries = await cursor.to_list(length=None)

    for entry in dispatch_entries:
        entry["requestId"] = str(entry["_id"])
        if isinstance(entry["date"], datetime):
            entry["date"] = entry["date"].isoformat()

    return [RmRequest(**entry) for entry in dispatch_entries]

# ---------- Get By ID ----------
@router.get("/{request_id}", response_model=RmRequest)
async def get_dispatch_by_id(request_id: str):
    dispatch = await get_rmdispatch_collection().find_one({"_id": ObjectId(request_id)})
    if dispatch:
        dispatch["requestId"] = str(dispatch["_id"])
        return RmRequest(**dispatch)
    else:
        raise HTTPException(status_code=404, detail="Dispatch not found")
    
    

# ---------- Update (PUT) ----------
@router.put("/{request_id}")
async def update_dispatch(request_id: str, dispatch: RmRequestPost):
    updated_dispatch = dispatch.dict(exclude_unset=True)
    result = await get_rmdispatch_collection().update_one(
        {"_id": ObjectId(request_id)}, {"$set": updated_dispatch}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Dispatch not found")
    return {"message": "Dispatch updated successfully"}

# ---------- Patch ----------
@router.patch("/{request_id}")
async def patch_dispatch(request_id: str, dispatch_patch: RmRequestPost):
    existing_dispatch = await get_rmdispatch_collection().find_one({"_id": ObjectId(request_id)})
    if not existing_dispatch:
        raise HTTPException(status_code=404, detail="Dispatch not found")

    updated_fields = {
        key: value for key, value in dispatch_patch.dict(exclude_unset=True).items() if value is not None
    }

    if updated_fields:
        result = await get_rmdispatch_collection().update_one(
            {"_id": ObjectId(request_id)}, {"$set": updated_fields}
        )
        if result.modified_count == 0:
            raise HTTPException(status_code=500, detail="Failed to update Dispatch")

    updated_dispatch = await get_rmdispatch_collection().find_one({"_id": ObjectId(request_id)})
    updated_dispatch["_id"] = str(updated_dispatch["_id"])
    return updated_dispatch


# ---------- Delete ----------
@router.delete("/{request_id}")
async def delete_dispatch(request_id: str):
    result = await get_rmdispatch_collection().delete_one({"_id": ObjectId(request_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Dispatch not found")
    return {"message": "rmrequest deleted successfully"}
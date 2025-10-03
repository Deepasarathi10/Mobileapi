


from typing import List
from fastapi import APIRouter, HTTPException
from bson import ObjectId
from datetime import datetime
from rmclosing.models import RmClosing, RmClosingPost, get_iso_datetime
from rmclosing.utils import get_rmclosing_collection

router = APIRouter()


async def get_next_request_number():
    collection = await get_rmclosing_collection()
    latest = await collection.find().sort("requestNumber", -1).limit(1).to_list(length=1)

    if latest:
        return int(latest[0]["requestNumber"]) + 1   # ✅ Convert to int before adding
    return 1


@router.post("/", response_model=dict)
async def create_dispatch(dispatches: List[RmClosingPost]):
    collection = await get_rmclosing_collection()
    inserted_ids = []

    for dispatch in dispatches:
        new_dispatch_data = {
            "itemName": dispatch.itemName,
            "price": dispatch.price,
            "qty": dispatch.closingqty,
            "branch": dispatch.branchName,
            "uom": dispatch.uom,
            "date": get_iso_datetime(),
            "requestNumber": await get_next_request_number(),
        }
        result = await collection.insert_one(new_dispatch_data)
        inserted_ids.append(str(result.inserted_id))

    return {"inserted_ids": inserted_ids}



# ✅ Get all (no date filter, no cancel check)
# ✅ Get all (no date filter, no cancel check)
@router.get("/", response_model=List[RmClosing])
async def get_all_dispatch_entries():
    collection = await get_rmclosing_collection()

    dispatch_entries = await collection.find({}).to_list(length=None)

    for entry in dispatch_entries:
        entry["requestId"] = str(entry["_id"])

        # Convert datetime → iso string
        date_value = entry.get("date")
        if isinstance(date_value, datetime):
            entry["date"] = date_value.isoformat()
        elif date_value is None:
            entry["date"] = None

        # ✅ Convert requestNumber → string
        if "requestNumber" in entry and entry["requestNumber"] is not None:
            entry["requestNumber"] = str(entry["requestNumber"])

    return [RmClosing(**entry) for entry in dispatch_entries]


@router.get("/{request_id}", response_model=RmClosing)
async def get_dispatch_by_id(request_id: str):
    collection = await get_rmclosing_collection()

    dispatch = await collection.find_one({"_id": ObjectId(request_id)})

    if dispatch:
        dispatch["requestId"] = str(dispatch["_id"])

        if isinstance(dispatch.get("date"), datetime):
            dispatch["date"] = dispatch["date"].isoformat()

        # ✅ Convert requestNumber → string
        if "requestNumber" in dispatch and dispatch["requestNumber"] is not None:
            dispatch["requestNumber"] = str(dispatch["requestNumber"])

        return RmClosing(**dispatch)
    else:
        raise HTTPException(status_code=404, detail="Dispatch not found")

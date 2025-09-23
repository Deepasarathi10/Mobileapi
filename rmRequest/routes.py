from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from bson import ObjectId
from datetime import date, datetime, timedelta
from dateutil.parser import isoparse

#from SalesOrder.utils import get_salesOrder_collection
from rmRequest.models import RmRequest, RmRequestPost, get_iso_datetime
from rmRequest.utils import get_rmdispatch_collection

router = APIRouter()
def get_next_request_number():
    collection = get_rmdispatch_collection()

    # Find all matching requestNumbers starting with REQ (or just numeric)
    latest = collection.find(
        {"requestNumber": {"$regex": r"^\d{3}$"}},
        sort=[("requestNumber", -1)],
        limit=1
    )

    # Get the last request number if available
    latest_request = next(latest, None)
    if latest_request and "requestNumber" in latest_request:
        try:
            last_number = int(latest_request["requestNumber"])
            next_number = last_number + 1
        except ValueError:
            next_number = 1
    else:
        next_number = 1

    # Return formatted as 3-digit padded string (e.g., '001', '002', etc.)
    return f"{next_number:03d}"

# @router.post("/", response_model=dict)
# async def create_dispatch(dispatch: RmRequestPost):
#     new_dispatch_data = dispatch.dict()

#     if not new_dispatch_data.get("date"):
#         new_dispatch_data["date"] = get_iso_datetime()

#     # ✅ Assign auto-incremented requestNumber
#     new_dispatch_data["requestNumber"] = get_next_request_number()

#     result = get_rmdispatch_collection().insert_one(new_dispatch_data)

#     return {
#         "inserted_id": str(result.inserted_id),
#         "requestNumber": new_dispatch_data["requestNumber"],
#         "date": new_dispatch_data["date"]
#     }

@router.post("/", response_model=dict)
async def create_dispatch(dispatch: RmRequestPost):
    # Convert request to dict
    new_dispatch_data = dispatch.dict()

    # Always set current datetime in ISO format, overriding any client value
    new_dispatch_data["date"] = get_iso_datetime()

    # Assign auto-incremented request number
    new_dispatch_data["requestNumber"] = get_next_request_number()

    # Insert into MongoDB
    result = get_rmdispatch_collection().insert_one(new_dispatch_data)

    return {
        "inserted_id": str(result.inserted_id),
        "requestNumber": new_dispatch_data["requestNumber"],
        "date": new_dispatch_data["date"]  # ISO string with timezone offset
    }
    
    
    
# @router.get("/", response_model=List[RmRequest]) 
# async def get_all_dispatch_entries(
#     start_date: Optional[str] = Query(None),
#     end_date: Optional[str] = Query(None),
# ):
#     """
#     Fetch all RmRequest entries, optionally filtering by a start and end date,
#     excluding entries with a 'Cancel' status.
#     Dates must be in DD-MM-YYYY format.
#     """
#     query = {"status": {"$ne": "Cancel"}}  # Exclude cancelled dispatches

#     # Add date range filter if applicable
#     if start_date or end_date:
#         try:
#             date_filter = {}
#             if start_date:
#                 start_dt = datetime.strptime(start_date, "%Y-%m-%d")
#                 start_dt = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
#                 date_filter["$gte"] = start_dt

#             if end_date:
#                 end_dt = datetime.strptime(end_date, "%Y-%m-%d")
#                 end_dt = end_dt.replace(hour=23, minute=59, second=59, microsecond=999999)
#                 date_filter["$lte"] = end_dt

#             if date_filter:
#                 query["date"] = date_filter

#         except ValueError:
#             raise HTTPException(
#                 status_code=400, detail="Invalid date format. Use DD-MM-YYYY."
#             )

#     # Fetch from MongoDB
#     dispatch_entries = list(get_rmdispatch_collection().find(query))

#     # Convert _id to requestId
#     for entry in dispatch_entries:
#         entry["requestId"] = str(entry["_id"])
    
   


#     return [RmRequest(**entry) for entry in dispatch_entries]



@router.get("/", response_model=List[RmRequest])
async def get_all_dispatch_entries(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
):
    """
    Fetch all RmRequest entries, optionally filtering by a start and end date,
    excluding entries with a 'Cancel' status.
    Dates must be in YYYY-MM-DD format.
    """
    query = {"status": {"$ne": "Cancel"}}  # Exclude cancelled dispatches

    # Add date range filter if applicable
    if start_date or end_date:
        try:
            date_filter = {}
            if start_date:
                # Parse input date (YYYY-MM-DD)
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                start_dt = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
                # Convert to ISO 8601 string for MongoDB query
                date_filter["$gte"] = start_dt.isoformat()

            if end_date:
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                end_dt = end_dt.replace(hour=23, minute=59, second=59, microsecond=999999)
                # Convert to ISO 8601 string for MongoDB query
                date_filter["$lte"] = end_dt.isoformat()

            if date_filter:
                query["date"] = date_filter

        except ValueError:
            raise HTTPException(
                status_code=400, detail="Invalid date format. Use YYYY-MM-DD."
            )

    # Fetch from MongoDB
    dispatch_entries = list(get_rmdispatch_collection().find(query))

    # Convert _id to requestId
    for entry in dispatch_entries:
        entry["requestId"] = str(entry["_id"])
        # Ensure date is in ISO 8601 format (if stored as datetime in MongoDB)
        if isinstance(entry["date"], datetime):
            entry["date"] = entry["date"].isoformat()

    return [RmRequest(**entry) for entry in dispatch_entries]


@router.get("/{request_id}", response_model=RmRequest)
async def get_dispatch_by_id(request_id: str):
    """
    Fetch a dispatch entry by its ID.

    :param request_id: The ID of the dispatch entry.
    :return: The Dispatch object.
    
    """
    dispatch = get_rmdispatch_collection().find_one({"_id": ObjectId(request_id)})
    if dispatch:
        dispatch["requestId"] = str(dispatch["_id"])
        return RmRequest(**dispatch)
    else:
        raise HTTPException(status_code=404, detail="Dispatch not found")
    
    

@router.put("/{request_id}")
async def update_dispatch(request_id: str, dispatch: RmRequestPost):
    """
    Update an existing dispatch entry.

    :param request_id: The ID of the dispatch entry.
    :param dispatch: DispatchPost object with updated data.
    :return: Success message.
    """
    updated_dispatch = dispatch.dict(exclude_unset=True)  # Exclude unset fields
    result = get_rmdispatch_collection().update_one({"_id": ObjectId(request_id)}, {"$set": updated_dispatch})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Dispatch not found")
    return {"message": "Dispatch updated successfully"}

@router.patch("/{request_id}")
async def patch_dispatch(request_id: str, dispatch_patch: RmRequestPost):
    """
    Partially update an existing dispatch entry.

    :param request_id: The ID of the dispatch entry.
    :param dispatch_patch: DispatchPost object with fields to update.
    :return: The updated RMDispatch object.
    """
    existing_dispatch = get_rmdispatch_collection().find_one({"_id": ObjectId(request_id)})
    if not existing_dispatch:
        raise HTTPException(status_code=404, detail="Dispatch not found")

    updated_fields = {key: value for key, value in dispatch_patch.dict(exclude_unset=True).items() if value is not None}
    if updated_fields:
        result = get_rmdispatch_collection().update_one({"_id": ObjectId(request_id)}, {"$set": updated_fields})
        if result.modified_count == 0:
            raise HTTPException(status_code=500, detail="Failed to update Dispatch")

    updated_dispatch = get_rmdispatch_collection().find_one({"_id": ObjectId(request_id)})
    updated_dispatch["_id"] = str(updated_dispatch["_id"])
    return updated_dispatch

@router.delete("/{request_id}")
async def delete_dispatch(request_id: str):
    """
    Delete a dispatch entry by its ID.

    :param request_id: The ID of the dispatch entry.
    :return: Success message.
    """
    result = get_rmdispatch_collection().delete_one({"_id": ObjectId(request_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Dispatch not found")
    return {"message": "rmrequest deleted successfully"}


# @router.patch("/{request_id}/status")
# async def change_dispatch_status(request_id: str, status: str):
#     """
#     Change the status of a dispatch entry. If the dispatch type is 'SO' and the status is updated,
#     find the related sale order and update its status to 'production entry'.

#     :param request_id: The ID of the dispatch entry.
#     :param status: The new status of the dispatch entry.
#     :return: Success message.
#     """
#     dispatch = get_rmdispatch_collection().find_one({"_id": ObjectId(request_id)})
#     if not dispatch:
#         raise HTTPException(status_code=404, detail="Dispatch not found")

#     # Update dispatch status
#     result = get_rmdispatch_collection().update_one({"_id": ObjectId(request_id)}, {"$set": {"status": status}})
#     if result.modified_count == 0:
#         raise HTTPException(status_code=500, detail="Failed to update Dispatch status")

#     # If dispatch type is 'SO', update the related sale order status
#     if dispatch.get("type") == "SO":
#         sale_order_id = dispatch.get("saleOrderNo")
#         if sale_order_id:
#             sale_order = get_salesOrder_collection().find_one({"_id": ObjectId(sale_order_id)})
#             if sale_order:
#                 get_salesOrder_collection().update_one({"_id": ObjectId(sale_order_id)}, {"$set": {"status": "productionEntry"}})
#             else:
#                 raise HTTPException(status_code=404, detail="Sale order not found")

#     return {"message": "rmrequest status updated successfully"}
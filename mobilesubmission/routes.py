
from datetime import datetime
from http.client import InvalidURL
import logging
from typing import List, Optional
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Query,status

from mobilesubmission.models import Mobile, MobileGet,RemarkUpdate,viewStatesUpdate
from mobilesubmission.utils import get_mobile_details

router = APIRouter()

@router.get("/", response_model=List[MobileGet])
async def get_all(
    branch_name: Optional[str] = Query(None, description="Filter by single branch name (deprecated if using branch_names)"),
    branch_names: Optional[List[str]] = Query(None, description="Filter by one or more branch names"),
    date: Optional[datetime] = Query(None, description="Filter by specific date (YYYY-MM-DD)")
):
    query = {}
    mobiles = []

    # Branch filter
    if branch_names:
        query["branchName"] = {"$in": branch_names}
    elif branch_name:
        query["branchName"] = branch_name

    # Date filter (entire day range)
    if date:
        start = datetime.combine(date.date(), datetime.min.time())
        end = datetime.combine(date.date(), datetime.max.time())
        query["date"] = {"$gte": start, "$lte": end}

    try:
        collection = get_mobile_details()
        if collection is None:
            raise HTTPException(status_code=500, detail="MongoDB collection not found")
        # collection.update_many(query, {"$set": {"viewStates": "delivery"}})
        mobiles = list(collection.find(query))

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return [
        MobileGet(**{
            **mobile,
            "id": str(mobile.get("_id", ""))
        })
        for mobile in mobiles
    ]
        

@router.post("/", response_model=str,status_code=status.HTTP_201_CREATED)
async def create_mobile(mob_data:Mobile):
    try:
        new_mobile= mob_data.dict()
        result = get_mobile_details().insert_one(new_mobile)
        return str(result.inserted_id)
    except Exception as e:
        logging.error(f"Error occurred: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


#         raise HTTPException(status_code=500, detail="Internal Server Error")      
@router.patch("/display/{id}/remark", response_model=dict)
async def update_remark(id: str, update: RemarkUpdate):
    if not update.reMark:
        raise HTTPException(status_code=422, detail="No remark provided")

    try:
        result = get_mobile_details().update_one(
            {"_id": ObjectId(id)},
            {"$set": {"reMark": update.reMark}}
        )

        # Use matched_count to ensure the document exists, even if no change happened
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Employee not found")

        updated_doc = get_mobile_details().find_one(
            {"_id": ObjectId(id)},
            {"reMark": 1, "_id": 0}
        )
        return updated_doc

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update remark: {str(e)}")



@router.patch("/{id}", response_model=dict)
async def update_viewStates_only(id: str, update: viewStatesUpdate):
    if not update.viewStates:
        raise HTTPException(status_code=422, detail="viewStates is required")

    try:
        try:
            object_id = ObjectId(id)
        except InvalidURL:
            raise HTTPException(status_code=400, detail="Invalid ObjectId format")

        result = get_mobile_details().update_one(
            {"_id": object_id},
            {"$set": {"viewStates": update.viewStates}}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Sheet not found")

        # Return only viewStates
        updated_doc = get_mobile_details().find_one(
            {"_id": object_id},
            {"_id": 0, "viewStates": 1}
        )

        return updated_doc

    except HTTPException:
        raise  # Re-raise HTTPExceptions as is

    except Exception as e:
        logging.error(f"Error updating viewStates for sheet {id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update viewStates: {str(e)}"
        )
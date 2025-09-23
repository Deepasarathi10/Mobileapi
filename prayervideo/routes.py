
from datetime import datetime
from http.client import InvalidURL
import logging
from typing import List, Optional
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Query,status

from prayervideo.models import Employee,EmployeeGet,RemarkUpdate,viewStatesUpdate
from prayervideo.utils import get_prayer_report


router = APIRouter()

@router.get("/", response_model=List[EmployeeGet])
async def get_all(
    branch_name: Optional[str] = Query(None, description="Filter by single branch name (deprecated if using branch_names)"),
    branch_names: Optional[List[str]] = Query(None, description="Filter by multiple branch names"),
    date: Optional[datetime] = Query(None, description="Filter by specific date (YYYY-MM-DD)")
):
    filters = {}

    # Branch filter
    if branch_names:
        filters["branchName"] = {"$in": branch_names}
    elif branch_name:
        filters["branchName"] = branch_name

    # Date filter (entire day range)
    if date:
        start = datetime.combine(date.date(), datetime.min.time())
        end = datetime.combine(date.date(), datetime.max.time())
        filters["date"] = {"$gte": start, "$lte": end}

    try:
        collection = get_prayer_report()  # Your MongoDB collection getter

        # Update 'viewstates' to 'delivery' for matching documents
        # collection.update_many(filters, {"$set": {"viewStates": "delivery"}})

        employees = list(collection.find(filters))

        # Convert ObjectId to string
        for emp in employees:
            emp["id"] = str(emp.pop("_id", ""))

        return employees

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.post("/", response_model=str,status_code=status.HTTP_201_CREATED)
async def create_mobile(prayer_data:Employee):
    try:
        new_prayer= prayer_data.dict()
        result = get_prayer_report().insert_one(new_prayer)
        return str(result.inserted_id)
    except Exception as e:
        logging.error(f"Error occurred: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

  
# PATCH route
@router.patch("/{prayer_id}/remark", response_model=dict)
async def update_remark_only(prayer_id: str, update: RemarkUpdate):
    if not update.reMark:
        raise HTTPException(status_code=422, detail="Remark is required")

    try:
        result = get_prayer_report().update_one(
            {"_id": ObjectId(prayer_id)},
            {"$set": {"reMark": update.reMark}}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Record not found")

        updated_doc = get_prayer_report().find_one(
            {"_id": ObjectId(prayer_id)},
            {"_id": 0, "reMark": 1}
        )

        return updated_doc

    except Exception as e:
        logging.error(f"Error updating reMark for record {prayer_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")     

@router.patch("/{id}", response_model=dict)
async def update_viewStates_only(id: str, update: viewStatesUpdate):
    if not update.viewStates:
        raise HTTPException(status_code=422, detail="viewStates is required")

    try:
        try:
            object_id = ObjectId(id)
        except InvalidURL:
            raise HTTPException(status_code=400, detail="Invalid ObjectId format")

        result = get_prayer_report().update_one(
            {"_id": object_id},
            {"$set": {"viewStates": update.viewStates}}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Sheet not found")

        # Return only viewStates
        updated_doc = get_prayer_report().find_one(
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
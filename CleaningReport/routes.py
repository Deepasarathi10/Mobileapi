
from datetime import datetime
from http.client import InvalidURL
import logging
from typing import List, Optional
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Query,status

from CleaningReport .models import Employee,EmployeeGet,RemarkUpdate,viewStatesUpdate
from CleaningReport.utils import get_cleaning_video


router = APIRouter()

@router.get("/", response_model=List[EmployeeGet])
async def get_all(
    branch_name: Optional[str] = Query(None, description="Filter by branch name"),
    branch_names: Optional[List[str]] = Query(None, description="Filter by multiple branch names"),
    date: Optional[datetime] = Query(None, description="Filter by specific date (YYYY-MM-DD)")
):
    query = {}

    # Add branch name filter
    if branch_names:
        query["branchName"] = {"$in": branch_names}
    elif branch_name:
        query["branchName"] = branch_name

    # Add single-day date filter
    if date:
        start_of_day = datetime.combine(date.date(), datetime.min.time())
        end_of_day = datetime.combine(date.date(), datetime.max.time())
        query["date"] = {"$gte": start_of_day, "$lte": end_of_day}

    try:
        collection = get_cleaning_video()

        # Update `viewstates` field to "delivery" for all matching documents

        # Fetch the updated documents
        employees = list(collection.find(query))

        return [
            EmployeeGet(**{**emp, "id": str(emp["_id"])})
            for emp in employees
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=str,status_code=status.HTTP_201_CREATED)
async def create_video(video_data:Employee):
    try:
        new_video= video_data.dict()
        result = get_cleaning_video().insert_one(new_video)
        return str(result.inserted_id)
    except Exception as e:
        logging.error(f"Error occurred: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.patch("/{id}/remark")
async def update_employee_remark(id: str, remark_update: RemarkUpdate):
    try:
        object_id = ObjectId(id)

        # Update only the 'reMark' field with the new string value (replace old)
        result = get_cleaning_video().update_one(
            {"_id": object_id},
            {"$set": {"reMark": remark_update.reMark}}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Employee not found")

        return {
            "message": "Remark updated successfully",
            "modified_count": result.modified_count,
            "reMark": remark_update.reMark
        }
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

        result = get_cleaning_video().update_one(
            {"_id": object_id},
            {"$set": {"viewStates": update.viewStates}}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Cleaning not found")

        updated_doc = get_cleaning_video().find_one(
            {"_id": object_id},
            {"_id": 0, "viewStates": 1}
        )

        return updated_doc
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error updating viewStates for sheet {id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update viewStates: {str(e)}"
        )
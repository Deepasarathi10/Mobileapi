
from datetime import datetime
from http.client import InvalidURL
import logging
from typing import List, Optional
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Query,status
from kraSheet.models import Employee, EmployeeGet, RemarkUpdate, viewStatesUpdate
from  kraSheet.utils import get_clean_report


router = APIRouter()

@router.get("/", response_model=List[EmployeeGet])
async def get_all(
    branch_names: Optional[List[str]] = Query(None, description="Filter by multiple branch names"),
    date: Optional[datetime] = Query(None, description="Filter by specific date (YYYY-MM-DD)")
):
    query = {}

    # Filter by branch name(s)
    if branch_names:
        query["branchName"] = {"$in": branch_names}
 

    # Filter by date (entire day)
    if date:
        start_of_day = datetime.combine(date.date(), datetime.min.time())
        end_of_day = datetime.combine(date.date(), datetime.max.time())
        query["date"] = {"$gte": start_of_day, "$lte": end_of_day}

    try:
        collection = get_clean_report()
        
        # collection.update_many(query, {"$set": {"viewStates": "delivery"}})

        employees = list(collection.find(query))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return [
        EmployeeGet(
            **{
                **{k: v for k, v in emp.items() if k != "_id"},
                "id": str(emp["_id"])
            }
        )
        for emp in employees
    ]

@router.post("/", response_model=str,status_code=status.HTTP_201_CREATED)
async def create_report(report:Employee):
    try:
        new_report= report.dict()
        result = get_clean_report().insert_one(new_report)
        return str(result.inserted_id)
    except Exception as e:
        logging.error(f"Error occurred: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

# --- PATCH Endpoint to Update Only `remarks` ---
@router.patch("/sheets/{id}/remark", response_model=dict)
async def update_remarks_only(id: str, update: RemarkUpdate):
    if not update.reMark:
        raise HTTPException(status_code=422, detail="Remark is required")

    try:
        result = get_clean_report().update_one(
            {"_id": ObjectId(id)},
            {"$set": {"reMark": update.reMark}}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Sheet not found")

        # Fetch and return only the updated remark
        updated_doc = get_clean_report().find_one(
            {"_id": ObjectId(id)},
            {"_id": 0, "reMark": 1}
        )

        return updated_doc

    except Exception as e:
        logging.error(f"Error updating remark for sheet {id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update remark: {str(e)}"
        )
        
@router.patch("/{id}", response_model=dict)
async def update_viewStates_only(id: str, update: viewStatesUpdate):
    if not update.viewStates:
        raise HTTPException(status_code=422, detail="viewStates is required")

    try:
        try:
            object_id = ObjectId(id)
        except InvalidURL:
            raise HTTPException(status_code=400, detail="Invalid ObjectId format")

        result = get_clean_report().update_one(
            {"_id": object_id},
            {"$set": {"viewStates": update.viewStates}}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Sheet not found")

        # Return only viewStates
        updated_doc = get_clean_report().find_one(
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
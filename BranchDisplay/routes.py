
from datetime import datetime
import logging
from typing import List, Optional
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Query,status
from .models import Employee, EmployeeGet,RemarkUpdate,viewStatesUpdate
from .utils import get_branch_report
from bson.errors import InvalidId



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
        collection = get_branch_report()

        

        # Fetch the updated documents
        employees = list(collection.find(query))

        return [
            EmployeeGet(**{**emp, "id": str(emp["_id"])})
            for emp in employees
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=str,status_code=status.HTTP_201_CREATED)
async def create_branch(branch_data:Employee):
    try:
        new_branch= branch_data.dict()
        result = get_branch_report().insert_one(new_branch)
        return str(result.inserted_id)
    except Exception as e:
        logging.error(f"Error occurred: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
    

@router.patch("/{id}/remark")
async def update_employee_remark(id: str, update: RemarkUpdate):
    try:
        # Check if reMark is provided
        if not update.reMark:
            raise HTTPException(status_code=422, detail="Remark is required")

        object_id = ObjectId(id)

        result =  get_branch_report().update_one(
            {"_id": object_id},
            {"$set": {"reMark": update.reMark}}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Employee not found")

        return {
            "message": "Remark updated successfully",
            "modified_count": result.modified_count,
            "reMark": update.reMark
        }

    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Error updating remark: {str(e)}")
    
    
@router.patch("/{id}", response_model=dict)
async def update_viewStates_only(id: str, update: viewStatesUpdate):
    if not update.viewStates:
        raise HTTPException(status_code=422, detail="viewStates is required")

    try:
        try:
            object_id = ObjectId(id)
        except InvalidId:
            raise HTTPException(status_code=400, detail="Invalid ObjectId format")

        result = get_branch_report().update_one(
            {"_id": object_id},
            {"$set": {"viewStates": update.viewStates}}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Branch not found")

        # Return only viewStates
        updated_doc = get_branch_report().find_one(
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
        
        
        
        
        
        
        
        
        
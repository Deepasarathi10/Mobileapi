from datetime import datetime
from http.client import InvalidURL
import logging
from typing import List, Optional
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Query,status

from empphoto.models import Employee, EmployeeGet,RemarkUpdate,viewStatesUpdate
from empphoto.utils import get_emp_details
    

router =APIRouter()

@router.get("/", response_model=List[EmployeeGet])
async def get_all_employee(
    branch_name: Optional[str] = Query(None, description="Filter by single branch name"),
    branch_names: Optional[List[str]] = Query(None, description="Filter by multiple branch names"),
    date: Optional[datetime] = Query(None, description="Filter by specific date (YYYY-MM-DD)")
):
    query = {}

    # Branch filter
    if branch_names:
        query["branchName"] = {"$in": branch_names}
    elif branch_name:
        query["branchName"] = branch_name

    # Single-day date filter
    if date:
        start_of_day = datetime.combine(date.date(), datetime.min.time())
        end_of_day = datetime.combine(date.date(), datetime.max.time())
        query["date"] = {"$gte": start_of_day, "$lte": end_of_day}

    try:
        collection = get_emp_details()

        # Update viewstates field to "delivery" for matched documents
        # collection.update_many(query, {"$set": {"viewStates": "delivery"}})

        employees = list(collection.find(query))

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Response format
    return [
        EmployeeGet(**{**employee, "id": str(employee["_id"])})
        for employee in employees
    ]




@router.post("/", response_model=str,status_code=status.HTTP_201_CREATED)
async def create_emp(emp_data: Employee):
    try:
        new_emp = emp_data.dict()
        
        result = get_emp_details().insert_one(new_emp)
        return str(result.inserted_id)
    
    except Exception as e:
        logging.error(f"Error occurred: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
 
 
 
@router.patch("/{emp_id}/remark", response_model=dict)
async def update_employee_remark(emp_id: str, update: RemarkUpdate):
    try:
        # Validate ID and prepare the update
        emp_obj_id = ObjectId(emp_id)

        result = get_emp_details().update_one(
            {"_id": emp_obj_id},
            {"$set": {"reMark": update.reMark}}
        )

        # If employee is not found
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Employee not found")

        # Fetch and return updated remark
        updated_emp = get_emp_details().find_one(
            {"_id": emp_obj_id},
            {"_id": 0, "reMark": 1}
        )

        return updated_emp

    except Exception as e:
        logging.error(f"Error updating remark for employee {emp_id}: {str(e)}", exc_info=True)
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

        result = get_emp_details().update_one(
            {"_id": object_id},
            {"$set": {"viewStates": update.viewStates}}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Sheet not found")

        # Return only viewStates
        updated_doc = get_emp_details().find_one(
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
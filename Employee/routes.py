from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from bson import ObjectId
from .models import Employee, EmployeePost, EmployeeSearch
from .utils import get_employee_collection
import re
router = APIRouter()

@router.post("/", response_model=str)
async def create_employee(employee: EmployeePost):
    # Prepare data for insertion
    new_employee_data = employee.dict()

    # Insert into MongoDB
    result = get_employee_collection().insert_one(new_employee_data)
    return str(result.inserted_id)

@router.get("/", response_model=List[Employee])
async def get_all_employee():
    employees = list(get_employee_collection().find())
    formatted_employee = []
    for employee in employees:
        employee["employeeId"] = str(employee["_id"])
        formatted_employee.append(Employee(**employee))
    return formatted_employee

@router.get("/{employee_id}", response_model=Employee)
async def get_employee_by_id(employee_id: str):
    employee = get_employee_collection().find_one({"_id": ObjectId(employee_id)})
    if employee:
        employee["employeeId"] = str(employee["_id"])
        return Employee(**employee)
    else:
        raise HTTPException(status_code=404, detail="Employee not found")

@router.put("/{employee_id}")
async def update_employee(employee_id: str, employee:EmployeePost):
    updated_employee= employee.dict(exclude_unset=True)  # exclude_unset=True prevents sending None values to MongoDB
    result = get_employee_collection().update_one({"_id": ObjectId(employee_id)}, {"$set": updated_employee})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Employee not found")
    return {"message": "Employee updated successfully"}

@router.patch("/{employee_id}")
async def patch_employee(employee_id: str, employee_patch: EmployeePost):
    existing_employee = get_employee_collection().find_one({"_id": ObjectId(employee_id)})
    if not existing_employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    updated_fields = {key: value for key, value in employee_patch.dict(exclude_unset=True).items() if value is not None}
    if updated_fields:
        result = get_employee_collection().update_one({"_id": ObjectId(employee_id)}, {"$set": updated_fields})
        if result.modified_count == 0:
            raise HTTPException(status_code=500, detail="Failed to update Employee")

    updated_employee = get_employee_collection().find_one({"_id": ObjectId(employee_id)})
    updated_employee["_id"] = str(updated_employee["_id"])
    return updated_employee

@router.delete("/{employee_id}")
async def delete_employee(employee_id: str):
    result = get_employee_collection().delete_one({"_id": ObjectId(employee_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Employee not found")
    return {"message": "Employee deleted successfully"}



# @router.get("/search-by/", response_model=List[str])
# async def get_employee_by_name_or_number(
#     employeeName: Optional[str] = Query(None), 
#     employeeNumber: Optional[str] = Query(None)
# ):
#     query = {}
    
#     # Build the query based on provided parameters (use regex for partial matching)
#     if employeeName:
#         query["firstName"] = {"$regex": re.compile(f".*{employeeName}.*", re.IGNORECASE)}
#     elif employeeNumber:
#         query["employeeNumber"] = {"$regex": re.compile(f".*{employeeNumber}.*", re.IGNORECASE)}
#     else:
#         raise HTTPException(status_code=400, detail="Either employeeName or employeeNumber must be provided")
    
#     # Perform the query and get matching employees
#     employees = get_employee_collection().find(query)
#     results = [f"{emp.get('firstName')} - {emp.get('employeeNumber')}" for emp in employees]
    
#     if not results:
#         raise HTTPException(status_code=404, detail="No employees found")
    
#     return results


@router.get("/search-by/", response_model=List[str])
async def get_employee_by_name_or_number(
    searchQuery: Optional[str] = Query(None)  # Accepts a general search query
):
    # Define the query based on whether searchQuery is provided
    if searchQuery:
        # Match only at the start of `firstName` or `employeeNumber`
        query = {
            "$or": [
                {"firstName": {"$regex": re.compile(f"^{searchQuery}", re.IGNORECASE)}},
                {"employeeNumber": {"$regex": re.compile(f"^{searchQuery}", re.IGNORECASE)}}
            ]
        }
    else:
        query = {}  # Empty query retrieves all employees if no searchQuery is given
    
    # Retrieve the collection and perform the query
    employees = get_employee_collection().find(query)
    
    # Collect results into a list
    results = [f"{emp.get('firstName')} - {emp.get('employeeNumber')}" for emp in employees]
    
    # If no employees match, raise a 404 error
    if not results:
        raise HTTPException(status_code=404, detail="No employees found")
    
    return results

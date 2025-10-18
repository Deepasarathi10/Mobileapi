from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from bson import ObjectId
import re
from .models import Employee, EmployeePost
from .utils import get_employee_collection

router = APIRouter()


@router.post("/", response_model=str)
async def create_employee(employee: EmployeePost):
    collection = get_employee_collection()
    new_employee_data = employee.dict()
    result = await collection.insert_one(new_employee_data)
    return str(result.inserted_id)


@router.get("/", response_model=List[Employee])
async def get_all_employee():
    collection = get_employee_collection()
    employees_cursor = collection.find({})
    employees = []
    async for employee in employees_cursor:
        employee["employeeId"] = str(employee["_id"])
        employees.append(Employee(**employee))
    return employees


@router.get("/drivers", response_model=List[str])
async def get_driver_names():
    collection = get_employee_collection()
    cursor = collection.find({"position": "Driver"})

    driver_list = []
    seen_emp_nos = set()

    async for employee in cursor:
        name = employee.get("firstName", "")
        emp_no = employee.get("employeeNumber", "")
        if name and emp_no and emp_no not in seen_emp_nos:
            driver_list.append(f"{name} - {emp_no}")
            seen_emp_nos.add(emp_no)

    return driver_list


@router.get("/{employee_id}", response_model=Employee)
async def get_employee_by_id(employee_id: str):
    collection = get_employee_collection()
    employee = await collection.find_one({"_id": ObjectId(employee_id)})

    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    employee["employeeId"] = str(employee["_id"])
    return Employee(**employee)


@router.put("/{employee_id}")
async def update_employee(employee_id: str, employee: EmployeePost):
    collection = get_employee_collection()
    updated_employee = employee.dict(exclude_unset=True)
    result = await collection.update_one(
        {"_id": ObjectId(employee_id)},
        {"$set": updated_employee}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Employee not found")

    return {"message": "Employee updated successfully"}


@router.patch("/{employee_id}")
async def patch_employee(employee_id: str, employee_patch: EmployeePost):
    collection = get_employee_collection()
    existing_employee = await collection.find_one({"_id": ObjectId(employee_id)})

    if not existing_employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    updated_fields = {
        key: value
        for key, value in employee_patch.dict(exclude_unset=True).items()
        if value is not None
    }

    if updated_fields:
        result = await collection.update_one(
            {"_id": ObjectId(employee_id)},
            {"$set": updated_fields}
        )
        if result.modified_count == 0:
            raise HTTPException(status_code=500, detail="Failed to update Employee")

    updated_employee = await collection.find_one({"_id": ObjectId(employee_id)})
    updated_employee["_id"] = str(updated_employee["_id"])
    return updated_employee


@router.delete("/{employee_id}")
async def delete_employee(employee_id: str):
    collection = get_employee_collection()
    result = await collection.delete_one({"_id": ObjectId(employee_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Employee not found")
    return {"message": "Employee deleted successfully"}


@router.get("/search-by/", response_model=List[str])
async def get_employee_by_name_or_number(
    searchQuery: Optional[str] = Query(None)
):
    collection = get_employee_collection()

    if searchQuery:
        query = {
            "$or": [
                {"firstName": {"$regex": re.compile(f"^{searchQuery}", re.IGNORECASE)}},
                {"employeeNumber": {"$regex": re.compile(f"^{searchQuery}", re.IGNORECASE)}}
            ]
        }
    else:
        query = {}

    cursor = collection.find(query)
    results = []
    async for emp in cursor:
        results.append(f"{emp.get('firstName')} - {emp.get('employeeNumber')}")

    if not results:
        raise HTTPException(status_code=404, detail="No employees found")

    return results

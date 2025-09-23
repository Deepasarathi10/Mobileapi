from typing import List
from fastapi import APIRouter, HTTPException
from bson import ObjectId
from .models import Designation, DesignationPost
from .utils import get_designation_collection, convert_to_string_or_none

router = APIRouter()

@router.post("/", response_model=str)
async def create_designation(designation: DesignationPost):
    new_designation_data = designation.dict()
    new_designation_data['status'] = "active"

    try:
        result = get_designation_collection().insert_one(new_designation_data)
        return str(result.inserted_id)
    except Exception as e:
        print(f"Error creating designation: {e}")
        raise HTTPException(status_code=500, detail="Failed to create designation")

@router.get("/", response_model=List[Designation])
async def get_all_designations():
    try:
        designations = list(get_designation_collection().find())
        formatted_designations = []
        for des in designations:
            for key, value in des.items():
                des[key] = convert_to_string_or_none(value)
            des["designationId"] = str(des["_id"])
            formatted_designations.append(Designation(**des))
        return formatted_designations
    except Exception as e:
        print(f"Error fetching designations: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/{designation_id}", response_model=Designation)
async def get_designation_by_id(designation_id: str):
    try:
        designation = get_designation_collection().find_one({"_id": ObjectId(designation_id)})
        if designation:
            for key, value in designation.items():
                designation[key] = convert_to_string_or_none(value)
            designation["designationId"] = str(designation["_id"])
            return Designation(**designation)
        else:
            raise HTTPException(status_code=404, detail="Designation not found")
    except Exception as e:
        print(f"Error fetching designation by ID: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.patch("/{designation_id}")
async def update_designation(designation_id: str, designation: DesignationPost):
    try:
        updated_data = designation.dict(exclude_unset=True)
        result = get_designation_collection().update_one(
            {"_id": ObjectId(designation_id)},
            {"$set": updated_data}
        )
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Designation not found")
        return {"message": "Designation updated successfully"}
    except Exception as e:
        print(f"Error updating designation: {e}")
        raise HTTPException(status_code=500, detail="Failed to update designation")

@router.patch("/{designation_id}/status")
async def patch_designation_status(designation_id: str, status: str):
    try:
        existing = get_designation_collection().find_one({"_id": ObjectId(designation_id)})
        if not existing:
            raise HTTPException(status_code=404, detail="Designation not found")

        if status not in ["active", "deactivated"]:
            raise HTTPException(status_code=400, detail="Invalid status value")

        result = get_designation_collection().update_one(
            {"_id": ObjectId(designation_id)},
            {"$set": {"status": status}}
        )
        if result.modified_count == 0:
            raise HTTPException(status_code=500, detail="Failed to update designation status")

        updated = get_designation_collection().find_one({"_id": ObjectId(designation_id)})
        for key, value in updated.items():
            updated[key] = convert_to_string_or_none(value)
        updated["designationId"] = str(updated["_id"])
        return updated
    except Exception as e:
        print(f"Error patching designation status: {e}")
        raise HTTPException(status_code=500, detail="Failed to patch designation status")

@router.delete("/{designation_id}")
async def delete_designation(designation_id: str):
    try:
        result = get_designation_collection().delete_one({"_id": ObjectId(designation_id)})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Designation not found")
        return {"message": "Designation deleted successfully"}
    except Exception as e:
        print(f"Error deleting designation: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete designation")

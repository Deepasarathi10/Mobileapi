from typing import List
from fastapi import APIRouter, HTTPException
from bson import ObjectId
from .models import kotTableStatus, kotTableStatusPost, kotTableStatusPatch
from .utils import get_kotTableStatus_collection

router = APIRouter()

# Generate unique branch ID
import hashlib

def generate_branch_id(branch_name: str) -> str:
    return hashlib.md5(branch_name.encode()).hexdigest()

@router.post("/upsert", response_model=str)
async def upsert_kotTableStatus(kotTableStatus: kotTableStatusPost):
    branch_id = generate_branch_id(kotTableStatus.branchName)
    kotTableStatus.hiveStatusId = branch_id

    existing_entry = get_kotTableStatus_collection().find_one({"hiveStatusId": branch_id})

    if existing_entry:
        # Update existing record
        updated_fields = kotTableStatus.dict(exclude_unset=True)  # Includes all fields
        result = get_kotTableStatus_collection().update_one({"hiveStatusId": branch_id}, {"$set": updated_fields})
        if result.modified_count == 0:
            raise HTTPException(status_code=500, detail="Failed to update kotTableStatus")
        return "Updated successfully"
    else:
        # Insert new record
        new_kotTableStatus_data = kotTableStatus.dict()
        result = get_kotTableStatus_collection().insert_one(new_kotTableStatus_data)
        return str(result.inserted_id)



@router.get("/by-branch/{branch_name}/{updatedDate}", response_model=kotTableStatus)
async def get_kotTableStatus_by_branch(branch_name: str, updatedDate: str):
    # Generate branch ID
    branch_id = generate_branch_id(branch_name)

    # Fetch the matching record
    kotTableStatus = get_kotTableStatus_collection().find_one({"hiveStatusId": branch_id, "updatedDate": updatedDate})

    # Handle no matching records
    if not kotTableStatus:
        raise HTTPException(status_code=404, detail="kotTableStatus not found")

    # Handle unexpected list response (if multiple entries exist)
    if isinstance(kotTableStatus, list):  # If the response is a list, pick the first item
        kotTableStatus = kotTableStatus[0]

    # Add the ID field explicitly
    kotTableStatus["kotTableStatusId"] = str(kotTableStatus["_id"])

    # Return as a dictionary
    return kotTableStatus


@router.get("", response_model=List[kotTableStatus])
async def get_all_kotTableStatus():
    kotTableStatus_list = get_kotTableStatus_collection().find()
    result = []
    for item in kotTableStatus_list:
        item["kotTableStatusId"] = str(item["_id"])
        result.append(kotTableStatus(**item))
    return result

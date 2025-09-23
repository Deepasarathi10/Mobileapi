
import logging
from datetime import datetime
from typing import List
from bson import ObjectId
from fastapi import APIRouter, HTTPException, status
from OpeningCash.utils import get_opening_cash_collection
from OpeningCash.models import OpeningCash, OpeningCashPost

router = APIRouter()

## Get All OpeningCashs in LIFO order
@router.get("/", response_model=List[OpeningCash])
async def get_all_openingcashs():
    try:
        openingcashs = list(get_opening_cash_collection().find().sort("createdDate", -1))
        openingcash_store = []
        
        for openingcash_data in openingcashs:
            openingcash_data["systemOpenCashId"] = str(openingcash_data["_id"])  # Map _id to systemOpenCashId
            del openingcash_data["_id"]  # Remove _id to match Pydantic model
            openingcash_store.append(OpeningCash(**openingcash_data))
        
        return openingcash_store
    except Exception as e:
        logging.error(f"Error fetching OpeningCash records: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

## Create a new OpeningCash
@router.post("/", response_model=str, status_code=status.HTTP_201_CREATED)
async def create_openingcash(openingcash_data: OpeningCashPost):
    try:
        new_openingcash = openingcash_data.dict()
        new_openingcash["createdDate"] = datetime.utcnow()
        
        result = get_opening_cash_collection().insert_one(new_openingcash)
        return str(result.inserted_id)  # Return the MongoDB _id
    except Exception as e:
        logging.error(f"Error creating OpeningCash: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

## Get a specific OpeningCash by ID
@router.get("/{record_id}", response_model=OpeningCash)
async def get_openingcash_by_id(record_id: str):
    try:
        # First try to find by MongoDB _id
        if ObjectId.is_valid(record_id):
            openingcash = get_opening_cash_collection().find_one({"_id": ObjectId(record_id)})
            if openingcash:
                openingcash["systemOpenCashId"] = str(openingcash["_id"])
                del openingcash["_id"]
                return OpeningCash(**openingcash)
        
        # If not found by _id, try by systemOpenCashId (if you want to support both)
        openingcash = get_opening_cash_collection().find_one({"systemOpenCashId": record_id})
        if openingcash:
            openingcash["systemOpenCashId"] = str(openingcash.get("_id", record_id))
            if "_id" in openingcash:
                del openingcash["_id"]
            return OpeningCash(**openingcash)
        
        raise HTTPException(status_code=404, detail="OpeningCash not found")
    except Exception as e:
        logging.error(f"Error fetching OpeningCash by ID: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

## Patch (Update) an OpeningCash
@router.patch("/{record_id}", response_model=OpeningCash)
async def patch_openingcash(record_id: str, openingcash_patch: OpeningCashPost):
    try:
        # Prepare update fields
        update_data = openingcash_patch.dict(exclude_unset=True)
        update_data["updatedDate"] = datetime.utcnow()

        # Try to update by MongoDB _id first
        if ObjectId.is_valid(record_id):
            result = get_opening_cash_collection().update_one(
                {"_id": ObjectId(record_id)},
                {"$set": update_data}
            )
            if result.modified_count > 0:
                updated = get_opening_cash_collection().find_one({"_id": ObjectId(record_id)})
                updated["systemOpenCashId"] = str(updated["_id"])
                del updated["_id"]
                return OpeningCash(**updated)

        # If not found by _id, try by systemOpenCashId
        result = get_opening_cash_collection().update_one(
            {"systemOpenCashId": record_id},
            {"$set": update_data}
        )
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="OpeningCash not found")

        updated = get_opening_cash_collection().find_one({"systemOpenCashId": record_id})
        if not updated:
            raise HTTPException(status_code=404, detail="OpeningCash not found after update")

        updated["systemOpenCashId"] = str(updated.get("_id", record_id))
        if "_id" in updated:
            del updated["_id"]
        return OpeningCash(**updated)
    except Exception as e:
        logging.error(f"Error updating OpeningCash: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

# ## Delete an OpeningCash
# @router.delete("/{record_id}")
# async def delete_openingcash(record_id: str):
#     try:
#         # Try to delete by MongoDB _id first
#         if ObjectId.is_valid(record_id):
#             result = get_opening_cash_collection().delete_one({"_id": ObjectId(record_id)})
#             if result.deleted_count > 0:
#                 return {"message": "OpeningCash deleted successfully"}

#         # If not found by _id, try by systemOpenCashId
#         result = get_opening_cash_collection().delete_one({"systemOpenCashId": record_id})
#         if result.deleted_count == 0:
#             raise HTTPException(status_code=404, detail="OpeningCash not found")
#         return {"message": "OpeningCash deleted successfully"}
#     except Exception as e:
#         logging.error(f"Error deleting OpeningCash: {e}")
#         raise HTTPException(status_code=500, detail="Internal Server Error")
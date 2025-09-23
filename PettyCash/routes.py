import logging
from datetime import datetime
from typing import List
from bson import ObjectId
from fastapi import APIRouter, HTTPException, status
from PettyCash.utils import get_petty_cash_collection
from PettyCash.models import PettyCash, PettyCashPost

router = APIRouter()

## Get All PettyCash records in LIFO order
@router.get("/", response_model=List[PettyCash])
async def get_all_petty_cash():
    try:
        petty_cash_records = list(get_petty_cash_collection().find().sort("createdDate", -1))
        petty_cash_store = []
        
        for record_data in petty_cash_records:
            record_data["pettyCashId"] = str(record_data["_id"])  # Map _id to pettyCashId
            del record_data["_id"]  # Remove _id to match Pydantic model
            petty_cash_store.append(PettyCash(**record_data))
        
        return petty_cash_store
    except Exception as e:
        logging.error(f"Error fetching PettyCash records: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

## Create a new PettyCash record
@router.post("/", response_model=str, status_code=status.HTTP_201_CREATED)
async def create_petty_cash(petty_cash_data: PettyCashPost):
    try:
        new_record = petty_cash_data.dict()
        new_record["createdDate"] = datetime.utcnow()
        
        result = get_petty_cash_collection().insert_one(new_record)
        return str(result.inserted_id)  # Return the MongoDB _id
    except Exception as e:
        logging.error(f"Error creating PettyCash record: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

## Get a specific PettyCash by ID
@router.get("/{record_id}", response_model=PettyCash)
async def get_petty_cash_by_id(record_id: str):
    try:
        # First try to find by MongoDB _id
        if ObjectId.is_valid(record_id):
            petty_cash = get_petty_cash_collection().find_one({"_id": ObjectId(record_id)})
            if petty_cash:
                petty_cash["pettyCashId"] = str(petty_cash["_id"])
                del petty_cash["_id"]
                return PettyCash(**petty_cash)
        
        # If not found by _id, try by pettyCashId
        petty_cash = get_petty_cash_collection().find_one({"pettyCashId": record_id})
        if petty_cash:
            petty_cash["pettyCashId"] = str(petty_cash.get("_id", record_id))
            if "_id" in petty_cash:
                del petty_cash["_id"]
            return PettyCash(**petty_cash)
        
        raise HTTPException(status_code=404, detail="PettyCash record not found")
    except Exception as e:
        logging.error(f"Error fetching PettyCash by ID: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

## Patch (Update) a PettyCash record
@router.patch("/{record_id}", response_model=PettyCash)
async def patch_petty_cash(record_id: str, petty_cash_patch: PettyCashPost):
    try:
        # Prepare update fields
        update_data = petty_cash_patch.dict(exclude_unset=True)
        update_data["updatedDate"] = datetime.utcnow()

        # Try to update by MongoDB _id first
        if ObjectId.is_valid(record_id):
            result = get_petty_cash_collection().update_one(
                {"_id": ObjectId(record_id)},
                {"$set": update_data}
            )
            if result.modified_count > 0:
                updated = get_petty_cash_collection().find_one({"_id": ObjectId(record_id)})
                updated["pettyCashId"] = str(updated["_id"])
                del updated["_id"]
                return PettyCash(**updated)

        # If not found by _id, try by pettyCashId
        result = get_petty_cash_collection().update_one(
            {"pettyCashId": record_id},
            {"$set": update_data}
        )
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="PettyCash record not found")

        updated = get_petty_cash_collection().find_one({"pettyCashId": record_id})
        if not updated:
            raise HTTPException(status_code=404, detail="PettyCash record not found after update")

        updated["pettyCashId"] = str(updated.get("_id", record_id))
        if "_id" in updated:
            del updated["_id"]
        return PettyCash(**updated)
    except Exception as e:
        logging.error(f"Error updating PettyCash record: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

# ## Delete a PettyCash record
# @router.delete("/{record_id}")
# async def delete_petty_cash(record_id: str):
#     try:
#         # Try to delete by MongoDB _id first
#         if ObjectId.is_valid(record_id):
#             result = get_petty_cash_collection().delete_one({"_id": ObjectId(record_id)})
#             if result.deleted_count > 0:
#                 return {"message": "PettyCash record deleted successfully"}

#         # If not found by _id, try by pettyCashId
#         result = get_petty_cash_collection().delete_one({"pettyCashId": record_id})
#         if result.deleted_count == 0:
#             raise HTTPException(status_code=404, detail="PettyCash record not found")
#         return {"message": "PettyCash record deleted successfully"}
#     except Exception as e:
#         logging.error(f"Error deleting PettyCash record: {e}")
#         raise HTTPException(status_code=500, detail="Internal Server Error")
import logging
from datetime import datetime
from typing import List
from bson import ObjectId
from fastapi import APIRouter, HTTPException, status
from .utils import get_whatsApp_collection
from .models import WhatsApp, WhatsAppPost

router = APIRouter()

## Get All WhatsApp entries in FIFO order
@router.get("/", response_model=List[WhatsApp])
async def get_all_whatsapp_entries():
    try:
        # Fetch entries sorted by createdDate in ascending order (FIFO)
        entries = list(get_whatsApp_collection().find().sort("createdDate", 1))
        whatsapp_store = []
        
        for entry_data in entries:
            entry_data["whatsAppId"] = str(entry_data["_id"])  # Convert ObjectId to str
            del entry_data["_id"]  # Remove _id to match Pydantic model
            whatsapp_store.append(WhatsApp(**entry_data))  # Create WhatsApp object
        
        return whatsapp_store
    except Exception as e:
        logging.error(f"Error occurred while fetching WhatsApp entries: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

## Create a new WhatsApp entry
@router.post("/", response_model=str, status_code=status.HTTP_201_CREATED)
async def create_whatsapp_entry(whatsapp_data: WhatsAppPost):
    try:
        new_entry = whatsapp_data.dict()
        new_entry["createdDate"] = datetime.utcnow()  # Automatically set createdDate
        
        result = get_whatsApp_collection().insert_one(new_entry)
        return str(result.inserted_id)
    except Exception as e:
        logging.error(f"Error occurred: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

## Get a specific WhatsApp entry by ID
@router.get("/{whatsapp_id}", response_model=WhatsApp)
async def get_whatsapp_entry_by_id(whatsapp_id: str):
    entry = get_whatsApp_collection().find_one({"_id": ObjectId(whatsapp_id)})
    if entry:
        entry["whatsAppId"] = str(entry["_id"])
        del entry["_id"]
        return WhatsApp(**entry)
    else:
        raise HTTPException(status_code=404, detail="WhatsApp entry not found")

## Patch (Update) a WhatsApp entry
@router.patch("/{whatsapp_id}", response_model=WhatsApp)
async def patch_whatsapp_entry(whatsapp_id: str, whatsapp_patch: WhatsAppPost):
    try:
        existing_entry = get_whatsApp_collection().find_one({"_id": ObjectId(whatsapp_id)})
        if not existing_entry:
            raise HTTPException(status_code=404, detail="WhatsApp entry not found")
        
        updated_fields = {
            key: value for key, value in whatsapp_patch.dict(exclude_unset=True).items() if value is not None
        }
        
        updated_fields["updatedDate"] = datetime.utcnow()  # Automatically update updatedDate
        
        if updated_fields:
            result = get_whatsApp_collection().update_one(
                {"_id": ObjectId(whatsapp_id)}, {"$set": updated_fields}
            )
            if result.modified_count == 0:
                raise HTTPException(status_code=500, detail="Failed to update WhatsApp entry")
        
        updated_entry = get_whatsApp_collection().find_one({"_id": ObjectId(whatsapp_id)})
        updated_entry["whatsAppId"] = str(updated_entry["_id"])
        del updated_entry["_id"]
        return WhatsApp(**updated_entry)
    except Exception as e:
        logging.error(f"Error occurred while updating WhatsApp entry: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

# ## Delete a WhatsApp entry
# @router.delete("/{whatsapp_id}")
# async def delete_whatsapp_entry(whatsapp_id: str):
#     result = get_whatsApp_collection().delete_one({"_id": ObjectId(whatsapp_id)})
#     if result.deleted_count == 0:
#         raise HTTPException(status_code=404, detail="WhatsApp entry not found")
#     return {"message": "WhatsApp entry deleted successfully"}
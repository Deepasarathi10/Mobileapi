import logging
from fastapi import APIRouter, HTTPException,status
from bson import ObjectId
from typing import List, Dict, Any
from meterdetailsapi.models import Item, ItemGet
from meterdetailsapi.utils import  getmeters

router = APIRouter()

@router.get("/", response_model=List[ItemGet])
async def get_all_vendor():
    meter = list(getmeters().find())
    meterstore = []
    for meter in meter:
        meter["id"] = str(meter["_id"])
        meterstore.append(ItemGet(**meter))
    return meterstore

@router.post("/", response_model=str,status_code=status.HTTP_201_CREATED)
async def create_reading(meter_data: Item):
    try:
        new_meter = meter_data.dict()
        
        result = getmeters().insert_one(new_meter)
        return str(result.inserted_id)
    
    except Exception as e:
        logging.error(f"Error occurred: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
@router.patch("/{item_id}", response_model=Item)
async def patch_meter(item_id: str, meter_patch: Item):
    try:
        # Check if the meter exists
        existing_meter = getmeters().find_one({"_id": ObjectId(item_id)})
        if not existing_meter:
            raise HTTPException(status_code=404, detail="Meter not found")

        # Prepare updated fields, excluding any unset fields
        updated_fields = {key: value for key, value in meter_patch.dict(exclude_unset=True).items() if value is not None}

        # Log the updated fields
        logging.info(f"Updating meter ID {item_id} with fields: {updated_fields}")

        # Update the meter if there are fields to update
        if updated_fields:
            result = getmeters().update_one({"_id": ObjectId(item_id)}, {"$set": updated_fields})
            logging.info(f"Update result for meter ID {item_id}: {result.raw_result}")

            if result.modified_count == 0:
                logging.warning(f"No documents were modified for meter ID: {item_id}")
                raise HTTPException(status_code=500, detail="Failed to update meter")

        # Retrieve the updated meter
        updated_meter = getmeters().find_one({"_id": ObjectId(item_id)})
        if updated_meter is None:
            raise HTTPException(status_code=404, detail="Meter not found after update")

        updated_meter["id"] = str(updated_meter["_id"])  # Convert ObjectId to string
        return updated_meter

    except Exception as e:
        logging.error(f"Error occurred while patching meter: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

  
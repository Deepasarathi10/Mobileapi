
from fastapi import APIRouter, HTTPException,status
from bson import ObjectId  # Import ObjectId here
from pydantic import BaseModel
from typing import List, Optional
from .models import EPPrice, EppriceGet
from eppricedetails.utils import geteppricecollection
import logging

router = APIRouter()

@router.post("/", response_model=str,status_code=status.HTTP_201_CREATED)
async def create_reading(ep_price: EPPrice):
    try:
        ep_price = ep_price.dict()
        
        result =geteppricecollection().insert_one(ep_price)
        return str(result.inserted_id)
    
    except Exception as e:
        logging.error(f"Error occurred: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    

@router.get("/",response_model=List[EppriceGet])
async def get_epprice():
   epprices = list(geteppricecollection().find())
   prices = []
   for price in epprices:
        price["id"] = str(price["_id"])
        prices.append(EppriceGet(**price))
   return prices

@router.patch("/{ep_price_id}")
async def patch_reading(ep_price_id: str, read_patch: EppriceGet):
    try:
        existing_reading = geteppricecollection().find_one({"_id": ObjectId(ep_price_id)})
        if not existing_reading:
            raise HTTPException(status_code=404, detail="reading not found")

        updated_fields = {key: value for key, value in read_patch.dict(exclude_unset=True).items() if value is not None}

        if updated_fields:
            result = geteppricecollection().update_one({"_id": ObjectId(ep_price_id)}, {"$set": updated_fields})
            if result.modified_count == 0:
                raise HTTPException(status_code=500, detail="Failed to update vendor")

        updated_vendor = geteppricecollection().find_one({"_id": ObjectId(ep_price_id)})
        updated_vendor["_id"] = str(updated_vendor["_id"])
        return updated_vendor
    except Exception as e:
        logging.error(f"Error occurred while patching vendor: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


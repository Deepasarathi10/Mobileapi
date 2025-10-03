
import logging
from datetime import datetime
from typing import List
from bson import ObjectId
from fastapi import APIRouter, HTTPException, status
from .utils import get_amount_collection
from .models import AdvanceAmount, AdvanceAmountPost

router = APIRouter()

## Get All Amounts (LIFO Order)
@router.get("/", response_model=List[AdvanceAmount])
async def get_all_amounts():
    try:
        # Fetch amounts sorted by createdDate in descending order (LIFO)
        amounts = await get_amount_collection().find().sort("createdDate", -1).to_list(length=None)
        amount_store = []
        
        for amount_data in amounts:
            amount_data["amountId"] = str(amount_data["_id"])  # Convert ObjectId to str
            del amount_data["_id"]  # Remove _id to match Pydantic model
            amount_store.append(AdvanceAmount(**amount_data))  # Create AdvanceAmount object
        
        return amount_store
    except Exception as e:
        logging.error(f"Error occurred while fetching amounts: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

## Create a new Amount
@router.post("/", response_model=str, status_code=status.HTTP_201_CREATED)
async def create_amount(amount_data: AdvanceAmountPost):
    try:
        new_amount = amount_data.dict()
        new_amount["createdDate"] = datetime.utcnow()  # Automatically set createdDate
        
        result = await get_amount_collection().insert_one(new_amount)
        return str(result.inserted_id)
    except Exception as e:
        logging.error(f"Error occurred: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

## Get a specific Amount by ID
@router.get("/{amount_id}", response_model=AdvanceAmount)
async def get_amount_by_id(amount_id: str):
    try:
        amount = await get_amount_collection().find_one({"_id": ObjectId(amount_id)})
        if amount:
            amount["amountId"] = str(amount["_id"])
            del amount["_id"]
            return AdvanceAmount(**amount)
        else:
            raise HTTPException(status_code=404, detail="Amount not found")
    except Exception as e:
        logging.error(f"Error occurred while fetching amount by ID: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

## Patch (Update) an Amount
@router.patch("/{amount_id}", response_model=AdvanceAmount)
async def patch_amount(amount_id: str, amount_patch: AdvanceAmountPost):
    try:
        existing_amount = await get_amount_collection().find_one({"_id": ObjectId(amount_id)})
        if not existing_amount:
            raise HTTPException(status_code=404, detail="Amount not found")
        
        updated_fields = {
            key: value for key, value in amount_patch.dict(exclude_unset=True).items() if value is not None
        }
        
        updated_fields["updatedDate"] = datetime.utcnow()  # Automatically update updatedDate
        
        if updated_fields:
            result = await get_amount_collection().update_one(
                {"_id": ObjectId(amount_id)}, {"$set": updated_fields}
            )
            if result.modified_count == 0:
                raise HTTPException(status_code=500, detail="Failed to update Amount")
        
        updated_amount = await get_amount_collection().find_one({"_id": ObjectId(amount_id)})
        updated_amount["amountId"] = str(updated_amount["_id"])
        del updated_amount["_id"]
        return AdvanceAmount(**updated_amount)
    except Exception as e:
        logging.error(f"Error occurred while updating amount: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

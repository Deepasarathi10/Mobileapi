import logging
from datetime import datetime
from typing import List
from bson import ObjectId
from fastapi import APIRouter, HTTPException, status
from .utils import get_addon_collection  # You'll need to implement this
from .models import addOn, addOnPost

router = APIRouter()


purchase_category_counter = 0

def get_next_counter_value():
    counter_collection = get_addon_collection ().database["counters"]
    counter = counter_collection.find_one_and_update(
        {"_id": "categoryId"},
        {"$inc": {"sequence_value": 1}},
        upsert=True,
        return_document=True
    )
    return counter["sequence_value"]

def reset_counter():
    counter_collection = get_addon_collection ().database["counters"]
    counter_collection.update_one(
        
        {"_id": "categoryId"},
        {"$set": {"sequence_value": 0}},
        upsert=True
    )

def generate_random_id():
    counter_value = get_next_counter_value()
    return f"IC{counter_value:03d}"



## Get All AddOns (LIFO Order)
@router.get("/", response_model=List[addOn])
async def get_all_addons():
    try:
        # Fetch addons sorted by createdDate in descending order (LIFO)
        addons = list(get_addon_collection().find().sort("createdDate", -1))
        addon_store = []
        
        for addon_data in addons:
            addon_data["addOnId"] = str(addon_data["_id"])  # Convert ObjectId to str
            del addon_data["_id"]  # Remove _id to match Pydantic model
            addon_store.append(addOn(**addon_data))  # Create addOn object
        
        return addon_store
    except Exception as e:
        logging.error(f"Error occurred while fetching addons: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

## Create a new AddOn
@router.post("/", response_model=str, status_code=status.HTTP_201_CREATED)
async def create_addon(addon_data: addOnPost):
    try:

      # Generate randomId
        random_id = generate_random_id()

        new_addon = addon_data.dict()
        new_addon["createdDate"] = datetime.utcnow()  # Automatically set createdDate
        new_addon["randomId"] = str(())  # Generate a randomId
        new_addon["status"] = "active"
        new_addon['randomId'] = random_id
        
        result = get_addon_collection().insert_one(new_addon)
        return str(result.inserted_id)
    except Exception as e:
        logging.error(f"Error occurred: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

## Get a specific AddOn by ID
@router.get("/{addon_id}", response_model=addOn)
async def get_addon_by_id(addon_id: str):
    try:
        addon = get_addon_collection().find_one({"_id": ObjectId(addon_id)})
        if addon:
            addon["addOnId"] = str(addon["_id"])
            del addon["_id"]
            return addOn(**addon)
        else:
            raise HTTPException(status_code=404, detail="AddOn not found")
    except Exception as e:
        logging.error(f"Error occurred while fetching addon by ID: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

## Patch (Update) an AddOn
@router.patch("/{addon_id}", response_model=addOn)
async def patch_addon(addon_id: str, addon_patch: addOnPost):
    try:
        existing_addon = get_addon_collection().find_one({"_id": ObjectId(addon_id)})
        if not existing_addon:
            raise HTTPException(status_code=404, detail="AddOn not found")
        
        updated_fields = {
            key: value for key, value in addon_patch.dict(exclude_unset=True).items() if value is not None
        }
        
        updated_fields["updatedDate"] = datetime.utcnow()  # Automatically update updatedDate
        
        if updated_fields:
            result = get_addon_collection().update_one(
                {"_id": ObjectId(addon_id)}, {"$set": updated_fields}
            )
            if result.modified_count == 0:
                raise HTTPException(status_code=500, detail="Failed to update AddOn")
        
        updated_addon = get_addon_collection().find_one({"_id": ObjectId(addon_id)})
        updated_addon["addOnId"] = str(updated_addon["_id"])
        del updated_addon["_id"]
        return addOn(**updated_addon)
    except Exception as e:
        logging.error(f"Error occurred while updating addon: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

## Delete an AddOn
@router.delete("/{addon_id}")
async def delete_addon(addon_id: str):
    try:
        result = get_addon_collection().delete_one({"_id": ObjectId(addon_id)})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="AddOn not found")
        return {"message": "AddOn deleted successfully"}
    except Exception as e:
        logging.error(f"Error occurred while deleting addon: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
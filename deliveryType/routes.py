import logging
from datetime import datetime
from typing import List
import uuid
from bson import ObjectId
from fastapi import APIRouter, HTTPException, logger, status
from .utils import get_delivery_type_collection
from .models import DeliveryType, DeliveryTypePost

router = APIRouter()

## Get All DeliveryTypes in LIFO order
@router.get("/", response_model=List[DeliveryType])
async def get_all_DeliveryTypes():
    try:
        delivery_types = list(get_delivery_type_collection().find().sort("createdDate", -1))
        delivery_type_store = []

        for delivery_type_data in delivery_types:
            delivery_type_data["deliveryTypeId"] = str(delivery_type_data["_id"])  # Ensure correct field name
            del delivery_type_data["_id"]  # Remove raw MongoDB `_id` field
            
            delivery_type_store.append(DeliveryType(**delivery_type_data))  # Convert to Pydantic model
        
        return delivery_type_store
    except Exception as e:
        logging.error(f"Error occurred while fetching DeliveryTypes: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


## Create a new DeliveryType
@router.post("/", response_model=str, status_code=status.HTTP_201_CREATED)
async def create_DeliveryType(delivery_type_data: DeliveryTypePost):
    try:
        # Convert Pydantic model to dict
        new_delivery_type = delivery_type_data.dict()
        
        # Generate random ID
        new_delivery_type["randomId"] = f"DT-{uuid.uuid4().hex[:8].upper()}"
        
        # Add timestamp (using correct datetime usage)
        new_delivery_type["createdDate"] = datetime.now().isoformat()
        
        # Insert into database
        result = get_delivery_type_collection().insert_one(new_delivery_type)
        
        # Return the randomId
        return new_delivery_type["randomId"]
        
    except Exception as e:
        logger.error(f"Error creating delivery type: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create delivery type"
        )


## Get a specific DeliveryType by ID
@router.get("/{DeliveryType_id}", response_model=DeliveryType)
async def get_DeliveryType_by_id(DeliveryType_id: str):
    delivery_type_data = get_delivery_type_collection().find_one({"_id": ObjectId(DeliveryType_id)})
    if delivery_type_data:
        delivery_type_data["DeliveryTypeId"] = str(delivery_type_data["_id"])
        del delivery_type_data["_id"]
        return DeliveryType(**delivery_type_data)
    else:
        raise HTTPException(status_code=404, detail="DeliveryType not found")

## Patch (Update) a DeliveryType
@router.patch("/{DeliveryType_id}", response_model=DeliveryType)
async def patch_DeliveryType(DeliveryType_id: str, delivery_type_patch: DeliveryTypePost):
    try:
        existing_delivery_type = get_delivery_type_collection().find_one({"_id": ObjectId(DeliveryType_id)})
        if not existing_delivery_type:
            raise HTTPException(status_code=404, detail="DeliveryType not found")
        
        updated_fields = {
            key: value for key, value in delivery_type_patch.model_dump(exclude_unset=True).items() if value is not None
        }
        
        updated_fields["updatedDate"] = datetime.utcnow()  # Automatically update updatedDate
        
        if updated_fields:
            result = get_delivery_type_collection().update_one(
                {"_id": ObjectId(DeliveryType_id)}, {"$set": updated_fields}
            )
            if result.modified_count == 0:
                raise HTTPException(status_code=500, detail="Failed to update DeliveryType")
        
        updated_delivery_type = get_delivery_type_collection().find_one({"_id": ObjectId(DeliveryType_id)})
        updated_delivery_type["DeliveryTypeId"] = str(updated_delivery_type["_id"])
        del updated_delivery_type["_id"]
        return DeliveryType(**updated_delivery_type)
    except Exception as e:
        logging.error(f"Error occurred while updating DeliveryType: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

## Activate a DeliveryType
@router.patch("/{DeliveryType_id}/activate", response_model=DeliveryType)
async def activate_DeliveryType(DeliveryType_id: str):
    try:
        collection = get_delivery_type_collection()

        # Ensure the given DeliveryType exists
        existing_delivery_type = collection.find_one({"_id": ObjectId(DeliveryType_id)})
        if not existing_delivery_type:
            raise HTTPException(status_code=404, detail="DeliveryType not found")

        # Activate the selected DeliveryType
        collection.update_one(
            {"_id": ObjectId(DeliveryType_id)}, {"$set": {"status": "active", "updatedDate": datetime.utcnow()}}
        )

        # Fetch updated document
        updated_delivery_type = collection.find_one({"_id": ObjectId(DeliveryType_id)})
        updated_delivery_type["deliveryTypeId"] = str(updated_delivery_type["_id"])
        del updated_delivery_type["_id"]
        return DeliveryType(**updated_delivery_type)

    except Exception as e:
        logging.error(f"Error occurred while activating DeliveryType: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

## Deactivate a DeliveryType
@router.patch("/{DeliveryType_id}/deactivate", response_model=DeliveryType)
async def deactivate_DeliveryType(DeliveryType_id: str):
    try:
        collection = get_delivery_type_collection()

        # Ensure the given DeliveryType exists
        existing_delivery_type = collection.find_one({"_id": ObjectId(DeliveryType_id)})
        if not existing_delivery_type:
            raise HTTPException(status_code=404, detail="DeliveryType not found")

        # Deactivate the selected DeliveryType
        collection.update_one(
            {"_id": ObjectId(DeliveryType_id)}, {"$set": {"status": "deactivate", "updatedDate": datetime.utcnow()}}
        )

        # Fetch updated document
        updated_delivery_type = collection.find_one({"_id": ObjectId(DeliveryType_id)})
        updated_delivery_type["deliveryTypeId"] = str(updated_delivery_type["_id"])
        del updated_delivery_type["_id"]
        return DeliveryType(**updated_delivery_type)

    except Exception as e:
        logging.error(f"Error occurred while deactivating DeliveryType: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

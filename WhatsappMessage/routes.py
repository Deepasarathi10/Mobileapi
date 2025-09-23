

import logging
from datetime import datetime
from typing import List
from bson import ObjectId
from fastapi import APIRouter, HTTPException, status
from WhatsappMessage.utils import get_whatsapp_Message_collection
from WhatsappMessage.models import WhatsappMessage, WhatsappMessagePost

router = APIRouter()

# Get All WhatsApp messages in LIFO order
@router.get("/", response_model=List[WhatsappMessage])
async def get_all_whatsapp_messages():
    try:
        # Fetch messages sorted by createdDate in descending order (LIFO)
        messages = list(get_whatsapp_Message_collection().find().sort("createdDate", -1))
        whatsapp_messages = []
        
        for message_data in messages:
            message_data["whatsappMessageId"] = str(message_data["_id"])  # Convert ObjectId to str
            del message_data["_id"]  # Remove _id to match Pydantic model
            whatsapp_messages.append(WhatsappMessage(**message_data))  # Create WhatsappMessage object
        
        return whatsapp_messages
    except Exception as e:
        logging.error(f"Error occurred while fetching WhatsApp messages: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

# Create a new WhatsApp message
@router.post("/", response_model=str, status_code=status.HTTP_201_CREATED)
async def create_whatsapp_message(message_data: WhatsappMessagePost):
    try:
        new_message = message_data.dict()
        
        # Set default values if not provided in the request
        if new_message.get("createdDate") is None:
            new_message["createdDate"] = datetime.utcnow()
        
        if new_message.get("enable") is None:
            new_message["enable"] = False
        
        if new_message.get("status") is None:
            new_message["status"] = "active"
        
        result = get_whatsapp_Message_collection().insert_one(new_message)
        return str(result.inserted_id)
    except Exception as e:
        logging.error(f"Error occurred while creating WhatsApp message: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

# Get a specific WhatsApp message by ID
@router.get("/{message_id}", response_model=WhatsappMessage)
async def get_whatsapp_message_by_id(message_id: str):
    try:
        message = get_whatsapp_Message_collection().find_one({"_id": ObjectId(message_id)})
        if message:
            message["whatsappMessageId"] = str(message["_id"])
            del message["_id"]
            return WhatsappMessage(**message)
        else:
            raise HTTPException(status_code=404, detail="WhatsApp message not found")
    except Exception as e:
        logging.error(f"Error occurred while fetching WhatsApp message: {e}")
        raise HTTPException(status_code=400, detail="Invalid message ID format")

# Update a WhatsApp message
@router.patch("/{message_id}", response_model=WhatsappMessage)
async def update_whatsapp_message(message_id: str, message_patch: WhatsappMessagePost):
    try:
        existing_message = get_whatsapp_Message_collection().find_one({"_id": ObjectId(message_id)})
        if not existing_message:
            raise HTTPException(status_code=404, detail="WhatsApp message not found")
        
        # Get the current enable status
        current_enable_status = existing_message.get("enable", False)
        
        # Prepare update fields
        updated_fields = {
            key: value for key, value in message_patch.dict(exclude_unset=True).items() if value is not None
        }
        
        # Toggle the enable field if it's being updated
        if "enable" in updated_fields:
            updated_fields["enable"] = not current_enable_status
        
        # Always update the updatedDate field
        updated_fields["updatedDate"] = datetime.utcnow()
        
        if updated_fields:
            result = get_whatsapp_Message_collection().update_one(
                {"_id": ObjectId(message_id)}, {"$set": updated_fields}
            )
            if result.modified_count == 0:
                raise HTTPException(status_code=500, detail="Failed to update WhatsApp message")
        
        updated_message = get_whatsapp_Message_collection().find_one({"_id": ObjectId(message_id)})
        updated_message["whatsappMessageId"] = str(updated_message["_id"])
        del updated_message["_id"]
        return WhatsappMessage(**updated_message)
    except Exception as e:
        logging.error(f"Error occurred while updating WhatsApp message: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

# Toggle WhatsApp message enable status
@router.patch("/{message_id}/toggle", response_model=WhatsappMessage)
async def toggle_whatsapp_message_status(message_id: str):
    try:
        existing_message = get_whatsapp_Message_collection().find_one({"_id": ObjectId(message_id)})
        if not existing_message:
            raise HTTPException(status_code=404, detail="WhatsApp message not found")
        
        # Toggle the enable status
        new_enable_status = not existing_message.get("enable", False)
        
        # Update the message with the new enable status and updated date
        result = get_whatsapp_Message_collection().update_one(
            {"_id": ObjectId(message_id)},
            {
                "$set": {
                    "enable": new_enable_status,
                    "updatedDate": datetime.utcnow()
                }
            }
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=500, detail="Failed to toggle WhatsApp message status")
        
        # Return the updated message
        updated_message = get_whatsapp_Message_collection().find_one({"_id": ObjectId(message_id)})
        updated_message["whatsappMessageId"] = str(updated_message["_id"])
        del updated_message["_id"]
        return WhatsappMessage(**updated_message)
    except Exception as e:
        logging.error(f"Error occurred while toggling WhatsApp message status: {e}")
        raise HTTPException(status_code=400, detail="Invalid message ID format")

# # Delete a WhatsApp message
# @router.delete("/{message_id}")
# async def delete_whatsapp_message(message_id: str):
#     try:
#         result = get_whatsapp_Message_collection().delete_one({"_id": ObjectId(message_id)})
#         if result.deleted_count == 0:
#             raise HTTPException(status_code=404, detail="WhatsApp message not found")
#         return {"message": "WhatsApp message deleted successfully"}
#     except Exception as e:
#         logging.error(f"Error occurred while deleting WhatsApp message: {e}")
#         raise HTTPException(status_code=400, detail="Invalid message ID format")
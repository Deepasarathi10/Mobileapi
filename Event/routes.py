
import logging
from datetime import datetime
from typing import List
from bson import ObjectId
from fastapi import APIRouter, HTTPException, status
from .utils import get_event_collection
from .models import Event, EventPost

router = APIRouter()

## Get All Events in LIFO order
@router.get("/", response_model=List[Event])
async def get_all_events():
    try:
        # Fetch events sorted by createdDate in descending order (LIFO)
        events = list(get_event_collection().find().sort("createdDate", -1))
        event_store = []
        
        for event_data in events:
            event_data["eventId"] = str(event_data["_id"])  # Convert ObjectId to str
            del event_data["_id"]  # Remove _id to match Pydantic model
            event_store.append(Event(**event_data))  # Create Event object
        
        return event_store
    except Exception as e:
        logging.error(f"Error occurred while fetching events: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

## Create a new Event
@router.post("/", response_model=str, status_code=status.HTTP_201_CREATED)
async def create_event(event_data: EventPost):
    try:
        new_event = event_data.dict()
        new_event["createdDate"] = datetime.utcnow()  # Automatically set createdDate
        
        result = get_event_collection().insert_one(new_event)
        return str(result.inserted_id)
    except Exception as e:
        logging.error(f"Error occurred: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

## Get a specific Event by ID
@router.get("/{event_id}", response_model=Event)
async def get_event_by_id(event_id: str):
    event = get_event_collection().find_one({"_id": ObjectId(event_id)})
    if event:
        event["eventId"] = str(event["_id"])
        del event["_id"]
        return Event(**event)
    else:
        raise HTTPException(status_code=404, detail="Event not found")

## Patch (Update) an Event
@router.patch("/{event_id}", response_model=Event)
async def patch_event(event_id: str, event_patch: EventPost):
    try:
        existing_event = get_event_collection().find_one({"_id": ObjectId(event_id)})
        if not existing_event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        updated_fields = {
            key: value for key, value in event_patch.dict(exclude_unset=True).items() if value is not None
        }
        
        updated_fields["updatedDate"] = datetime.utcnow()  # Automatically update updatedDate
        
        if updated_fields:
            result = get_event_collection().update_one(
                {"_id": ObjectId(event_id)}, {"$set": updated_fields}
            )
            if result.modified_count == 0:
                raise HTTPException(status_code=500, detail="Failed to update Event")
        
        updated_event = get_event_collection().find_one({"_id": ObjectId(event_id)})
        updated_event["eventId"] = str(updated_event["_id"])
        del updated_event["_id"]
        return Event(**updated_event)
    except Exception as e:
        logging.error(f"Error occurred while updating event: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

# ## Delete an Event
# @router.delete("/{event_id}")
# async def delete_event(event_id: str):
#     result = get_event_collection().delete_one({"_id": ObjectId(event_id)})
#     if result.deleted_count == 0:
#         raise HTTPException(status_code=404, detail="Event not found")
#     return {"message": "Event deleted successfully"}
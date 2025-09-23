import logging
from fastapi import APIRouter, HTTPException, status, Query
from bson import ObjectId
from typing import List, Optional
from datetime import datetime
from .utils import get_stickercount_collection
from .models import StickercountPost, Stickercount

router = APIRouter()

@router.post("/", response_model=str, status_code=status.HTTP_201_CREATED)
async def create_stickercount(stickercount: StickercountPost):
    new_stickercount_data = stickercount.model_dump()

    # Convert date string (in 'DD-MM-YYYY') to datetime before inserting into MongoDB
    if 'date' in new_stickercount_data and new_stickercount_data['date']:
        try:
            # Parse the input date in 'DD-MM-YYYY' format
            new_stickercount_data['date'] = datetime.strptime(new_stickercount_data['date'], '%d-%m-%Y')
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Please use 'DD-MM-YYYY'.")

    # Insert the data into MongoDB
    result = get_stickercount_collection().insert_one(new_stickercount_data)
    return str(result.inserted_id)

@router.get("/", response_model=List[Stickercount])
async def get_stickercount_by_date(date: Optional[str] = Query(None, description="Date in 'DD-MM-YYYY' format")):
    query = {}

    # If date is provided, parse it to datetime and add to query
    if date:
        try:
            # Convert the input date string to a datetime object
            query_date = datetime.strptime(date, '%d-%m-%Y')
            query['date'] = query_date
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Please use 'DD-MM-YYYY'.")

    # Fetch stickercount entries filtered by the date (if provided)
    stickercount_entries = get_stickercount_collection().find(query)

    # Convert the date field back to 'DD-MM-YYYY' format for responses
    formatted_entries = []
    for doc in stickercount_entries:
        if 'date' in doc and isinstance(doc['date'], datetime):
            doc['date'] = doc['date'].strftime('%d-%m-%Y')
        formatted_entries.append(Stickercount(**convert_document(doc)))

    return formatted_entries

@router.get("/{stickercount_id}", response_model=Stickercount)
async def get_stickercount_by_id(stickercount_id: str):
    stickercount_data = get_stickercount_collection().find_one({"_id": ObjectId(stickercount_id)})
    if stickercount_data:
        return Stickercount(**convert_document(stickercount_data))
    else:
        raise HTTPException(status_code=404, detail="Stickercount entry not found")

@router.patch("/{stickercount_id}", response_model=Stickercount)
async def patch_stickercount(stickercount_id: str, stickercount_patch: StickercountPost):
    existing_stickercount_data = get_stickercount_collection().find_one({"_id": ObjectId(stickercount_id)})
    if not existing_stickercount_data:
        raise HTTPException(status_code=404, detail="Stickercount entry not found")

    # Update the document with only the fields that are set in stickercount_patch
    updated_fields = {k: v for k, v in stickercount_patch.dict(exclude_unset=True).items() if v is not None}

    # Convert date string to datetime if present
    if 'date' in updated_fields and updated_fields['date']:
        updated_fields['date'] = datetime.strptime(updated_fields['date'], '%d-%m-%y')

    if updated_fields:
        result = get_stickercount_collection().update_one({"_id": ObjectId(stickercount_id)}, {"$set": updated_fields})
        if result.modified_count == 0:
            raise HTTPException(status_code=500, detail="Failed to update Stickercount entry")

    # Fetch the updated document to return as response
    updated_stickercount = get_stickercount_collection().find_one({"_id": ObjectId(stickercount_id)})
    if updated_stickercount:
        return Stickercount(**convert_document(updated_stickercount))
    else:
        raise HTTPException(status_code=404, detail="Updated Stickercount entry not found")

@router.delete("/{stickercount_id}")
async def delete_stickercount(stickercount_id: str):
    result = get_stickercount_collection().delete_one({"_id": ObjectId(stickercount_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Stickercount entry not found")
    return {"message": "Stickercount deleted successfully"}

def convert_document(document):
    document['stickercountId'] = str(document.pop('_id'))
    return document

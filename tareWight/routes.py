from fastapi import APIRouter, HTTPException,status
from bson import ObjectId
from typing import List, Optional
from .utils import get_tare_collection
from .models import TareWeightPost, TareWeight

router = APIRouter()

@router.post("/", response_model=str,status_code=status.HTTP_201_CREATED)
async def create_tare(tare: TareWeightPost):
    new_tare_data = tare.dict()
    result = get_tare_collection().insert_one(new_tare_data)
    return str(result.inserted_id)

@router.get("/", response_model=List[TareWeight])
async def get_all_tare():
    tare_entries = list(get_tare_collection().find())
    return [TareWeight(**convert_document(doc)) for doc in tare_entries]

@router.get("/{tare_id}", response_model=TareWeight)
async def get_tare_by_id(tare_id: str):
    tare_data = get_tare_collection().find_one({"_id": ObjectId(tare_id)})
    if tare_data:
        return TareWeight(**convert_document(tare_data))
    else:
        raise HTTPException(status_code=404, detail="TareWeight entry not found")

@router.patch("/{tare_id}", response_model=TareWeight)
async def patch_tare(tare_id: str, tare_patch: TareWeightPost):
    existing_tare_data = get_tare_collection().find_one({"_id": ObjectId(tare_id)})
    if not existing_tare_data:
        raise HTTPException(status_code=404, detail="TareWeight entry not found")

    # Update the document with only the fields that are set in tare_patch
    updated_fields = {k: v for k, v in tare_patch.dict(exclude_unset=True).items() if v is not None}
    if updated_fields:
        result = get_tare_collection().update_one({"_id": ObjectId(tare_id)}, {"$set": updated_fields})
        if result.modified_count == 0:
            raise HTTPException(status_code=500, detail="Failed to update TareWeight entry")

    # Fetch the updated document to return as response
    updated_tare = get_tare_collection().find_one({"_id": ObjectId(tare_id)})
    if updated_tare:
        return TareWeight(**convert_document(updated_tare))
    else:
        raise HTTPException(status_code=404, detail="Updated TareWeight entry not found")

@router.delete("/{tare_id}")
async def delete_tare(tare_id: str):
    result = get_tare_collection().delete_one({"_id": ObjectId(tare_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="TareWeight entry not found")
    return {"message": "TareWeight deleted successfully"}

def convert_document(document):
    document['tareId'] = str(document.pop('_id'))
    return document

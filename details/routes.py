from fastapi import APIRouter, HTTPException
from typing import List
from bson import ObjectId
from pymongo import MongoClient
from .models import Details, DetailsPost, DetailsPatch
from .utils import get_details_collection
router = APIRouter()



@router.post("/", response_model=Details)
async def create_details(details: DetailsPost):
    new_data = details.dict()
    result = get_details_collection().insert_one(new_data)
    new_data['id'] = str(result.inserted_id)
    return new_data

@router.get("/", response_model=List[Details])
async def get_all_details():
    details_list = list(get_details_collection().find())
    return [Details(**detail, id=str(detail["_id"])) for detail in details_list]

@router.get("/{details_id}", response_model=Details)
async def get_details_by_id(details_id: str):
    detail = get_details_collection().find_one({"_id": ObjectId(details_id)})
    if detail is None:
        raise HTTPException(status_code=404, detail="Details not found")
    return Details(**detail, id=str(detail["_id"]))

@router.patch("/{details_id}", response_model=Details)
async def update_details(details_id: str, details_patch: DetailsPatch):
    updated_fields = {k: v for k, v in details_patch.dict(exclude_unset=True).items() if v is not None}
    if updated_fields:
        result = get_details_collection().update_one(
            {"_id": ObjectId(details_id)}, {"$set": updated_fields})
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="No details found to update")
    updated_detail = get_details_collection().find_one({"_id": ObjectId(details_id)})
    return Details(**updated_detail, id=str(updated_detail["_id"]))

@router.delete("/{details_id}")
async def delete_details(details_id: str):
    result = get_details_collection().delete_one({"_id": ObjectId(details_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Details not found")
    return {"message": "Details deleted successfully"}

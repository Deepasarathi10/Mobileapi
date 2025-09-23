from fastapi import APIRouter, HTTPException, Query, status
from bson import ObjectId
from typing import List
from .utils import get_country_collection
from .models import County, CountyPost
router = APIRouter()

@router.post("/", response_model=str, status_code=status.HTTP_201_CREATED)
async def create_county(data: CountyPost):
    new_data = data.model_dump()
    result = get_country_collection().insert_one(new_data)
    return str(result.inserted_id)

@router.get("/", response_model=List[County])
async def get_all_counties(skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100)):
    """
    Fetch county data with pagination.
    - `skip`: Number of records to skip (default: 0)
    - `limit`: Maximum number of records to return (default: 50, max: 100)
    """
    entries = list(get_country_collection().find().skip(skip).limit(limit))
    return [County(**convert_document(doc)) for doc in entries]


@router.get("/{county_id}", response_model=County)
async def get_county_by_id(county_id: str):
    doc = get_country_collection().find_one({"_id": ObjectId(county_id)})
    if doc:
        return County(**convert_document(doc))
    else:
        raise HTTPException(status_code=404, detail="County data not found")

@router.patch("/{county_id}", response_model=County)
async def patch_county(county_id: str, update: CountyPost):
    doc = get_country_collection().find_one({"_id": ObjectId(county_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="County data not found")

    updated_fields = {k: v for k, v in update.model_dump(exclude_unset=True).items() if v is not None}
    if updated_fields:
        result = get_country_collection().update_one({"_id": ObjectId(county_id)}, {"$set": updated_fields})
        if result.modified_count == 0:
            raise HTTPException(status_code=500, detail="Failed to update county data")

    updated_doc = get_country_collection().find_one({"_id": ObjectId(county_id)})
    if updated_doc:
        return County(**convert_document(updated_doc))
    else:
        raise HTTPException(status_code=404, detail="Updated county data not found")

def convert_document(document):
    document['countyId'] = str(document.pop('_id'))
    return document

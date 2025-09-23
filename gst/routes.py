from fastapi import APIRouter, HTTPException
from fastapi import APIRouter, status
from bson import ObjectId
from typing import List,Optional
from .utils import get_gst_collection
from .models import GstPost,Gst
router = APIRouter()

@router.post("/", response_model=str, status_code=status.HTTP_201_CREATED)
async def create_gst(gst: GstPost):
    new_gst_data = gst.model_dump()
    result = get_gst_collection().insert_one(new_gst_data)
    return str(result.inserted_id)

@router.get("/", response_model=List[Gst])
async def get_all_gst():
    gst_entries = list(get_gst_collection().find())
    return [Gst(**convert_document(doc)) for doc in gst_entries]

@router.get("/{gst_id}", response_model=Gst)
async def get_gst_by_id(gst_id: str):
    gst_data = get_gst_collection().find_one({"_id": ObjectId(gst_id)})
    if gst_data:
        return Gst(**convert_document(gst_data))
    else:
        raise HTTPException(status_code=404, detail="GST entry not found")

@router.patch("/{gst_id}", response_model=Gst)
async def patch_gst(gst_id: str, gst_patch: GstPost):
    existing_gst_data = get_gst_collection().find_one({"_id": ObjectId(gst_id)})
    if not existing_gst_data:
        raise HTTPException(status_code=404, detail="GST entry not found")

    # Update the document with only the fields that are set in gst_patch
    updated_fields = {k: v for k, v in gst_patch.dict(exclude_unset=True).items() if v is not None}
    if updated_fields:
        result = get_gst_collection().update_one({"_id": ObjectId(gst_id)}, {"$set": updated_fields})
        if result.modified_count == 0:
            raise HTTPException(status_code=500, detail="Failed to update GST entry")

    # Fetch the updated document to return as response
    updated_gst = get_gst_collection().find_one({"_id": ObjectId(gst_id)})
    if updated_gst:
        return Gst(**convert_document(updated_gst))
    else:
        raise HTTPException(status_code=404, detail="Updated GST entry not found")


@router.delete("/{gst_id}")
async def delete_gst(gst_id: str):
    result = get_gst_collection().delete_one({"_id": ObjectId(gst_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="GST entry not found")
    return {"message": "GST deleted successfully"}

def convert_document(document):
    document['gstId'] = str(document.pop('_id'))
    return document

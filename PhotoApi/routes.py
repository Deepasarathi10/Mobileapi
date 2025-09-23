
from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File
from pymongo import MongoClient
from bson import ObjectId
from fastapi.responses import StreamingResponse
import io
from PIL import Image
import numpy as np

router = APIRouter()

# MongoDB connection and collection getter
def get_expensephoto_collection():
    client = MongoClient("mongodb://admin:YenE580nOOUE6cDhQERP@194.233.78.90:27017/admin?appName=mongosh+2.1.1&authSource=admin&authMechanism=SCRAM-SHA-256&replicaSet=yenerp-cluster")
    db = client["dailyactivities"]
    return db['photosApi']

@router.post("/")
async def upload_photo(file: UploadFile = File(...), custom_id: Optional[str] = None):
    try:
        # Read the contents of the uploaded file
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))

        # Compress the image
        compressed_image_io = io.BytesIO()
        image.save(compressed_image_io, format='JPEG', quality=25)  # Adjust quality as needed
        compressed_image_io.seek(0)  # Reset IO stream position

        # Check if custom_id is provided, otherwise generate a new ObjectId
        if custom_id:
            custom_object_id = custom_id
        else:
            custom_object_id = str(ObjectId())

        # Insert the compressed file contents into MongoDB
        result = get_expensephoto_collection().insert_one({
            "_id": custom_object_id,
            "filename": file.filename,
            "content": compressed_image_io.getvalue()
        })

        return {"filename": file.filename, "id": custom_object_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.get("/{photo_id}")
async def get_photo(photo_id: str):
    try:
        photo_document = get_expensephoto_collection().find_one({"_id": photo_id})

        if photo_document:
            content = photo_document["content"]
            return StreamingResponse(io.BytesIO(content), media_type="image/jpeg")

        else:
            raise HTTPException(status_code=404, detail="Photo not found")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/{photo_id}")
async def update_photo(photo_id: str, file: UploadFile = File(...)):
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))

        # Compress the image
        compressed_image_io = io.BytesIO()
        image.save(compressed_image_io, format='JPEG', quality=25)  # Adjust quality as needed
        compressed_image_io.seek(0)

        result = get_expensephoto_collection().update_one(
            {"_id": photo_id},
            {"$set": {
                "filename": file.filename,
                "content": compressed_image_io.getvalue()
            }}
        )

        if result.matched_count == 1:
            return {"message": "Photo updated successfully"}
        else:
            raise HTTPException(status_code=404, detail="Photo not found")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{photo_id}")
async def delete_photo(photo_id: str):
    try:
        result = get_expensephoto_collection().delete_one({"_id": photo_id})

        if result.deleted_count == 1:
            return {"message": "Photo deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Photo not found")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

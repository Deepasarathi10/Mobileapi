import os
from fastapi import APIRouter, File, Form, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorClient
from uuid import uuid4
from pathlib import Path
from bson.objectid import ObjectId

# Router setup
router = APIRouter()

# MongoDB connection and collection
def get_media_collection():
    client = AsyncIOMotorClient(
        "mongodb://admin:YenE580nOOUE6cDhQERP@194.233.78.90:27017/admin"
        "?appName=mongosh+2.1.1&authSource=admin&authMechanism=SCRAM-SHA-256&replicaSet=yenerp-cluster"
    )
    db = client['reactfluttertest']
    return db['audioFiles']  # Collection to store audio files metadata


# Create the folder path for storing audio files
UPLOAD_FOLDER = "./uploads/audio"
Path(UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)  # Ensure folder exists


@router.post("/upload_audio")
async def upload_audio(
    file: UploadFile = File(...),  # Audio file
    custom_id: str = Form(...),    # Custom ID
):
    try:
        if not custom_id:
            raise HTTPException(status_code=400, detail="Custom ID is required.")
        
        # Generate a unique filename for the audio file to avoid conflicts
        unique_filename = f"{uuid4().hex}_{file.filename}"
        file_path = os.path.join(UPLOAD_FOLDER, unique_filename)

        # Save the audio file to the server's file system
        with open(file_path, "wb") as f:
            f.write(await file.read())

        # Insert the file path and metadata into the database
        media_collection = get_media_collection()
        await media_collection.insert_one({
            "_id": custom_id,  # Use the custom_id as the file's _id
            "type": "audio",
            "filename": file.filename,
            "file_path": file_path,
            "custom_id": custom_id
        })

        return JSONResponse(content={
            "_id": custom_id,
            "audio_url": f"/media/{custom_id}/audio"
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading audio: {str(e)}")


@router.get("/media/{custom_id}/audio")
async def get_audio(custom_id: str):
    try:
        media_collection = get_media_collection()
        media_document = await media_collection.find_one({"custom_id": custom_id})

        if not media_document or media_document.get("type") != "audio":
            raise HTTPException(status_code=404, detail="Audio not found for this custom_id")

        file_path = media_document["file_path"]

        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Audio file not found on the server")

        with open(file_path, "rb") as f:
            audio_data = f.read()

        return JSONResponse(content={
            "filename": media_document["filename"],
            "content_type": "audio/mpeg",
            "content": audio_data.hex()
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching audio: {str(e)}")


@router.patch("/media/{current_custom_id}/audio")
async def patch_audio_id(
    current_custom_id: str,  
    new_custom_id: str = Form(...),  
):
    try:
        media_collection = get_media_collection()

        existing_document = await media_collection.find_one({"custom_id": current_custom_id})
        if not existing_document:
            raise HTTPException(status_code=404, detail="Audio with the provided custom ID not found.")

        if await media_collection.find_one({"custom_id": new_custom_id}):
            raise HTTPException(status_code=400, detail="The new custom ID is already in use.")

        result = await media_collection.update_one(
            {"custom_id": current_custom_id},
            {"$set": {"custom_id": new_custom_id}}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Failed to update custom ID.")

        return JSONResponse(content={
            "message": "Custom ID updated successfully.",
            "old_custom_id": current_custom_id,
            "new_custom_id": new_custom_id,
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating custom ID: {str(e)}")

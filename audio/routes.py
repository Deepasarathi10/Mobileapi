import os
from fastapi import APIRouter, File, Form, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from pymongo import MongoClient
from uuid import uuid4
from pathlib import Path

# Router setup
router = APIRouter()

# MongoDB connection and collection
def get_media_collection():
    client = MongoClient("mongodb://admin:YenE580nOOUE6cDhQERP@194.233.78.90:27017/admin?appName=mongosh+2.1.1&authSource=admin&authMechanism=SCRAM-SHA-256&replicaSet=yenerp-cluster")
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
        media_collection.insert_one({
            "_id": custom_id,  # Use the custom_id as the file's _id
            "type": "audio",
            "filename": file.filename,
            "file_path": file_path,  # Store file path in the DB
            "custom_id": custom_id  # Save the custom_id as reference
        })

        # Return a URL to access the audio file
        return JSONResponse(content={
            "_id": custom_id,
            "audio_url": f"/media/{custom_id}/audio"
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading audio: {str(e)}")


@router.get("/media/{custom_id}/audio")
async def get_audio(custom_id: str):
    try:
        # Find the media document for the given custom_id
        media_collection = get_media_collection()
        media_document = media_collection.find_one({"custom_id": custom_id})

        if not media_document or media_document.get("type") != "audio":
            raise HTTPException(status_code=404, detail="Audio not found for this custom_id")

        # Retrieve the file path from the database
        file_path = media_document["file_path"]

        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Audio file not found on the server")

        # Return the audio file's content as a response
        with open(file_path, "rb") as f:
            audio_data = f.read()

        return JSONResponse(content={
            "filename": media_document["filename"],
            "content_type": "audio/mpeg",  # or use the content_type from the database if needed
            "content": audio_data.hex()  # Returning binary data as hex (base64 can also be used)
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching audio: {str(e)}")

@router.patch("/media/{current_custom_id}/audio")
async def patch_audio_id(
    current_custom_id: str,  # Existing custom ID
    new_custom_id: str = Form(...),  # New custom ID
):
    try:
        # Get the media collection
        media_collection = get_media_collection()

        # Check if the current custom ID exists
        existing_document = media_collection.find_one({"custom_id": current_custom_id})
        if not existing_document:
            raise HTTPException(status_code=404, detail="Audio with the provided custom ID not found.")

        # Check if the new custom ID is already in use
        if media_collection.find_one({"custom_id": new_custom_id}):
            raise HTTPException(status_code=400, detail="The new custom ID is already in use.")

        # Update the custom ID in the database
        result = media_collection.update_one(
            {"custom_id": current_custom_id},  # Filter by current custom ID
            {"$set": {"custom_id": new_custom_id}}  # Update to new custom ID
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Failed to update custom ID.")

        # Return a success response
        return JSONResponse(content={
            "message": "Custom ID updated successfully.",
            "old_custom_id": current_custom_id,
            "new_custom_id": new_custom_id,
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating custom ID: {str(e)}")

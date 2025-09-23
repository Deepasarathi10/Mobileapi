import io
import os
from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from bson import ObjectId
import requests
from ftplib import FTP, error_perm
from ngxwebiste_photos.utils import get_ngxphotos_collection

# FTP Configuration
FTP_HOST = "194.233.78.90"
FTP_USER = "yenerp.com_thys677l7kc"
FTP_PASSWORD = "PUTndhivxi6x94^%"
FTP_UPLOAD_DIR = "/httpdocs/share/upload/ngxwebsite/photos"
BASE_URL = "https://yenerp.com/share/upload"
# Local temp folder for processing
LOCAL_UPLOAD_FOLDER = "./temp_uploads"
os.makedirs(LOCAL_UPLOAD_FOLDER, exist_ok=True)

# MongoDB Collection
photos_collection = get_ngxphotos_collection()

# Initialize router
router = APIRouter()

async def upload_to_ftp(file_path: str, remote_filename: str):
    """Uploads a file to the FTP server."""
    try:
        ftp = FTP()
        ftp.set_pasv(True)
        ftp.connect(FTP_HOST, 21, timeout=10)
        ftp.login(FTP_USER, FTP_PASSWORD)

        # Ensure directory exists
        folders = FTP_UPLOAD_DIR.strip("/").split("/")
        for folder in folders:
            try:
                ftp.cwd(folder)
            except error_perm:
                ftp.mkd(folder)
                ftp.cwd(folder)

        # Upload file
        with open(file_path, "rb") as f:
            ftp.storbinary(f"STOR {remote_filename}", f)
        ftp.quit()
        return f"{BASE_URL}/ngxwebsite/photos/{remote_filename}"
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"FTP upload failed: {str(e)}")

@router.post("/photo/upload")
async def upload_photo(file: UploadFile = File(...), custom_id: Optional[str] = None):
    try:
        contents = await file.read()

        # Use custom_id if provided, otherwise generate a new ObjectId
        custom_object_id = custom_id if custom_id else str(ObjectId())

        # Save the original image locally before FTP upload
        local_filename = f"{custom_object_id}{os.path.splitext(file.filename)[1]}"
        local_path = os.path.join(LOCAL_UPLOAD_FOLDER, local_filename)

        with open(local_path, "wb") as f:
            f.write(contents)

        # Upload the file to FTP
        ftp_url = await upload_to_ftp(local_path, local_filename)

        # Store file URL in MongoDB
        photos_collection.insert_one({
            "_id": custom_object_id,
            "filename": file.filename,
            "url": ftp_url
        })

        # Remove the local file after upload
        os.remove(local_path)

        return {"filename": file.filename, "id": custom_object_id, "url": ftp_url}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/photo/view/{photo_id}")
async def get_photo(photo_id: str):
    try:
        # Find the image document in MongoDB
        photo_document = photos_collection.find_one({"_id": photo_id})
        if not photo_document:
            raise HTTPException(status_code=404, detail="Photo not found")

        # Fetch image from the URL stored in MongoDB
        image_url = photo_document["url"]
        response = requests.get(image_url, stream=True)
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to retrieve image")

        # Return the image as StreamingResponse
        return StreamingResponse(response.raw, media_type="image/jpeg")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/photo/view/{photo_id}")
async def update_photo(photo_id: str, file: UploadFile = File(...)):
    try:
        contents = await file.read()

        # Save locally before uploading to FTP
        local_filename = f"{photo_id}{os.path.splitext(file.filename)[1]}"
        local_path = os.path.join(LOCAL_UPLOAD_FOLDER, local_filename)

        with open(local_path, "wb") as f:
            f.write(contents)

        # Upload the file to FTP
        ftp_url = await upload_to_ftp(local_path, local_filename)

        # Update MongoDB with new URL
        result = photos_collection.update_one(
            {"_id": photo_id},
            {"$set": {"filename": file.filename, "url": ftp_url}}
        )

        # Remove the local file after upload
        os.remove(local_path)

        if result.matched_count == 1:
            return {"message": "Photo updated successfully", "url": ftp_url}
        else:
            raise HTTPException(status_code=404, detail="Photo not found")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

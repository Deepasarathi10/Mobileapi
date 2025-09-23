from typing import List
from fastapi import APIRouter, HTTPException
from bson import ObjectId
from facialRecognization.models import FacialRecognition, FacialRecognitionPost
from facialRecognization.utils import facial_recognition_collection
from fastapi import APIRouter, status


router = APIRouter()

# Function to convert values to strings or empty values
def convert_to_string_or_empty(data):
    if isinstance(data, list):
        return [str(value) if value is not None else "" for value in data]
    elif isinstance(data, (int, float)):
        return str(data)
    else:
        return str(data) if data is not None else ""

@router.post("/", response_model=str,status_code=status.HTTP_201_CREATED)
async def create_facial_recognition(facial_recognition: FacialRecognitionPost):
    new_facial_recognition = facial_recognition.model_dump()
    new_facial_recognition.pop("id", None)
    result = facial_recognition_collection().insert_one(new_facial_recognition)  # Call the function
    return str(result.inserted_id)

@router.get("/", response_model=List[FacialRecognition])
async def get_all_facial_recognitions():
    facial_recognitions = list(facial_recognition_collection().find())  # Call the function
    formatted_facial_recognitions = []
    for facial_recognition in facial_recognitions:
        for key, value in facial_recognition.items():
            facial_recognition[key] = convert_to_string_or_empty(value)
        facial_recognition["facialRecognizationId"] = str(facial_recognition.pop("_id"))  
        formatted_facial_recognitions.append(FacialRecognition(**facial_recognition))
    return formatted_facial_recognitions

@router.get("/{facial_recognition_id}", response_model=FacialRecognition)
async def get_facial_recognition_by_id(facial_recognition_id: str):
    facial_recognition = facial_recognition_collection().find_one(  # Call the function
        {"_id": ObjectId(facial_recognition_id)}
    )
    if facial_recognition:
        for key, value in facial_recognition.items():
            facial_recognition[key] = convert_to_string_or_empty(value)
        facial_recognition["facialRecognizationId"] = str(facial_recognition.pop("_id"))  
        return FacialRecognition(**facial_recognition)
    else:
        raise HTTPException(
            status_code=404, detail="Facial recognition record not found"
        )

@router.patch("/{facial_recognition_id}")
async def update_facial_recognition(
    facial_recognition_id: str, facial_recognition_patch: FacialRecognitionPost
):
    existing_facial_recognition = facial_recognition_collection().find_one(  # Call the function
        {"_id": ObjectId(facial_recognition_id)}
    )
    if not existing_facial_recognition:
        raise HTTPException(
            status_code=404, detail="Facial recognition record not found"
        )

    updated_fields = {
        key: convert_to_string_or_empty(value)
        for key, value in facial_recognition_patch.model_dump(exclude_unset=True).items()
    }

    if updated_fields:
        result = facial_recognition_collection().update_one(  # Call the function
            {"_id": ObjectId(facial_recognition_id)},
            {"$set": updated_fields}
        )
        if result.modified_count == 0:
            raise HTTPException(
                status_code=500, detail="Failed to update facial recognition record"
            )

    updated_facial_recognition = facial_recognition_collection().find_one(  # Call the function
        {"_id": ObjectId(facial_recognition_id)}
    )
    updated_facial_recognition["_id"] = str(updated_facial_recognition["_id"])  
    return updated_facial_recognition

@router.delete("/{facial_recognition_id}")
async def delete_facial_recognition(facial_recognition_id: str):
    result = facial_recognition_collection().delete_one(  # Call the function
        {"_id": ObjectId(facial_recognition_id)}
    )
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404, detail="Facial recognition record not found"
        )
    return {"message": "Facial recognition record deleted successfully"}

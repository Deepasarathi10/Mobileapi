from time import asctime
from typing import List
from fastapi import APIRouter, HTTPException
from bson import ObjectId
from .models import postDevice, postDevicePost
from .utils import get_postDevice_collection, convert_to_string_or_none

router = APIRouter()

@router.post("/", response_model=str)
async def create_postDevice(postDevice: postDevicePost):
    # Check if the collection is empty
    if get_postDevice_collection().count_documents({}) == 0:
        pass  # You need to add logic here for when collection is empty

    # Generate randomId
    # random_id = generate_random_id()

    # Prepare data including randomId
    new_postDevice_data = postDevice.dict()
    # new_postDevice_data['randomId'] = random_id
    new_postDevice_data['status'] = "activate"

    # Insert into MongoDB
    result = get_postDevice_collection().insert_one(new_postDevice_data)
    return str(result.inserted_id)
@router.get("/", response_model=List[postDevice])
async def get_all_postDevice():
    try:
        itempostDevice = list(get_postDevice_collection().find())
        formatted_postDevice = []
        for postDevices in itempostDevice:
            for key, value in postDevices.items():
                postDevices[key] = convert_to_string_or_none(value)
            postDevices["postDeviceId"] = str(postDevices["_id"])
            formatted_postDevice.append(postDevice(**postDevices))
        return formatted_postDevice
    except Exception as e:
        print(f"Error fetching postDevices: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/{postDevice_id}", response_model=postDevice)
async def get_postDevice_by_id(postDevice_id: str):
    try:
        postDevice_data = get_postDevice_collection().find_one({"_id": ObjectId(postDevice_id)})
        if postDevice_data:
            postDevice_data["postDeviceId"] = str(postDevice_data["_id"])
            return postDevice(**postDevice_data)
        else:
            raise HTTPException(status_code=404, detail="postDevice not found")
    except Exception as e:
        print(f"Error fetching postDevice by ID: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

# @router.patch("/{postDevice_id}")
# async def update_postDevice(postDevice_id: str, postDevice: postDevicePost):
#     updated_postDevice = postDevice.dict(exclude_unset=True)  # exclude_unset=True prevents sending None values to MongoDB
#     result = get_postDevice_collection().update_one({"_id": ObjectId(postDevice_id)}, {"$set": updated_postDevice})
#     if result.modified_count == 0:
#         raise HTTPException(status_code=404, detail="postDevice not found")
#     return {"message": "postDevice updated successfully"}

# @router.patch("/{postDevice_id}")
# async def patch_postDevice(postDevice_id: str, postDevice_patch: postDevicePost):
#     existing_postDevice = get_postDevice_collection().find_one({"_id": ObjectId(postDevice_id)})
#     if not existing_postDevice:
#         raise HTTPException(status_code=404, detail="postDevice not found")

#     updated_fields = {key: value for key, value in postDevice_patch.dict(exclude_unset=True).items() if value is not None}
#     if updated_fields:
#         result = get_postDevice_collection().update_one({"_id": ObjectId(postDevice_id)}, {"$set": updated_fields})
#         if result.modified_count == 0:
#             raise HTTPException(status_code=500, detail="Failed to update postDevice")

#     updated_postDevice = get_postDevice_collection().find_one({"_id": ObjectId(postDevice_id)})
#     updated_postDevice["_id"] = str(updated_postDevice["_id"])
#     return updated_postDevice


@router.patch("/{postDevice_id}")
async def update_postDevice(postDevice_id: str, postDevice: postDevicePost):
    updated_postDevice = postDevice.dict(exclude_unset=True)  # Exclude unset fields

    # Validate the 'status' field
    if "status" in updated_postDevice:
        if updated_postDevice["status"] not in ["activate", "deactivate"]:
            raise HTTPException(status_code=400, detail="Invalid status value. Must be 'activate' or 'deactivate'.")
    
    # Update the device in MongoDB
    result = get_postDevice_collection().update_one(
        {"_id": ObjectId(postDevice_id)},
        {"$set": updated_postDevice}
    )

    # Check if the device was updated
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="postDevice not found or no changes made")

    return {"message": "postDevice updated successfully"}


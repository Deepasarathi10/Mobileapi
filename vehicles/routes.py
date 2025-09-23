# from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import APIRouter, HTTPException, status
from pymongo import MongoClient
from .models import Vehicle, VehiclePost
from .utils import get_vehicle_collection
from bson import ObjectId
from typing import List

router = APIRouter()

@router.post("/", response_model=Vehicle)
async def create_vehicle(vehicle: VehiclePost):
    new_vehicle = vehicle.model_dump()
    new_vehicle["status"] = "active"
    result = await get_vehicle_collection().insert_one(new_vehicle)
    inserted_id = result.inserted_id
    doc = await get_vehicle_collection().find_one({"_id": inserted_id})
    if not doc:
        raise HTTPException(status_code=500, detail="Failed to create vehicle")
    formatted = {k: convert_to_string_or_emptys(v) for k, v in doc.items() if k != "_id"}
    formatted["id"] = str(doc["_id"])
    return Vehicle(**formatted)

def convert_to_string_or_emptys(data):
    if isinstance(data, list):
        return [str(value) if value is not None and value != "" else None for value in data]
    elif isinstance(data, (int, float)):
        return str(data)
    else:
        return str(data) if data is not None and data != "" else None

@router.get("/", response_model=List[Vehicle])
async def get_all_vehicles():
    vehicle_collection = get_vehicle_collection()
    vehicles: List[Vehicle] = []
    async for doc in vehicle_collection.find():
        formatted = {
            k: convert_to_string_or_emptys(v)
            for k, v in doc.items() if k != "_id"
        }
        formatted["id"] = str(doc["_id"])
        vehicles.append(Vehicle(**formatted))
    return vehicles

@router.get("_numbers/", response_model=List[str])
async def get_all_vehicle_numbers():
    vehicle_collection = get_vehicle_collection()
    vehicle_numbers = []
    async for doc in vehicle_collection.find({}, {"vehicleNo": 1}):
        if "vehicleNo" in doc and doc["vehicleNo"]:
            vehicle_numbers.append(str(doc["vehicleNo"]))
    return vehicle_numbers

@router.get("/{id}", response_model=Vehicle)
async def get_vehicle_by_id(id: str):
    coll = get_vehicle_collection()
    doc = await coll.find_one({"_id": ObjectId(id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    formatted = { k: convert_to_string_or_emptys(v) for k, v in doc.items() if k != "_id" }
    formatted["id"] = str(doc["_id"])
    return Vehicle(**formatted)

@router.put("/{id}", response_model=Vehicle)
async def update_vehicle(id: str, vehicle: VehiclePost):
    updated_vehicle = vehicle.model_dump(exclude_unset=True)
    result = await get_vehicle_collection().update_one(
        {"_id": ObjectId(id)}, {"$set": updated_vehicle}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    doc = await get_vehicle_collection().find_one({"_id": ObjectId(id)})
    formatted = {k: convert_to_string_or_emptys(v) for k, v in doc.items() if k != "_id"}
    formatted["id"] = str(doc["_id"])
    return Vehicle(**formatted)

@router.patch("/{id}", response_model=Vehicle)
async def update_vehicle(id: str, vehicle_patch: VehiclePost):
    existing_vehicle = await get_vehicle_collection().find_one({"_id": ObjectId(id)})
    if not existing_vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    updated_fields = {
        key: convert_to_string_or_emptys(value) for key, value in vehicle_patch.dict(exclude_unset=True).items()
    }

    if updated_fields:
        result = await get_vehicle_collection().update_one(
            {"_id": ObjectId(id)},
            {"$set": updated_fields}
        )
        if result.modified_count == 0:
            raise HTTPException(status_code=500, detail="Failed to update vehicle")

    updated_vehicle = await get_vehicle_collection().find_one({"_id": ObjectId(id)})
    formatted = {k: convert_to_string_or_emptys(v) for k, v in updated_vehicle.items() if k != "_id"}
    formatted["id"] = str(updated_vehicle["_id"])
    return Vehicle(**formatted)

@router.delete("/{id}")
async def delete_vehicle(id: str):
    result = await get_vehicle_collection().delete_one({"_id": ObjectId(id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return {"message": "Vehicle deleted successfully"}
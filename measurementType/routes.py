from typing import List
from fastapi import APIRouter, HTTPException
from bson import ObjectId
from .models import measure, measurePost
from .utils import get_measure_collection, convert_to_string_or_none

router = APIRouter()

def get_next_counter_value():
    counter_collection = get_measure_collection().database["counters"]
    counter = counter_collection.find_one_and_update(
        {"_id": "measureId"},
        {"$inc": {"sequence_value": 1}},
        upsert=True,
        return_document=True
    )   
    return counter["sequence_value"]

def reset_counter():
    counter_collection = get_measure_collection().database["counters"]
    counter_collection.update_one(
        {"_id": "measureId"},
        {"$set": {"sequence_value": 0}},
        upsert=True
    )

def generate_random_id():
    counter_value = get_next_counter_value()
    return f"IU{counter_value:03d}"

@router.post("/", response_model=str)
async def create_measure(measure: measurePost):
    # Check if the collection is empty
    if get_measure_collection().count_documents({}) == 0:
        reset_counter()

    # Generate randomId
    random_id = generate_random_id()

    # Prepare data including randomId
    new_measure_data = measure.dict()
    new_measure_data['randomId'] = random_id
    new_measure_data['status'] = "active"

    # Insert into MongoDB
    result = get_measure_collection().insert_one(new_measure_data)
    return str(result.inserted_id)

@router.get("/", response_model=List[measure])
async def get_all_measure():
    try:
        itemmeasure = list(get_measure_collection().find())
        formatted_measure = []
        for measures in itemmeasure:
            for key, value in measures.items():
                measures[key] = convert_to_string_or_none(value)
            measures["measureId"] = str(measures["_id"])
            formatted_measure.append(measure(**measures))
        return formatted_measure
    except Exception as e:
        print(f"Error fetching measures: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/{measure_id}", response_model=measure)
async def get_measure_by_id(measure_id: str):
    try:
        measure_data = get_measure_collection().find_one({"_id": ObjectId(measure_id)})
        if measure_data:
            measure_data["measureId"] = str(measure_data["_id"])
            return measure(**measure_data)
        else:
            raise HTTPException(status_code=404, detail="measure not found")
    except Exception as e:
        print(f"Error fetching measure by ID: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.patch("/{measure_id}")
async def update_measure(measure_id: str, measure: measurePost):
    updated_measure = measure.dict(exclude_unset=True)  # exclude_unset=True prevents sending None values to MongoDB
    result = get_measure_collection().update_one({"_id": ObjectId(measure_id)}, {"$set": updated_measure})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="measure not found")
    return {"message": "measure updated successfully"}

@router.patch("/{measure_id}")
async def patch_measure(measure_id: str, measure_patch: measurePost):
    existing_measure = get_measure_collection().find_one({"_id": ObjectId(measure_id)})
    if not existing_measure:
        raise HTTPException(status_code=404, detail="measure not found")

    updated_fields = {key: value for key, value in measure_patch.dict(exclude_unset=True).items() if value is not None}
    if updated_fields:
        result = get_measure_collection().update_one({"_id": ObjectId(measure_id)}, {"$set": updated_fields})
        if result.modified_count == 0:
            raise HTTPException(status_code=500, detail="Failed to update measure")

    updated_measure = get_measure_collection().find_one({"_id": ObjectId(measure_id)})
    updated_measure["_id"] = str(updated_measure["_id"])
    return updated_measure



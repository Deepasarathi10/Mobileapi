from typing import List
from fastapi import APIRouter, HTTPException
from bson import ObjectId
from .models import inventory, inventoryPost
from .utils import get_inventory_collection, convert_to_string_or_none

router = APIRouter()
    
def get_next_counter_value():
    counter_collection = get_inventory_collection().database["counters"]
    counter = counter_collection.find_one_and_update(
        {"_id": "inventoryId"},
        {"$inc": {"sequence_value": 1}},
        upsert=True,
        return_document=True
    )   
    return counter["sequence_value"]

def reset_counter():
    counter_collection = get_inventory_collection().database["counters"]
    counter_collection.update_one(
        {"_id": "inventoryId"},
        {"$set": {"sequence_value": 0}},
        upsert=True
    )

def generate_random_id():
    counter_value = get_next_counter_value()
    return f"IU{counter_value:03d}"

@router.post("/", response_model=str)
async def create_inventory(inventory: inventoryPost):
    # Check if the collection is empty
    if get_inventory_collection().count_documents({}) == 0:
        reset_counter()

    # Generate randomId
    random_id = generate_random_id()

    # Prepare data including randomId
    new_inventory_data = inventory.dict()
    new_inventory_data['randomId'] = random_id
    new_inventory_data['status'] = "active"

    # Insert into MongoDB
    result = get_inventory_collection().insert_one(new_inventory_data)
    return str(result.inserted_id)

@router.get("/", response_model=List[inventory])
async def get_all_inventory():
    try:
        iteminventory = list(get_inventory_collection().find())
        formatted_inventory = []
        for inventorys in iteminventory:
            for key, value in inventorys.items():
                inventorys[key] = convert_to_string_or_none(value)
            inventorys["inventoryId"] = str(inventorys["_id"])
            formatted_inventory.append(inventory(**inventorys))
        return formatted_inventory
    except Exception as e:
        print(f"Error fetching inventorys: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/{inventory_id}", response_model=inventory)
async def get_inventory_by_id(inventory_id: str):
    try:
        inventory_data = get_inventory_collection().find_one({"_id": ObjectId(inventory_id)})
        if inventory_data:
            inventory_data["inventoryId"] = str(inventory_data["_id"])
            return inventory(**inventory_data)
        else:
            raise HTTPException(status_code=404, detail="inventory not found")
    except Exception as e:
        print(f"Error fetching inventory by ID: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.patch("/{inventory_id}")
async def update_inventory(inventory_id: str, inventory: inventoryPost):
    updated_inventory = inventory.dict(exclude_unset=True)  # exclude_unset=True prevents sending None values to MongoDB
    result = get_inventory_collection().update_one({"_id": ObjectId(inventory_id)}, {"$set": updated_inventory})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="inventory not found")
    return {"message": "inventory updated successfully"}

@router.patch("/{inventory_id}")
async def patch_inventory(inventory_id: str, inventory_patch: inventoryPost):
    existing_inventory = get_inventory_collection().find_one({"_id": ObjectId(inventory_id)})
    if not existing_inventory:
        raise HTTPException(status_code=404, detail="inventory not found")

    updated_fields = {key: value for key, value in inventory_patch.dict(exclude_unset=True).items() if value is not None}
    if updated_fields:
        result = get_inventory_collection().update_one({"_id": ObjectId(inventory_id)}, {"$set": updated_fields})
        if result.modified_count == 0:
            raise HTTPException(status_code=500, detail="Failed to update inventory")

    updated_inventory = get_inventory_collection().find_one({"_id": ObjectId(inventory_id)})
    updated_inventory["_id"] = str(updated_inventory["_id"])
    return updated_inventory



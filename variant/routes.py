from typing import List
from fastapi import APIRouter, HTTPException
from bson import ObjectId
from .models import variant, variantPost
from .utils import get_variant_collection, convert_to_string_or_none

router = APIRouter()

def get_next_counter_value() -> int:
    counter_collection = get_variant_collection().database["counters"]
    counter = counter_collection.find_one_and_update(
        {"_id": "variantId"},
        {"$inc": {"sequence_value": 1}},
        upsert=True,
        return_document=True
    )
    return counter["sequence_value"]

def reset_counter() -> None:
    counter_collection = get_variant_collection().database["counters"]
    counter_collection.update_one(
        {"_id": "variantId"},
        {"$set": {"sequence_value": 0}},
        upsert=True
    )

def generate_random_id() -> str:
    counter_value = get_next_counter_value()
    return f"Var{counter_value:03d}"

@router.post("/", response_model=str)
async def create_variant(variant: variantPost):
    # Reset counter if collection is empty
    if get_variant_collection().count_documents({}) == 0:
        reset_counter()

    # Generate randomId
    random_id = generate_random_id()

    # Prepare data including randomId
    new_variant_data = variant.dict(exclude_unset=True)
    new_variant_data['randomId'] = random_id

    # Ensure variantItems is a list of strings, filtering out None values
    if new_variant_data.get("variantItems"):
        new_variant_data["variantItems"] = [item for item in new_variant_data["variantItems"] if item is not None]

    # Insert into MongoDB
    result = get_variant_collection().insert_one(new_variant_data)
    return str(result.inserted_id)

@router.get("/", response_model=List[variant])
async def get_all_variant():
    try:
        item_variants = list(get_variant_collection().find())
        formatted_variants = []
        for variant_data in item_variants:
            # Convert _id to string
            variant_data["_id"] = str(variant_data["_id"])
            # Ensure variantItems is a list, default to empty list if missing
            variant_data["variantItems"] = variant_data.get("variantItems", [])
            # Filter out None values from variantItems and ensure all are strings
            variant_data["variantItems"] = [
                str(item) for item in variant_data["variantItems"] if item is not None
            ]
            # Set variantId to _id
            variant_data["variantId"] = variant_data["_id"]
            # Convert values to string or None where necessary
            for key, value in variant_data.items():
                if key != "variantItems":  # Skip variantItems since we handled it
                    variant_data[key] = convert_to_string_or_none(value)
            formatted_variants.append(variant(**variant_data))
        return formatted_variants
    except Exception as e:
        print(f"Error fetching variants: {e}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@router.patch("/{variant_id}")
async def patch_variant(variant_id: str, variant_patch: variantPost):
    if not ObjectId.is_valid(variant_id):
        raise HTTPException(status_code=400, detail="Invalid variantId format")
    
    # Find existing variant
    existing_variant = get_variant_collection().find_one({"_id": ObjectId(variant_id)})
    if not existing_variant:
        raise HTTPException(status_code=404, detail="Variant not found")

    # Prepare updated fields, excluding unset or None values
    updated_fields = {key: value for key, value in variant_patch.dict(exclude_unset=True).items() if value is not None}
    if not updated_fields:
        raise HTTPException(status_code=422, detail="No valid fields provided to update")

    # If variantItems is being updated, filter out None values and ensure strings
    if "variantItems" in updated_fields:
        updated_fields["variantItems"] = [str(item) for item in updated_fields["variantItems"] if item is not None]

    # Update in MongoDB
    result = get_variant_collection().update_one(
        {"_id": ObjectId(variant_id)},
        {"$set": updated_fields}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=500, detail="Failed to update variant")

    # Return updated variant
    updated_variant = get_variant_collection().find_one({"_id": ObjectId(variant_id)})
    updated_variant["_id"] = str(updated_variant["_id"])
    updated_variant["variantId"] = updated_variant["_id"]
    updated_variant["variantItems"] = [
        str(item) for item in updated_variant.get("variantItems", []) if item is not None
    ]
    return variant(**updated_variant)

@router.delete("/{variant_id}")
async def delete_variant(variant_id: str):
    if not ObjectId.is_valid(variant_id):
        raise HTTPException(status_code=400, detail="Invalid variantId format")
    
    result = get_variant_collection().delete_one({"_id": ObjectId(variant_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Variant not found")
    return {"message": "Variant deleted successfully"}
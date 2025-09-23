from typing import List
from fastapi import APIRouter, HTTPException, status
from bson import ObjectId
from rawMaterials.models import RawMaterials, RawMaterialsCreate
from rawMaterials.utils import get_raw_Matrials_collection

router = APIRouter()

# Create a new raw material
@router.post("/", response_model=str, status_code=status.HTTP_201_CREATED)
async def create_raw_material(raw_material: RawMaterialsCreate):
    new_raw_material = raw_material.dict()
    result = await get_raw_Matrials_collection().insert_one(new_raw_material)
    return str(result.inserted_id)


# Get all raw materials
@router.get("/", response_model=List[RawMaterials])
async def get_all_raw_materials():
    cursor = get_raw_Matrials_collection().find()
    raw_materials = await cursor.to_list(length=None)

    for material in raw_materials:
        material["rawMaterialid"] = str(material.pop("_id"))
    return raw_materials


# Get a single raw material by ID
@router.get("/{raw_material_id}", response_model=RawMaterials)
async def get_raw_material_by_id(raw_material_id: str):
    try:
        raw_material = await get_raw_Matrials_collection().find_one({"_id": ObjectId(raw_material_id)})
        if raw_material:
            raw_material["rawMaterialid"] = str(raw_material.pop("_id"))
            return raw_material
        else:
            raise HTTPException(status_code=404, detail="Raw Material not found")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid raw material ID")


# Update an entire raw material
@router.put("/{raw_material_id}")
async def update_raw_material(raw_material_id: str, raw_material_update: RawMaterialsCreate):
    updated_data = raw_material_update.dict(exclude_unset=True)
    result = await get_raw_Matrials_collection().update_one(
        {"_id": ObjectId(raw_material_id)}, {"$set": updated_data}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Raw Material not found")
    return {"message": "Raw Material updated successfully"}


# Partially update a raw material
@router.patch("/{raw_material_id}")
async def patch_raw_material(raw_material_id: str, raw_material_patch: RawMaterialsCreate):
    existing_raw_material = await get_raw_Matrials_collection().find_one({"_id": ObjectId(raw_material_id)})
    if not existing_raw_material:
        raise HTTPException(status_code=404, detail="Raw Material not found")

    updated_fields = {
        key: value
        for key, value in raw_material_patch.dict(exclude_unset=True).items()
        if value is not None
    }

    if updated_fields:
        result = await get_raw_Matrials_collection().update_one(
            {"_id": ObjectId(raw_material_id)}, {"$set": updated_fields}
        )
        if result.modified_count == 0:
            raise HTTPException(status_code=500, detail="Failed to update raw material")

    updated_raw_material = await get_raw_Matrials_collection().find_one({"_id": ObjectId(raw_material_id)})
    updated_raw_material["rawMaterialid"] = str(updated_raw_material["_id"])
    return updated_raw_material


# Delete a raw material
@router.delete("/{raw_material_id}")
async def delete_raw_material(raw_material_id: str):
    result = await get_raw_Matrials_collection().delete_one({"_id": ObjectId(raw_material_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Raw Material not found")
    return {"message": "Raw Material deleted successfully"}

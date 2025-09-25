from typing import List
from fastapi import APIRouter, HTTPException
from bson import ObjectId
from .models import SfgItems, SfgItemsPost
from .utils import get_sfgItems_collection

router = APIRouter()

# ---------- CREATE ----------
@router.post("/", response_model=str)
async def create_sfgitems(sfgitems: SfgItemsPost):
    new_sfgitems_data = sfgitems.dict()
    result = await get_sfgItems_collection().insert_one(new_sfgitems_data)
    return str(result.inserted_id)


# ---------- READ ALL ----------
@router.get("/", response_model=List[SfgItems])
async def get_all_sfgitems():
    cursor = get_sfgItems_collection().find()
    sfgitems_list = []
    async for sfgitem in cursor:
        sfgitem["sfgItemsId"] = str(sfgitem["_id"])
        sfgitems_list.append(SfgItems(**sfgitem))
    return sfgitems_list


# ---------- READ BY ID ----------
@router.get("/{sfgItems_id}", response_model=SfgItems)
async def get_sfgitems_by_id(sfgItems_id: str):
    sfgitem = await get_sfgItems_collection().find_one({"_id": ObjectId(sfgItems_id)})
    if not sfgitem:
        raise HTTPException(status_code=404, detail="SFG Item not found")

    sfgitem["sfgItemsId"] = str(sfgitem["_id"])
    return SfgItems(**sfgitem)


# ---------- UPDATE (PUT) ----------
@router.put("/{sfgItems_id}")
async def update_sfgitems(sfgItems_id: str, sfgitems: SfgItemsPost):
    updated_data = sfgitems.dict(exclude_unset=True)
    result = await get_sfgItems_collection().update_one(
        {"_id": ObjectId(sfgItems_id)},
        {"$set": updated_data}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="SFG Item not found or no changes made")
    return {"message": "SFG Item updated successfully"}


# ---------- PATCH ----------
@router.patch("/{sfgItems_id}")
async def patch_sfgitems(sfgItems_id: str, sfgitems_patch: SfgItemsPost):
    existing = await get_sfgItems_collection().find_one({"_id": ObjectId(sfgItems_id)})
    if not existing:
        raise HTTPException(status_code=404, detail="SFG Item not found")

    updated_fields = {
        key: value for key, value in sfgitems_patch.dict(exclude_unset=True).items()
        if value is not None
    }

    if updated_fields:
        result = await get_sfgItems_collection().update_one(
            {"_id": ObjectId(sfgItems_id)},
            {"$set": updated_fields}
        )
        if result.modified_count == 0:
            raise HTTPException(status_code=500, detail="Failed to update SFG Item")

    updated = await get_sfgItems_collection().find_one({"_id": ObjectId(sfgItems_id)})
    updated["sfgItemsId"] = str(updated["_id"])
    return SfgItems(**updated)


# ---------- DELETE ----------
@router.delete("/{sfgItems_id}")
async def delete_sfgitems(sfgItems_id: str):
    result = await get_sfgItems_collection().delete_one({"_id": ObjectId(sfgItems_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="SFG Item not found")
    return {"message": "SFG Item deleted successfully"}

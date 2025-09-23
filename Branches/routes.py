from typing import List, Optional
from fastapi import APIRouter, HTTPException, status
from bson import ObjectId
from .models import branch, branchPost
from .utils import get_branch_collection

router = APIRouter()

# indexing

async def get_next_counter_value():
    counter_collection = get_branch_collection().database["counters"]
    counter = await counter_collection.find_one_and_update(
        {"_id": "branchId"},
        {"$inc": {"sequence_value": 1}},
        upsert=True,
        return_document=True
    )
    return counter["sequence_value"]


async def reset_counter():
    counter_collection = get_branch_collection().database["counters"]
    await counter_collection.update_one(
        {"_id": "branchId"},
        {"$set": {"sequence_value": 0}},
        upsert=True
    )


async def generate_random_id():
    counter_value = await get_next_counter_value()
    return f"BR{counter_value:03d}"


@router.post("/", response_model=str, status_code=status.HTTP_201_CREATED)
async def create_branch(branch: branchPost):
    coll = get_branch_collection()

    # Check if the collection is empty
    if await coll.count_documents({}) == 0:
        await reset_counter()

    # Generate randomId
    random_id = await generate_random_id()

    # Prepare data including randomId
    new_branch_data = branch.dict()
    new_branch_data["randomId"] = random_id

    # Insert into MongoDB
    result = await coll.insert_one(new_branch_data)
    return str(result.inserted_id)


@router.get("/", response_model=List[branch])
async def get_all_branch(branch_name: Optional[str] = None, alias_name: Optional[str] = None):
    coll = get_branch_collection()
    query = {}
    if branch_name:
        query["branchName"] = branch_name
    if alias_name:
        query["aliasName"] = alias_name

    cursor = coll.find(query)
    branches = await cursor.to_list(length=None)

    formatted_branches = []
    for branch_dict in branches:
        branch_dict["branchId"] = str(branch_dict.pop("_id"))
        formatted_branches.append(branch(**branch_dict))
    return formatted_branches


@router.get("/{branch_id}", response_model=branch)
async def get_branch_by_id(branch_id: str):
    coll = get_branch_collection()
    doc = await coll.find_one({"_id": ObjectId(branch_id)})
    if doc:
        doc["branchId"] = str(doc.pop("_id"))
        return branch(**doc)
    else:
        raise HTTPException(status_code=404, detail="branch not found")


@router.patch("/{branch_id}")
async def patch_branch(branch_id: str, branch_patch: branchPost):
    coll = get_branch_collection()
    existing_branch = await coll.find_one({"_id": ObjectId(branch_id)})
    if not existing_branch:
        raise HTTPException(status_code=404, detail="branch not found")

    updated_fields = {
        key: value for key, value in branch_patch.dict(exclude_unset=True).items() if value is not None
    }
    if updated_fields:
        result = await coll.update_one({"_id": ObjectId(branch_id)}, {"$set": updated_fields})
        if result.modified_count == 0:
            raise HTTPException(status_code=500, detail="Failed to update branch")

    updated_branch = await coll.find_one({"_id": ObjectId(branch_id)})
    updated_branch["branchId"] = str(updated_branch.pop("_id"))
    return updated_branch


@router.delete("/{branch_id}")
async def delete_branch(branch_id: str):
    coll = get_branch_collection()
    result = await coll.delete_one({"_id": ObjectId(branch_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="branch not found")

    return {"message": "branch deleted successfully"}

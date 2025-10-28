from typing import List, Optional
from bson import ObjectId
from fastapi import APIRouter
from .utils import get_birthDayCake_collection
from .models import BirthDayCake,BirthDayCakePost
from fastapi import HTTPException,Body,Query

router = APIRouter()
 
 
def document_to_cake(doc) -> BirthDayCake:
    if not doc:
        return None
    # convert `_id` to string
    cake = BirthDayCake(
        id=str(doc.get("_id")),
        cakeId=doc.get("cakeId"),
        varianceName=doc.get("varianceName"),
        branchName=doc.get("branchName"),
        selfLife=doc.get("selfLife"),
        productionDate=doc.get("productionDate"),
        expiryDate=doc.get("expiryDate"),
        status=doc.get("status"),
        itemCode=doc.get("itemCode"),
        manufacture=doc.get("manufacture")
    )
    return cake

@router.post("/cakes/", response_model=BirthDayCakePost)
async def create_cake(cake_post: BirthDayCakePost = Body(...)):
    coll = get_birthDayCake_collection()
    # convert Pydantic to dict, excluding None fields
    cake_data = cake_post.dict(exclude_none=True)
    result = await coll.insert_one(cake_data)
    new_doc = await coll.find_one({"_id": result.inserted_id})
    # inline conversion
    return document_to_cake(new_doc)

@router.get("/cakes/{id}", response_model=BirthDayCake)
async def get_cake(id: str):
    coll = get_birthDayCake_collection()
    try:
        oid = ObjectId(id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID format")
    doc = await coll.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Cake not found")
    return document_to_cake(doc)


@router.get("/cakes/by-branch/", response_model=List[BirthDayCake])
async def get_cakes_by_branch(
    branch_name: str = Query(..., alias="branchName"),
    status: Optional[str] = Query(None, alias="status")  # 👈 new optional query param
) -> List[BirthDayCake]:
    coll = get_birthDayCake_collection()
    results: List[BirthDayCake] = []

    # Build filter dynamically
    filter_query = {"branchName": branch_name}
    if status is not None:
        filter_query["status"] = status

    cursor = coll.find(filter_query)
    async for doc in cursor:
        cake = document_to_cake(doc)
        if cake:
            results.append(cake)

    return results


@router.get("/cakes/", response_model=list[BirthDayCake])
async def get_all_cakes():
    coll = get_birthDayCake_collection()
    results = []
    cursor = coll.find({})
    async for doc in cursor:
        # inline conversion each
        cake = BirthDayCake(
            id=str(doc.get("_id")),
            cakeId=doc.get("cakeId"),
            varianceName=doc.get("varianceName"),
            branchName=doc.get("branchName"),
            selfLife=doc.get("selfLife"),
            productionDate=doc.get("productionDate"),
            expiryDate=doc.get("expiryDate"),
            status=doc.get("status"),
            itemCode=doc.get("itemCode"),
            manufacture=doc.get("manufacture")
        )
        results.append(cake)
    return results

@router.patch("/cakes/{cake_id}", response_model=BirthDayCakePost)
async def update_cake(cake_id: str, cake_post: BirthDayCakePost = Body(...)):
    coll = get_birthDayCake_collection()
    try:
        oid = ObjectId(cake_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID format")
    update_data = cake_post.dict(exclude_unset=True, exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="Nothing to update")
    result = await coll.update_one({"_id": oid}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Cake not found")
    updated_doc = await coll.find_one({"_id": oid})
    return document_to_cake(updated_doc)

from fastapi import Path

@router.patch("/cakes/{cake_id}/status", response_model=BirthDayCake)
async def update_cake_status(
    cake_id: str = Path(..., description="The ID of the cake to update"),
    status: str = Body(..., embed=True, description="New status value")
):
    coll = get_birthDayCake_collection()
    try:
        oid = ObjectId(cake_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    result = await coll.update_one({"_id": oid}, {"$set": {"status": status}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Cake not found")

    updated_doc = await coll.find_one({"_id": oid})
    return document_to_cake(updated_doc)

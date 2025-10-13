from fastapi import APIRouter, HTTPException
from typing import Dict, List
from bson import ObjectId
from reasons.models import ReasonPostWithModule, ReasonGroupResponse
from reasons.utils import get_collection

router = APIRouter(tags=["Reasons"])


# -----------------------------
# GET all modules with reasons list
# -----------------------------
@router.get("/", response_model=List[ReasonGroupResponse])
async def get_all_reasons():
    """
    Returns all modules with their reason lists.
    Example:
    [
      {"id": "6712a8...", "module": "Wastage Entry", "reasons": ["Damaged", "Expired"]},
      {"id": "6712a9...", "module": "Warehouse Return", "reasons": ["Broken", "Wrong Item"]}
    ]
    """
    collection = get_collection("reasons")

    cursor = collection.find({})
    results = []
    async for doc in cursor:
        results.append(
            ReasonGroupResponse(
                id=str(doc["_id"]),
                module=doc["module"],
                reasons=doc.get("reasons", [])
            )
        )
    return results


# -----------------------------
# POST add reason to module
# -----------------------------
@router.post("/", response_model=str)
async def add_reason(reason: ReasonPostWithModule):
    """
    Add a new reason to an existing module,
    or create the module if not exists.
    """
    collection = get_collection("reasons")

    # find if module exists
    existing = await collection.find_one({"module": reason.module})

    if existing:
        # update the reasons list if not already present
        if reason.reason not in existing.get("reasons", []):
            await collection.update_one(
                {"module": reason.module},
                {"$push": {"reasons": reason.reason}}
            )
        else:
            raise HTTPException(status_code=400, detail="Reason already exists in this module")
    else:
        # create new module document
        result = await collection.insert_one({
            "module": reason.module,
            "reasons": [reason.reason]
        })
        return str(result.inserted_id)

    return "Reason added successfully"

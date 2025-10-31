from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from bson import ObjectId
from bson.errors import InvalidId
from datetime import datetime,timedelta

from fastapi.encoders import jsonable_encoder
from .models import ItemType, ItemTypePost
from .utils import get_itemtransfer_collection
from Branchwiseitem.routes import branchwise_items_collection
from Branches.utils import get_branch_collection
router = APIRouter()

# ------------------- CREATE -------------------
@router.post("/", response_model=str, status_code=status.HTTP_201_CREATED)
async def create_itemtransfer(itemtransfer: ItemTypePost):
    new_itemtransfer_data = itemtransfer.model_dump()
    result = await get_itemtransfer_collection().insert_one(new_itemtransfer_data)
    return str(result.inserted_id)


#---------------------GETALL---------------------

@router.get("/", response_model=List[ItemType])
async def get_all_itemtransfer(
    from_branch: Optional[str] = Query(None),
    to_branch: Optional[str] = Query(None),
    from_login_id: Optional[str] = Query(None),  
    to_login_id: Optional[str] = Query(None),
    status: Optional[List[str]] = Query(None),
):
    base_query = {}

    # Branch filters
    if from_branch:
        base_query["fromBranch"] = from_branch
    if to_branch:
        base_query["toBranch"] = to_branch
    if from_login_id:  
        base_query["fromLoginId"] = from_login_id
    if to_login_id:    
        base_query["toLoginId"] = to_login_id   

    # Status filter
    if status:
        base_query["status"] = status[0] if len(status) == 1 else {"$in": status}

    # ✅ Date filter for current date and previous 2 days
    end_dt = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
    start_dt = (datetime.now() - timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0)
    date_filter = {"$gte": start_dt, "$lte": end_dt}

    # Priority date fields
    datetime_fields = ["requestDateTime", "sentDateTime", "receiveDateTime", "rejectDateTime"]

    for field in datetime_fields:
        query = base_query.copy()
        query[field] = date_filter  # Automatically restrict to last 3 days

        results = await get_itemtransfer_collection().find(query).to_list(length=None)
        if results:
            for item in results:
                item["itemtransferId"] = str(item["_id"])
                item["fromLoginId"] = item.get("fromLoginId", None)
                item["toLoginId"] = item.get("toLoginId", None)
            return [ItemType(**item) for item in results]

    # No matching data
    return []





















# ------------------- GET BY ID -------------------
@router.get("/{itemtransfer_id}", response_model=ItemType)
async def get_itemtransfer_by_id(itemtransfer_id: str):
    try:
        object_id = ObjectId(itemtransfer_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid itemtransfer_id")

    itemtransfer = await get_itemtransfer_collection().find_one({"_id": object_id})
    if itemtransfer:
        itemtransfer["itemtransferId"] = str(itemtransfer["_id"])
        itemtransfer["fromLoginId"] = itemtransfer.get("fromLoginId", None)
        itemtransfer["toLoginId"] = itemtransfer.get("toLoginId", None)
        return ItemType(**itemtransfer)
    else:
        raise HTTPException(status_code=404, detail="Itemtransfer not found")


# ------------------- PATCH -------------------

@router.patch("/{itemtransfer_id}")
async def patch_itemtransfer(itemtransfer_id: str, itemtransfer_patch: ItemTypePost):
    try:
        object_id = ObjectId(itemtransfer_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid itemtransfer_id")

   

    # Get existing item transfer
    existing_itemtransfer = await get_itemtransfer_collection().find_one({"_id": object_id})
    if not existing_itemtransfer:
        raise HTTPException(status_code=404, detail="Itemtransfer not found")

    

    # Extract only updated fields
    updated_fields = {
        k: v for k, v in itemtransfer_patch.model_dump(exclude_unset=True).items() if v is not None
    }

    

    # Apply updates to the itemtransfer document
    if updated_fields:
        result = await get_itemtransfer_collection().update_one({"_id": object_id}, {"$set": updated_fields})
     

    # --- Stock Update on Sent Status ---
    if updated_fields.get("status") == "Sent":
     

        send_qtys = updated_fields.get("sendQty", existing_itemtransfer.get("sendQty", []))
        to_branch = updated_fields.get("toBranch", existing_itemtransfer.get("toBranch"))
        item_Names = updated_fields.get("itemName", existing_itemtransfer.get("itemName", []))
        from_login_id = updated_fields.get("fromLoginId", existing_itemtransfer.get("fromLoginId"))
        to_login_id = updated_fields.get("toLoginId", existing_itemtransfer.get("toLoginId"))
      

        # --- Get branch alias ---
        branch_doc = await get_branch_collection().find_one({"branchName": to_branch})
        

        if not branch_doc or "aliasName" not in branch_doc:
            raise HTTPException(status_code=400, detail=f"Branch alias not found for {to_branch}")

        branch_alias = branch_doc["aliasName"]
        

        # --- Update stock for each item ---
        for code, qty in zip(item_Names, send_qtys):
          
            update_result = await branchwise_items_collection.update_one(
                {"varianceName": code},
                {
                    "$inc": {
                        f"physicalStock_{branch_alias}": -qty
                    }
                }
            )
         
    # Fetch and return the updated document
    updated_itemtransfer = await get_itemtransfer_collection().find_one({"_id": object_id})
    updated_itemtransfer["_id"] = str(updated_itemtransfer["_id"])
    updated_itemtransfer["itemtransferId"] = str(updated_itemtransfer["_id"])
    updated_itemtransfer["fromLoginId"] = updated_itemtransfer.get("fromLoginId", None)
    updated_itemtransfer["toLoginId"] = updated_itemtransfer.get("toLoginId", None)
   
    return jsonable_encoder(updated_itemtransfer)


# ------------------- DELETE -------------------
@router.delete("/{itemtransfer_id}")
async def delete_itemtransfer(itemtransfer_id: str):
    try:
        object_id = ObjectId(itemtransfer_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid itemtransfer_id")

    result = await get_itemtransfer_collection().delete_one({"_id": object_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Itemtransfer not found")
    return {"message": "Itemtransfer deleted successfully"}

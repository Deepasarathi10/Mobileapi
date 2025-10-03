from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from bson import ObjectId
from datetime import datetime, timedelta
from .models import DayEndValidation, DayEndValidationPost
from .utils import get_dayEndValidation_collection
from dispatch.utils import get_dispatch_collection
from SalesOrder.utils import get_salesOrder_collection
from HeldOrders.utils import get_holdOrder_collection
from itemTransfer.utils import get_itemtransfer_collection
from shift.utils import get_shift_collection
from storeDispatch.utils import get_dispatch_collection as get_storeDispatch_collection

router = APIRouter()


@router.get("/Validation", response_model=DayEndValidation)
async def get_day_end(branchName: str = Query(..., description="Branch name to validate")):
    """
    Compute dayend validation for today's data in a given branch,
    save it to DB, return stored record
    """
    result = DayEndValidation()
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)

    # ----- Sales Orders -----
    sales_col = get_salesOrder_collection()
    so_pending = await sales_col.count_documents({
        "branchName": branchName,
        "status": {"$in": ["toApprove Orders", "Waiting for Approval"]},
        "createdAt": {"$gte": today, "$lt": tomorrow},
    })

    hold_col = get_holdOrder_collection()
    hold_pending = await hold_col.count_documents({
        "branchName": branchName,
        "approvalStatus": "Sending to Approval",
        "createdAt": {"$gte": today, "$lt": tomorrow},
    })

    if so_pending > 0 or hold_pending > 0:
        result.soApprovalsStatus = "failed"
        result.soPendings = so_pending + hold_pending
    else:
        result.soApprovalsStatus = "success"
        result.soPendings = 0

    # ----- Dispatch -----
    dispatch_col = get_dispatch_collection()
    dispatch_pending = await dispatch_col.count_documents({
        "branchName": branchName,
        "status": "dispatched",
        "createdAt": {"$gte": today, "$lt": tomorrow},
    })

    if dispatch_pending > 0:
        result.dispatchStatus = "failed"
        result.dispatchPendings = dispatch_pending
    else:
        result.dispatchStatus = "success"
        result.dispatchPendings = 0

    # ----- Item Transfer -----
    item_col = get_itemtransfer_collection()
    item_pending = await item_col.count_documents({
        "branchName": branchName,
        "status": "Pending",
        "createdAt": {"$gte": today, "$lt": tomorrow},
    })

    if item_pending > 0:
        result.itemTransferStatus = "failed"
        result.itemTransferPendings = item_pending
    else:
        result.itemTransferStatus = "success"
        result.itemTransferPendings = 0

    # ----- Sales Orders Delivery -----
    soDelivery_col = get_salesOrder_collection()
    soDelivery_pending = await soDelivery_col.count_documents({
        "branchName": branchName,
        "status": "Confirm Order",
        "createdAt": {"$gte": today, "$lt": tomorrow},
    })

    if soDelivery_pending > 0:
        result.soDeliveryStatus = "failed"
        result.soDeliveryPendings = soDelivery_pending
    else:
        result.soDeliveryStatus = "success"
        result.soDeliveryPendings = 0

    # ----- Store Dispatch -----
    store_col = get_storeDispatch_collection()
    store_pending = await store_col.count_documents({
        "branchName": branchName,
        "status": "dispatched",
        "createdAt": {"$gte": today, "$lt": tomorrow},
    })

    if store_pending > 0:
        result.storeDispatchStatus = "failed"
        result.storeDispatchPendings = store_pending
    else:
        result.storeDispatchStatus = "success"
        result.storeDispatchPendings = 0

    # ---------- SAVE TO DB ----------
    dayend_col = get_dayEndValidation_collection()
    insert_dict = result.dict(exclude_none=True)
    insert_dict["branchName"] = branchName
    insert_dict["date"] = today

    inserted = await dayend_col.insert_one(insert_dict)
    insert_dict["dayEndId"] = str(inserted.inserted_id)

    return DayEndValidation(**insert_dict)


@router.get("/dayendValidation", response_model=List[DayEndValidation])
async def get_all_day_end():
    """
    Fetch all dayend validations from DB
    """
    dayend_col = get_dayEndValidation_collection()
    docs_cursor = dayend_col.find({})
    result = []

    async for doc in docs_cursor:
        doc["dayEndId"] = str(doc["_id"])
        del doc["_id"]
        result.append(DayEndValidation(**doc))

    return result


@router.get("/dayendValidation/{dayend_id}", response_model=DayEndValidation)
async def get_day_end_by_id(dayend_id: str):
    """
    Fetch single dayend validation by ID
    """
    dayend_col = get_dayEndValidation_collection()

    doc = await dayend_col.find_one({"_id": ObjectId(dayend_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="DayEnd not found")

    doc["dayEndId"] = str(doc["_id"])
    del doc["_id"]

    return DayEndValidation(**doc)


@router.get("/status", response_model=DayEndValidation)
async def get_shift_status(empId: str = Query(...), branchName: str = Query(...)):
    """
    Returns shiftStatus = "open" if any shift exists in DB for given empId & branchName with status "open",
    else "close".
    """
    shift_collection = get_shift_collection()
    query = {"empId": empId, "branchName": branchName, "status": "open"}
    shift = await shift_collection.find_one(query)
    status = "open" if shift else "close"
    return DayEndValidation(empId=empId, branchName=branchName, shiftStatus=status)


@router.patch("/dayendValidation", response_model=DayEndValidation)
async def update_day_end(payload: DayEndValidationPost, branchName: str = Query(...)):
    """
    Update today's dayend validation record for a given branch.
    If no record exists for today, create one.
    """
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    # ----- Sales Orders -----
    sales_col = get_salesOrder_collection()
    so_pending = await sales_col.count_documents({
        "branchName": branchName,
        "status": {"$in": ["toApprove Orders", "Waiting for Approval"]},
    })

    hold_col = get_holdOrder_collection()
    hold_pending = await hold_col.count_documents({
        "branchName": branchName,
        "approvalStatus": "Sending to Approval"
    })

    result = DayEndValidation()
    if so_pending > 0 or hold_pending > 0:
        result.soApprovalsStatus = "failed"
        result.soPendings = so_pending + hold_pending
    else:
        result.soApprovalsStatus = "success"
        result.soPendings = 0

    # ----- Dispatch -----
    dispatch_col = get_dispatch_collection()
    dispatch_pending = await dispatch_col.count_documents({
        "branchName": branchName,
        "status": "dispatched"
    })
    result.dispatchStatus = "failed" if dispatch_pending > 0 else "success"
    result.dispatchPendings = dispatch_pending if dispatch_pending > 0 else 0

    # ----- Item Transfer -----
    item_col = get_itemtransfer_collection()
    item_pending = await item_col.count_documents({
        "branchName": branchName,
        "status": "Pending"
    })
    result.itemTransferStatus = "failed" if item_pending > 0 else "success"
    result.itemTransferPendings = item_pending if item_pending > 0 else 0

    # ----- Store Dispatch -----
    store_col = get_storeDispatch_collection()
    store_pending = await store_col.count_documents({
        "branchName": branchName,
        "status": "dispatched"
    })
    result.storeDispatchStatus = "failed" if store_pending > 0 else "success"
    result.storeDispatchPendings = store_pending if store_pending > 0 else 0

    # ---------- UPSERT INTO DB ----------
    dayend_col = get_dayEndValidation_collection()
    update_dict = result.dict(exclude_none=True)
    update_dict["branchName"] = branchName
    update_dict["date"] = today

    existing = await dayend_col.find_one({"branchName": branchName, "date": today})
    if existing:
        await dayend_col.update_one({"_id": existing["_id"]}, {"$set": update_dict})
        update_dict["dayEndId"] = str(existing["_id"])
    else:
        inserted = await dayend_col.insert_one(update_dict)
        update_dict["dayEndId"] = str(inserted.inserted_id)

    return DayEndValidation(**update_dict)


@router.patch("/dayendValidation/{dayEndId}", response_model=DayEndValidation)
async def patch_day_end(dayEndId: str, payload: DayEndValidationPost):
    """
    Patch update an existing DayEndValidation document by its ID.
    """
    dayend_col = get_dayEndValidation_collection()
    try:
        obj_id = ObjectId(dayEndId)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid dayEndId")

    existing = await dayend_col.find_one({"_id": obj_id})
    if not existing:
        raise HTTPException(status_code=404, detail="DayEndValidation not found")

    update_dict = payload.dict(exclude_unset=True)
    if not update_dict:
        raise HTTPException(status_code=400, detail="No fields provided for update")

    await dayend_col.update_one({"_id": obj_id}, {"$set": update_dict})

    updated = await dayend_col.find_one({"_id": obj_id})
    updated["dayEndId"] = str(updated["_id"])

    return DayEndValidation(**updated)






import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, logger, WebSocket, WebSocketDisconnect
from bson import ObjectId
from datetime import datetime, timezone

from pydantic import ValidationError
import pytz

from Branchwiseitem.routes import update_system_stock
from SalesOrder.utils import get_counter_collection, get_salesOrder_collection
from warehouseItems.routes import adjust_warehouse_item_stock
from .models import Dispatch, DispatchPost, get_iso_datetime
from .utils import get_dispatch_collection
from Employee.utils import get_employee_collection
from Branches.utils import get_branch_collection

router = APIRouter()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

connected_clients = set()

connected_clients = set()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.add(websocket)
    logger.info(f"🔌 WebSocket connected: {websocket.client}")
    try:
        while True:
            await websocket.receive_text()  # Keep the connection alive
    except WebSocketDisconnect:
        logger.warning(f"⚠️ WebSocket temporarily disconnected: {websocket.client}")
        # ✅ Don't remove from connected_clients
    except Exception as e:
        logger.error(f"❌ WebSocket error: {e}")


# Local timezone
LOCAL_TZ = pytz.timezone("Asia/Kolkata")

def utc_to_local(dt: datetime) -> datetime:
    """Convert UTC datetime to local timezone (Asia/Kolkata)."""
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)
    return dt.astimezone(LOCAL_TZ)

# ✅ Sequence generator
async def get_next_dispatch_sequence() -> int:
    counters_collection = get_counter_collection()
    result = await counters_collection.find_one_and_update(
        {"prefix": "dispatch_global"},
        {"$inc": {"sequence": 1}},
        upsert=True,
        return_document=True
    )
    return result["sequence"]


@router.post("/", response_model=dict)
async def create_dispatch(dispatch: DispatchPost):
    new_dispatch_data = dispatch.dict()

    # ✅ Normalize qty/weight exclusivity
    qty_list = new_dispatch_data.get("qty") or []
    weight_list = new_dispatch_data.get("weight") or []

    max_len = max(len(qty_list), len(weight_list))
    normalized_qty, normalized_weight = [], []

    for i in range(max_len):
        qty_val = qty_list[i] if i < len(qty_list) else 0
        weight_val = weight_list[i] if i < len(weight_list) else 0.0

        if qty_val and qty_val > 0:
            normalized_qty.append(qty_val)
            normalized_weight.append(0.0)
        elif weight_val and weight_val > 0:
            normalized_qty.append(0)
            normalized_weight.append(weight_val)
        else:
            normalized_qty.append(0)
            normalized_weight.append(0.0)

    new_dispatch_data["qty"] = normalized_qty
    new_dispatch_data["weight"] = normalized_weight

    # ✅ Fetch the driver's phone number
    employee_collection = get_employee_collection()
    driver_doc = await employee_collection.find_one({
        "firstName": dispatch.driverName,
        "position": "Driver"
    })
    new_dispatch_data["driverNumber"] = driver_doc.get("phoneNumber") if driver_doc else None

    # ✅ Fetch branch alias (use aliasName field instead of alias)
    branch_collection = get_branch_collection()
    branch_doc = await branch_collection.find_one({"branchName": dispatch.branchName})

    if not branch_doc or not branch_doc.get("aliasName"):
        raise HTTPException(status_code=400, detail="Invalid branch or missing alias")

    branch_alias = branch_doc["aliasName"].upper()
    warehouse_name = branch_doc.get("warehouseName")

    # ✅ Generate formatted dispatch number
    try:
        seq_num = await get_next_dispatch_sequence()
        formatted_dispatch_no = f"DI{branch_alias}{str(seq_num).zfill(5)}"
        new_dispatch_data["dispatchNo"] = str(formatted_dispatch_no)
    except Exception as e:
        logger.error(f"Failed to generate dispatchNo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate dispatch number")

    # ✅ Insert into MongoDB
    result = await get_dispatch_collection().insert_one(new_dispatch_data)


    try:
        for item_code, qty, variance_name in zip(
            new_dispatch_data.get("itemCode", []),
            new_dispatch_data.get("qty", []),
            new_dispatch_data.get("varianceName", [])
        ):
            await adjust_warehouse_item_stock(
                variance_item_code=item_code,
                variance_name=variance_name,
                warehouse_name=warehouse_name,
                qty=-abs(qty)
            )
    except Exception as e:
        logger.error(f"❌ Failed to update warehouse stock: {e}", exc_info=True)

    for ws in connected_clients.copy():
        try:
            await ws.send_json({
                "type": "dispatch_created",
                "message": f"Stock dispatched for {dispatch['branchName']} by {dispatch['createdBy']}",
                "dispatchNo": new_dispatch_data["dispatchNo"],
                "branchAlias": branch_alias,
                "timestamp": datetime.utcnow().isoformat()
            })
        except Exception:
            continue

    return {
        "message": "Dispatch created successfully",
        "inserted_id": str(result.inserted_id),
        "dispatchNo": new_dispatch_data["dispatchNo"],
        "branchAlias": branch_alias,
        "date": new_dispatch_data.get("date", datetime.utcnow().isoformat())
    }

def build_date_range_filter(start: Optional[str], end: Optional[str], field_name: str):
    """
    Build a MongoDB date range filter for a given field.
    Accepts dates in DD-MM-YYYY format.
    """
    date_filter = {}
    try:
        if start:
            start_date = datetime.strptime(start, "%d-%m-%Y").replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            date_filter["$gte"] = start_date
        if end:
            end_date = datetime.strptime(end, "%d-%m-%Y").replace(
                hour=23, minute=59, second=59, microsecond=999999
            )
            date_filter["$lte"] = end_date
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid {field_name} format. Use DD-MM-YYYY.")

    return date_filter if date_filter else None



@router.get("/", response_model=List[Dispatch])
async def get_all_dispatch_entries(
    start_date: Optional[str] = Query(None, description="Start date in DD-MM-YYYY format"),
    end_date: Optional[str] = Query(None, description="End date in DD-MM-YYYY format"),
    status: Optional[str] = Query(None, description="Filter by dispatch status (case-insensitive)"),
    approvalStatus: Optional[str] = Query(None, description="Filter by approval status (case-insensitive)"),
    approvalType: Optional[str] = Query(None, description="Filter by approval type (case-insensitive)"),
    summary: Optional[str] = Query(None, description="Filter by summary text (case-insensitive)"),
    approvalDate: Optional[str] = Query(None, description="Exact approval date (DD-MM-YYYY)"),
    approvalStartDate: Optional[str] = Query(None, description="Start of approval date range (DD-MM-YYYY)"),
    approvalEndDate: Optional[str] = Query(None, description="End of approval date range (DD-MM-YYYY)"),
    dispatch_no: Optional[str] = Query(None, description="Filter by dispatch number"),
    branchName: Optional[str] = Query(None, description="Filter by branch name"),
):
    """
    Fetch all dispatch entries, optionally filtering by various parameters.
    Converts UTC datetimes to local timezone (Asia/Kolkata).
    """
    query = {}

    if status:
        query["status"] = {"$regex": status, "$options": "i"}

    if dispatch_no:
        query["dispatchNo"] = {"$regex": dispatch_no, "$options": "i"}

    if branchName:
        query["branchName"] = {"$regex": branchName, "$options": "i"}

    # Approval filters
    approval_filter = {}
    if approvalStatus:
        approval_filter["approvalStatus"] = {"$regex": approvalStatus, "$options": "i"}
    if approvalType:
        approval_filter["approvalType"] = {"$regex": approvalType, "$options": "i"}
    if summary:
        approval_filter["summary"] = {"$regex": summary, "$options": "i"}

    # Approval date filtering
    if approvalDate:
        try:
            approval_date_obj = datetime.strptime(approvalDate, "%d-%m-%Y")
            start_day = approval_date_obj.replace(hour=0, minute=0, second=0, microsecond=0)
            end_day = approval_date_obj.replace(hour=23, minute=59, second=59, microsecond=999999)
            approval_filter["approvalDate"] = {"$gte": start_day, "$lte": end_day}
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid approvalDate format. Use DD-MM-YYYY.")
    else:
        approval_date_range = build_date_range_filter(approvalStartDate, approvalEndDate, "approvalDate")
        if approval_date_range:
            approval_filter["approvalDate"] = approval_date_range

    if approval_filter:
        query["approvalDetails"] = {"$elemMatch": approval_filter}

    # Main date range filter
    date_range_filter = build_date_range_filter(start_date, end_date, "date")
    if date_range_filter:
        query["date"] = date_range_filter

    # Fetch data
    dispatch_entries = await get_dispatch_collection().find(query).to_list(length=None)
    formatted_dispatch_entries = []

    for entry in dispatch_entries:
        entry["dispatchId"] = str(entry.pop("_id"))
        if "dispatchNo" in entry:
            entry["dispatchNo"] = str(entry["dispatchNo"])

        # 🔹 Convert datetime fields to local timezone
        if "date" in entry and isinstance(entry["date"], datetime):
            entry["date"] = utc_to_local(entry["date"])

        if "receivedTime" in entry and isinstance(entry["receivedTime"], datetime):
            entry["receivedTime"] = utc_to_local(entry["receivedTime"])

        # Convert nested approval dates
        if "approvalDetails" in entry and isinstance(entry["approvalDetails"], list):
            for approval in entry["approvalDetails"]:
                if (
                    isinstance(approval, dict)
                    and "approvalDate" in approval
                    and isinstance(approval["approvalDate"], datetime)
                ):
                    approval["approvalDate"] = utc_to_local(approval["approvalDate"])

        # Validate with Pydantic
        try:
            formatted_dispatch_entries.append(Dispatch(**entry))
        except ValidationError as e:
            print(f"⚠️ Validation error for entry: {entry.get('dispatchNo', 'Unknown')}")
            print(f"Details: {e}")
            continue
    return formatted_dispatch_entries

@router.get("/paginated")
async def get_paginated_dispatch_entries(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
):
    query = {"status": {"$ne": "Cancel"}}

    # Date filters
    if start_date or end_date:
        try:
            date_filter = {}
            if start_date:
                start_date_obj = datetime.strptime(start_date, "%d-%m-%Y")
                date_filter["$gte"] = start_date_obj.replace(hour=0, minute=0).isoformat()
            if end_date:
                end_date_obj = datetime.strptime(end_date, "%d-%m-%Y")
                date_filter["$lte"] = end_date_obj.replace(hour=23, minute=59, second=59).isoformat()
            query["date"] = date_filter
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use DD-MM-YYYY.")

    collection = get_dispatch_collection()
    total_count = await collection.count_documents(query)

    skip = (page - 1) * page_size
    cursor = await collection.find(query).skip(skip).limit(page_size)
    dispatch_entries = []
    async for entry in cursor:
        entry["dispatchId"] = str(entry["_id"])
        entry["dispatchNo"] = str(entry.get("dispatchNo", ""))  # ✅ force string
        dispatch_entries.append(Dispatch(**entry).dict())


    total_pages = (total_count + page_size - 1) // page_size

    return {
        "data": dispatch_entries,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total_count,
            "total_pages": total_pages,
        },
    }


@router.get("/{dispatch_id}", response_model=Dispatch)
async def get_dispatch_by_id(dispatch_id: str):
    """
    Fetch a dispatch entry by its ID.

    :param dispatch_id: The ID of the dispatch entry.
    :return: The Dispatch object.
    
    """
    dispatch = await get_dispatch_collection().find_one({"_id": ObjectId(dispatch_id)})
    if dispatch:
        dispatch["dispatchId"] = str(dispatch["_id"])
        dispatch["dispatchNo"] = str(dispatch.get("dispatchNo", ""))  # ✅ force string
        return Dispatch(**dispatch)
    else:
        raise HTTPException(status_code=404, detail="Dispatch not found")


@router.put("/{dispatch_id}")
async def update_dispatch(dispatch_id: str, dispatch: DispatchPost):
    
    updated_dispatch = dispatch.dict(exclude_unset=True)  # Exclude unset fields
    result = get_dispatch_collection().update_one({"_id": ObjectId(dispatch_id)}, {"$set": updated_dispatch})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Dispatch not found")
    return {"message": "Dispatch updated successfully"}

@router.patch("/{dispatch_id}")
async def patch_dispatch(dispatch_id: str, dispatch_patch: DispatchPost):
    existing_dispatch = await get_dispatch_collection().find_one({"_id": ObjectId(dispatch_id)})
    if not existing_dispatch:
        print(f"❌ Dispatch not found in DB for id={dispatch_id}")
        raise HTTPException(status_code=404, detail="Dispatch not found")

    updated_fields = {
        key: value
        for key, value in dispatch_patch.dict(exclude_unset=True).items()
        if value is not None
    }

    # Rule: enforce qty/weight exclusivity only if one is provided
    if "receivedQty" in updated_fields and "receivedWeight" not in updated_fields:
        qty_values = updated_fields["receivedQty"]
        if isinstance(qty_values, list) and any(q > 0 for q in qty_values):
            updated_fields["receivedWeight"] = [0.0] * len(qty_values)

    elif "receivedWeight" in updated_fields and "receivedQty" not in updated_fields:
        weight_values = updated_fields["receivedWeight"]
        if isinstance(weight_values, list) and any(w > 0 for w in weight_values):
            updated_fields["receivedQty"] = [0] * len(weight_values)

    # ✅ Handle receivedTime — ensure it's stored as ISO UTC string
    if "receivedTime" in updated_fields:
        received_time = updated_fields["receivedTime"]
        if isinstance(received_time, datetime):
            # normalize to UTC ISO format
            updated_fields["receivedTime"] = received_time.astimezone(timezone.utc).isoformat()
        else:
            try:
                # handle string timestamps
                parsed_time = datetime.fromisoformat(str(received_time))
                updated_fields["receivedTime"] = parsed_time.astimezone(timezone.utc).isoformat()
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid datetime format for receivedTime")

    # ✅ Handle driverName → auto-fill driverNumber
    if "driverName" in updated_fields:
        employee = await get_employee_collection().find_one({"firstName": updated_fields["driverName"]})
        if employee:
            phone_number = employee.get("phoneNumber")
            updated_fields["driverNumber"] = str(phone_number) if phone_number else ""
        else:
            raise HTTPException(status_code=404, detail=f"Employee '{updated_fields['driverName']}' not found")

    # ✅ Perform update in MongoDB
    if updated_fields:
        result = await get_dispatch_collection().update_one(
            {"_id": ObjectId(dispatch_id)},
            {"$set": updated_fields}
        )
        if result.modified_count == 0:
            print(f"❌ Update failed for dispatch {dispatch_id}")
            raise HTTPException(status_code=500, detail="Failed to update Dispatch")

    updated_dispatch = await get_dispatch_collection().find_one({"_id": ObjectId(dispatch_id)})
    updated_dispatch["_id"] = str(updated_dispatch["_id"])
    updated_dispatch["dispatchNo"] = str(updated_dispatch.get("dispatchNo", ""))

    # ✅ If dispatch status is RECEIVED — update system stock
    if updated_dispatch.get("status") in ["received", "pending_approval"]:
        
        variance_names = updated_dispatch.get("varianceName", [])
        branch = updated_dispatch.get("branchName", "")
        stock_updates = updated_dispatch.get("receivedQty", [])
        weight_updates = updated_dispatch.get("receivedWeight", [])

        # Run the async update function
        result = await update_system_stock(
            variance_names=variance_names,
            branch=branch,
            stock_updates=stock_updates,
            weight_updates=weight_updates
            )

        for ws in connected_clients.copy():
            try:
                await ws.send_json({
                    "type": "dispatch_received",
                    "message": f"Stock received by {updated_dispatch['createdBy']} in {branch}",
                    "dispatchNo": updated_dispatch["dispatchNo"],
                    "branch": branch,
                    "timestamp": datetime.utcnow().isoformat()
                })
            except Exception:
                continue


    return updated_dispatch

@router.delete("/{dispatch_id}")
async def delete_dispatch(dispatch_id: str):
    """
    Delete a dispatch entry by its ID.

    :param dispatch_id: The ID of the dispatch entry.
    :return: Success message.
    """
    result = get_dispatch_collection().delete_one({"_id": ObjectId(dispatch_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Dispatch not found")
    return {"message": "Dispatch deleted successfully"}


@router.patch("/patchapproval/{salesOrder_id}")
async def patch_salesOrder(salesOrder_id: str, salesOrder_patch: DispatchPost):
    existing_salesOrder = get_dispatch_collection().find_one({"_id": ObjectId(salesOrder_id)})
    if not existing_salesOrder:
        raise HTTPException(status_code=404, detail="salesOrder not found")

    # Convert the Pydantic model to a dictionary, excluding unset values
    updated_fields = salesOrder_patch.dict(exclude_unset=True)

    # Update only the last approval detail if it exists
    if "approvalDetails" in updated_fields:
        new_approval = updated_fields["approvalDetails"][0]
        existing_approvals = existing_salesOrder.get("approvalDetails", [])

        if existing_approvals:
            # Update the last approval detail in the list
            existing_approvals[-1].update(new_approval)
            updated_fields["approvalDetails"] = existing_approvals
        else:
            # If no existing approvals, just add the new one
            updated_fields["approvalDetails"] = [new_approval]

    # Update the document if there are changes
    if updated_fields:
        result = get_dispatch_collection().update_one(
            {"_id": ObjectId(salesOrder_id)},
            {"$set": updated_fields}
        )
        if result.modified_count == 0:
            raise HTTPException(status_code=500, detail="Failed to update salesOrder")

    # Fetch and return the updated sales order
    updated_salesOrder = get_dispatch_collection().find_one({"_id": ObjectId(salesOrder_id)})
    updated_salesOrder["_id"] = str(updated_salesOrder["_id"])
    updated_salesOrder["dispatchNo"] = str(updated_salesOrder.get("dispatchNo", ""))  # ✅ force string
    return updated_salesOrder


@router.patch("/{dispatch_id}/status")
async def change_dispatch_status(dispatch_id: str, status: str):
    try:
        obj_id = ObjectId(dispatch_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid dispatch id")

    dispatch = await get_dispatch_collection().find_one({"_id": obj_id})
    if not dispatch:
        raise HTTPException(status_code=404, detail="Dispatch not found")

    result = await get_dispatch_collection().update_one(
        {"_id": obj_id},
        {"$set": {"status": status}}
    )

    if result.modified_count == 0:
        if dispatch.get("status") == status:
            return {"message": f"Dispatch already in '{status}' status"}
        raise HTTPException(status_code=500, detail="Failed to update Dispatch status")

    if dispatch.get("type") == "FG":
        try:
            branch_name = dispatch.get("branchName")
            branch_doc = await get_branch_collection().find_one({"branchName": branch_name})
            if not branch_doc:  
                raise HTTPException(status_code=404, detail="Branch not found")
            warehouse_name = branch_doc.get("warehouseName")

            item_codes = dispatch.get("itemCode", [])
            variances = dispatch.get("varianceName", [])
            qtys = dispatch.get("qty", [])
            weights = dispatch.get("weight", [])

            combined_qty = []
            max_len = max(len(qtys), len(weights))
            for i in range(max_len):
                q = qtys[i] if i < len(qtys) else 0
                w = weights[i] if i < len(weights) else 0
                combined_qty.append(q if q > 0 else w)

            for item_code, variance_name, qty in zip(item_codes, variances, combined_qty):
                await adjust_warehouse_item_stock(
                    variance_item_code=item_code,
                    variance_name=variance_name,
                    warehouse_name=warehouse_name,
                    qty=abs(qty)
                )

        except Exception as e:
            logger.error(f"❌ Failed to increase FG stock: {e}", exc_info=True)
        
        for ws in connected_clients.copy():
            try:
                message = {
                    "type": "dispatch_cancelled",
                    "message": f"Stock cancelled for {dispatch['branchName']} by {dispatch['createdBy']}",
                    "dispatchNo": dispatch["dispatchNo"],
                    "branchAlias": dispatch["aliasName"],
                    "timestamp": datetime.utcnow().isoformat()
                }
                await ws.send_json(message)
                print(f"✅ WS notification sent successfully to {ws.client} for FG dispatch {dispatch['dispatchNo']}")
            except Exception as e:
                print(f"⚠️ Failed to send FG WS notification to {ws.client}: {e}")
                continue

    # ✅ If dispatch is linked to SO, update its status
    if dispatch.get("type") == "SO":
        sale_order_id = dispatch.get("saleOrderNo")
        if sale_order_id:
            sale_order = await get_salesOrder_collection().find_one({"saleOrderNo": sale_order_id})
            if sale_order:
                await get_salesOrder_collection().update_one(
                    {"saleOrderNo": sale_order_id},
                    {"$set": {"status": "ProductionEntry"}}
                )
            else:
                raise HTTPException(status_code=404, detail="Sale order not found")
            
            for ws in connected_clients.copy():
                try:
                    message = {
                        "type": "dispatch_cancelled",
                        "message": f"Saleorder dispatch cancelled for {dispatch['branchName']} by {dispatch['createdBy']}",
                        "dispatchNo": dispatch["dispatchNo"],
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    await ws.send_json(message)
                    print(f"✅ WS notification sent successfully to {ws.client} for SO dispatch {dispatch['dispatchNo']}")
                except Exception as e:
                    print(f"⚠️ Failed to send SO WS notification to {ws.client}: {e}")
                    continue

    return {"message": "Dispatch status updated successfully"}



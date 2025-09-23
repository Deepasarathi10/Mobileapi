from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from bson import ObjectId
from datetime import datetime
from pymongo import DESCENDING

from rawMaterials.utils import get_raw_Matrials_collection
from SalesOrder.utils import get_salesOrder_collection
from Branches.utils import get_branch_collection
from sections.utils import get_sessions_collection
from .models import Dispatch, DispatchPost, get_iso_datetime
from .utils import get_dispatch_collection, get_purchaseitem_collection

router = APIRouter()


# ---------------------------
# 📌 Helper to parse multiple date formats
# ---------------------------
def try_parse_date(date_str: str) -> Optional[datetime]:
    for fmt in ("%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


# ---------------------------
# ✅ Create Dispatch
# ---------------------------
from fastapi import APIRouter
from datetime import datetime
from pymongo import DESCENDING

router = APIRouter()

@router.post("/", response_model=dict)
async def create_dispatch(dispatch: DispatchPost):
    coll = get_dispatch_collection()
    raw_coll = get_purchaseitem_collection()

    # Get last dispatch number
    last_doc = await coll.find_one(
        {"dispatchNumber": {"$exists": True}},
        sort=[("dispatchNumber", DESCENDING)]
    )
    last_number = last_doc["dispatchNumber"] if last_doc else 0
    next_dispatch_number = last_number + 1

    # Prepare new dispatch
    new_dispatch = dispatch.model_dump()
    new_dispatch["dispatchNumber"] = next_dispatch_number
    new_dispatch["date"] = new_dispatch.get("date", get_iso_datetime())

    # Insert dispatch record
    result = await coll.insert_one(new_dispatch)

    # 🔽 Update stock in rawMaterials
    variance_names = new_dispatch.get("varianceName", []) or []
    uoms = new_dispatch.get("uom", []) or []
    qtys = new_dispatch.get("qty", []) or []
    weights = new_dispatch.get("weight", []) or []

    for i, v_name in enumerate(variance_names):
        if not v_name:
            continue

        # Determine which field to use (qty or weight) based on UOM
        uom = (uoms[i].lower() if i < len(uoms) and uoms[i] else "").strip()
        qty_value = None

        if uom in ["kg", "kgs", "ltr", "g", "ml"]:
            if i < len(weights) and weights[i] is not None:
                qty_value = float(weights[i])  # ✅ fractional allowed
        elif uom in ["pcs", "pkt", "nos"]:
            if i < len(qtys) and qtys[i] is not None:
                qty_value = int(qtys[i])  # ✅ enforce integer only
        else:
            continue  # skip unsupported UOM

        if qty_value is None:
            continue  # skip if no valid qty/weight found

        # Find the raw material by itemName (varianceName maps to itemName)
        raw_item = await raw_coll.find_one({"itemName": v_name})

        if raw_item:
            new_qty = raw_item.get("stockQuantity", 0) - qty_value
            await raw_coll.update_one(
                {"_id": raw_item["_id"]},
                {
                    "$set": {
                        "stockQuantity": new_qty,
                        "lastUpdatedDate": datetime.utcnow(),
                        "lastUpdatedTime": datetime.utcnow(),
                    }
                }
            )

    return {
        "inserted_id": str(result.inserted_id),
        "date": new_dispatch["date"],
        "dispatchNumber": next_dispatch_number
    }

# ---------------------------
# ✅ Get All Dispatch Entries
# ---------------------------
@router.get("/", response_model=List[Dispatch])
async def get_all_dispatch_entries(
    branchName: Optional[str] = Query(None, description="Filter by branch"),
    date: Optional[str] = Query(None, description="Filter by specific date (DD-MM-YYYY or YYYY-MM-DD)"),
    start_date: Optional[str] = Query(None, description="Start date for range filter"),
    end_date: Optional[str] = Query(None, description="End date for range filter"),
):
    query = {"status": {"$ne": "Cancel"}}

    if branchName:
        query["branchName"] = branchName

    # ---------------- Date Filter ----------------
    date_filter = {}
    if date:
        date_obj = try_parse_date(date)
        if not date_obj:
            raise HTTPException(status_code=400, detail="Invalid date format.")
        start_dt = date_obj.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        end_dt = date_obj.replace(hour=23, minute=59, second=59, microsecond=999999).isoformat()
        date_filter = {"$gte": start_dt, "$lte": end_dt}
    else:
        if start_date:
            start_obj = try_parse_date(start_date)
            if not start_obj:
                raise HTTPException(status_code=400, detail="Invalid start_date format.")
            date_filter["$gte"] = start_obj.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        if end_date:
            end_obj = try_parse_date(end_date)
            if not end_obj:
                raise HTTPException(status_code=400, detail="Invalid end_date format.")
            date_filter["$lte"] = end_obj.replace(hour=23, minute=59, second=59, microsecond=999999).isoformat()

    if date_filter:
        query["date"] = date_filter

    try:
        # ✅ collections must be Motor collections
        dispatch_collection = get_dispatch_collection()
        raw_materials_collection = get_raw_Matrials_collection()
        branch_collection = get_branch_collection()
        section_collection = get_sessions_collection()

        # ---------------- Raw Materials ----------------
        raw_materials_cursor = raw_materials_collection.find(
            {},
            {"itemName": 1, "varianceItemcode": 1, "category": 1, "subCategory": 1}
        )
        raw_materials_list = await raw_materials_cursor.to_list(length=None)

        raw_materials_map = {
            rm.get("itemName", ""): {
                "itemCode": rm.get("varianceItemcode", ""),
                "category": rm.get("category") or "",
                "subCategory": rm.get("subCategory") or ""
            }
            for rm in raw_materials_list
        }

        # ---------------- Branch ----------------
        branch_cursor = branch_collection.find({}, {"branchName": 1, "code": 1, "location": 1})
        branch_list = await branch_cursor.to_list(length=None)
        branch_map = {
            b["branchName"]: {"code": b.get("code", ""), "location": b.get("location", "")}
            for b in branch_list
        }

        # ---------------- Section ----------------
        section_cursor = section_collection.find({}, {"sectionsName": 1, "code": 1, "location": 1})
        section_list = await section_cursor.to_list(length=None)
        section_map = {
            s["sectionsName"]: {"code": s.get("code", ""), "location": s.get("location", "")}
            for s in section_list
        }

        # ---------------- Dispatch ----------------
        dispatch_cursor = dispatch_collection.find(query)
        dispatch_list = await dispatch_cursor.to_list(length=None)

        formatted_dispatch_entries = []
        for entry in dispatch_list:
            entry["dispatchId"] = str(entry.get("_id", ""))

            if isinstance(entry.get("date"), str):
                try:
                    entry["date"] = datetime.fromisoformat(entry["date"])
                except Exception:
                    entry["date"] = get_iso_datetime()

            # Ensure list
            item_names = entry.get("itemName", [])
            if not isinstance(item_names, list):
                item_names = [item_names] if item_names else []

            entry["itemCode"] = []
            entry["category"] = []
            entry["subCategory"] = []
            for name in item_names:
                mapped_data = raw_materials_map.get(name, {"itemCode": "", "category": "", "subCategory": ""})
                entry["itemCode"].append(mapped_data["itemCode"])
                entry["category"].append(mapped_data["category"])
                entry["subCategory"].append(mapped_data["subCategory"])

            # Branch/Section mapping
            bn = entry.get("branchName", "")
            if bn in branch_map:
                entry["towarehouseCode"] = branch_map[bn]["code"]
                entry["location"] = branch_map[bn]["location"]
            elif bn in section_map:
                entry["towarehouseCode"] = section_map[bn]["code"]
                entry["location"] = section_map[bn]["location"]

            formatted_dispatch_entries.append(Dispatch(**entry))

        return formatted_dispatch_entries

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



# ---------------------------
# ✅ Get Dispatch by ID
# ---------------------------
@router.get("/{dispatch_id}", response_model=Dispatch)
async def get_dispatch_by_id(dispatch_id: str):
    dispatch = await get_dispatch_collection().find_one({"_id": ObjectId(dispatch_id)})
    if not dispatch:
        raise HTTPException(status_code=404, detail="Dispatch not found")

    dispatch["dispatchId"] = str(dispatch["_id"])

    if isinstance(dispatch.get("date"), str):
        try:
            dispatch["date"] = datetime.fromisoformat(dispatch["date"])
        except Exception:
            dispatch["date"] = get_iso_datetime()

    return Dispatch(**dispatch)


# ---------------------------
# ✅ Update Full Dispatch
# ---------------------------
@router.put("/{dispatch_id}")
async def update_dispatch(dispatch_id: str, dispatch: DispatchPost):
    updated_dispatch = dispatch.dict(exclude_unset=True)
    result = await get_dispatch_collection().update_one(
        {"_id": ObjectId(dispatch_id)}, {"$set": updated_dispatch}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Dispatch not found")
    return {"message": "Dispatch updated successfully"}


# ---------------------------
# ✅ Patch Dispatch (Partial Update)
# ---------------------------
@router.patch("/{dispatch_id}")
async def patch_dispatch(dispatch_id: str, dispatch_patch: DispatchPost):
    existing_dispatch = await get_dispatch_collection().find_one({"_id": ObjectId(dispatch_id)})
    if not existing_dispatch:
        raise HTTPException(status_code=404, detail="Dispatch not found")

    updated_fields = {k: v for k, v in dispatch_patch.dict(exclude_unset=True).items() if v is not None}
    if updated_fields:
        result = await get_dispatch_collection().update_one(
            {"_id": ObjectId(dispatch_id)}, {"$set": updated_fields}
        )
        if result.modified_count == 0:
            raise HTTPException(status_code=500, detail="Failed to update Dispatch")

    updated_dispatch = await get_dispatch_collection().find_one({"_id": ObjectId(dispatch_id)})
    updated_dispatch["dispatchId"] = str(updated_dispatch["_id"])

    if isinstance(updated_dispatch.get("date"), str):
        try:
            updated_dispatch["date"] = datetime.fromisoformat(updated_dispatch["date"])
        except Exception:
            updated_dispatch["date"] = get_iso_datetime()

    return updated_dispatch


# ---------------------------
# ✅ Delete Dispatch
# ---------------------------
@router.delete("/{dispatch_id}")
async def delete_dispatch(dispatch_id: str):
    result = await get_dispatch_collection().delete_one({"_id": ObjectId(dispatch_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Dispatch not found")
    return {"message": "Dispatch deleted successfully"}


# ---------------------------
# ✅ Change Dispatch Status + Update Sale Order if type = SO
# ---------------------------
@router.patch("/{dispatch_id}/status")
async def change_dispatch_status(dispatch_id: str, status: str):
    dispatch = await get_dispatch_collection().find_one({"_id": ObjectId(dispatch_id)})
    if not dispatch:
        raise HTTPException(status_code=404, detail="Dispatch not found")

    result = await get_dispatch_collection().update_one(
        {"_id": ObjectId(dispatch_id)}, {"$set": {"status": status}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=500, detail="Failed to update Dispatch status")

    if dispatch.get("type") == "SO":
        sale_order_id = dispatch.get("saleOrderNo")
        if sale_order_id:
            sale_order = await get_salesOrder_collection().find_one({"_id": ObjectId(sale_order_id)})
            if sale_order:
                await get_salesOrder_collection().update_one(
                    {"_id": ObjectId(sale_order_id)},
                    {"$set": {"status": "productionEntry"}}
                )
            else:
                raise HTTPException(status_code=404, detail="Sale order not found")

    return {"message": "Dispatch status updated successfully"}

from datetime import datetime
from typing import List
from fastapi import APIRouter, HTTPException
from bson import ObjectId, errors as bson_errors
from Branchwiseitem.routes import reduce_system_stock
from Branches.utils import get_branch_collection
from warehouseItems.utils import get_collection  # for warehouse stock
from .models import WarehouseReturn, WarehouseReturnPost
from .utils import get_warehouse_return_collection

router = APIRouter()


# ------------------- CREATE -------------------
@router.post("/", response_model=WarehouseReturn)
async def create_warehouse_return(warehouse_return: WarehouseReturnPost):
    coll = get_warehouse_return_collection()

    # Generate warehouseReturnNumber
    last_doc = await coll.find_one(
        {"warehouseReturnNumber": {"$exists": True}},
    
    )
    if last_doc and last_doc.get("warehouseReturnNumber"):
            try:
                last_number = int(last_doc["warehouseReturnNumber"][2:])  # skip "RE"
            except:
                last_number = 0
    else:
            last_number = 0       

            next_number = last_number + 1
            warehouse_return_number = f"RE{str(next_number).zfill(4)}"

            # Prepare new document
            new_return = warehouse_return.dict()
            new_return["warehouseReturnNumber"] = warehouse_return_number
            new_return["date"] = new_return.get("date", datetime.utcnow())

            # Insert into MongoDB
            result = await coll.insert_one(new_return)
            new_return["warehouseReturnId"] = str(result.inserted_id)

    # ------------------- Reduce Branch/System Stock -------------------
    try:
        branch_name = new_return.get("branchName")
        branch_doc = await get_branch_collection().find_one({"branchName": branch_name})
        if not branch_doc or not branch_doc.get("aliasName"):
            raise HTTPException(status_code=400, detail="Invalid branch or missing aliasName")

        branch_alias = branch_doc["aliasName"].upper()

        variance_item_codes = new_return.get("itemCode", []) or []
        variance_names = new_return.get("varianceName", []) or []
        send_qtys = new_return.get("sendqty", []) or []  # <-- use sendqty in POST

        if variance_item_codes and send_qtys:
            await reduce_system_stock(
                variance_item_codes=variance_item_codes,
                variance_names=variance_names,
                qtys=send_qtys,
                alias_name=branch_alias
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reducing branchwise stock: {e}")

    return WarehouseReturn(**new_return)


# ------------------- GET ALL -------------------
@router.get("/", response_model=List[WarehouseReturn])
async def get_all_wastage_entries():
    coll = get_warehouse_return_collection()
    cursor = coll.find()
    entries = await cursor.to_list(length=None)

    formatted_entries = []
    for entry in entries:
        entry["warehouseReturnId"] = str(entry["_id"])
        del entry["_id"]
        formatted_entries.append(WarehouseReturn(**entry))

    return formatted_entries


# ------------------- GET BY ID -------------------
@router.get("/{warehouse_return_id}", response_model=WarehouseReturn)
async def get_wastage_entry_by_id(warehouse_return_id: str):
    coll = get_warehouse_return_collection()
    try:
        entry = await coll.find_one({"_id": ObjectId(warehouse_return_id)})
    except bson_errors.InvalidId:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    if not entry:
        raise HTTPException(status_code=404, detail="Warehouse Return not found")

    entry["warehouseReturnId"] = str(entry["_id"])
    return WarehouseReturn(**entry)


# ------------------- UPDATE (PUT) -------------------
@router.put("/{warehouse_return_id}")
async def update_wastage_entry(warehouse_return_id: str, warehouse_return: WarehouseReturnPost):
    coll = get_warehouse_return_collection()
    updated_data = warehouse_return.dict(exclude_unset=True)

    try:
        result = await coll.update_one(
            {"_id": ObjectId(warehouse_return_id)},
            {"$set": updated_data}
        )
    except bson_errors.InvalidId:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Warehouse Return not found")

    return {"message": "Warehouse Return updated successfully"}


# ------------------- PATCH -------------------
@router.patch("/{warehouse_return_id_or_number}", response_model=WarehouseReturn)
async def patch_warehouse_return(warehouse_return_id_or_number: str, warehouse_return_patch: WarehouseReturnPost):
    coll = get_warehouse_return_collection()
    print(f"🚀 PATCH request received for: {warehouse_return_id_or_number}")
    print("Collection used for PATCH:", coll.name)

    existing_entry = None

    # 1️⃣ Try ObjectId lookup
    try:
        existing_entry = await coll.find_one({"_id": ObjectId(warehouse_return_id_or_number)})
        print("✅ Found by ObjectId")
    except bson_errors.InvalidId:
        pass

    # 2️⃣ Fallback: try warehouseReturnNumber or string _id
    if not existing_entry:
        existing_entry = await coll.find_one({
            "$or": [
                {"_id": warehouse_return_id_or_number},  # string _id fallback
                {"warehouseReturnNumber": warehouse_return_id_or_number}
            ]
        })
        if existing_entry:
            print("✅ Found by warehouseReturnNumber or string _id")

    if not existing_entry:
        print("❌ Warehouse Return not found")
        raise HTTPException(status_code=404, detail="Warehouse Return not found")

    # 3️⃣ Apply patch updates
    updated_fields = {k: v for k, v in warehouse_return_patch.dict(exclude_unset=True).items() if v is not None}
    if updated_fields:
        await coll.update_one({"_id": existing_entry["_id"]}, {"$set": updated_fields})

    updated_entry = await coll.find_one({"_id": existing_entry["_id"]})
    updated_entry["warehouseReturnId"] = str(updated_entry["_id"])

    # 4️⃣ Update warehouse stock
    warehouse_collection = get_collection("warehouseitem")
    codes = updated_entry.get("itemCode", []) or []
    qtys = updated_entry.get("receivedqty", []) or []

    for code, qty in zip(codes, qtys):
        qty = qty or 0
        warehouse_item = await warehouse_collection.find_one({"varianceitemCode": code})
        if not warehouse_item:
            print(f"⚠️ Warehouse item not found: {code}")
            continue

        system_stock = warehouse_item.get("system_stock", [])
        if not isinstance(system_stock, list):
            system_stock = [{"warehouseName": updated_entry.get("warehouseName", "").strip().lower(),
                             "stock": int(system_stock) if isinstance(system_stock, int) else 0}]
        stock_entry = next((s for s in system_stock if s.get("warehouseName", "").strip().lower()
                            == updated_entry.get("warehouseName", "").strip().lower()), None)
        if not stock_entry:
            stock_entry = {"warehouseName": updated_entry.get("warehouseName", "").strip().lower(), "stock": 0}
            system_stock.append(stock_entry)

        old_stock = stock_entry.get("stock", 0)
        stock_entry["stock"] = old_stock + qty

        await warehouse_collection.update_one({"_id": warehouse_item["_id"]}, {"$set": {"system_stock": system_stock}})
        print(f"⬆ Updated stock for {code}: {old_stock} → {stock_entry['stock']}")

    return WarehouseReturn(**updated_entry)


# ------------------- DELETE -------------------
@router.delete("/{warehouse_return_id}")
async def delete_wastage_entry(warehouse_return_id: str):
    coll = get_warehouse_return_collection()
    try:
        result = await coll.delete_one({"_id": ObjectId(warehouse_return_id)})
    except bson_errors.InvalidId:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Warehouse Return not found")

    return {"message": "Warehouse Return deleted successfully"}

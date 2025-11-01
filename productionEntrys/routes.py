from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from bson import ObjectId
from pymongo import DESCENDING
from .models import ProductionEntry, ProductionEntryPost
from .utils import get_productionEntry_collection
from datetime import datetime, timedelta
from dateutil import parser as date_parser
from warehouseItems.utils import get_collection
router = APIRouter()

# ------------------ CREATE ------------------
@router.post("/", response_model=ProductionEntry)
async def create_production_entry(production_entry: ProductionEntryPost):
    coll = get_productionEntry_collection()
    warehouse_collection = get_collection("warehouseitem")

    try:
        # --- Generate next productionEntryNumber ---
        last_doc = await coll.find_one(
            {"productionEntryNumber": {"$exists": True}},
            sort=[("_id", -1)]
        )

        if last_doc and last_doc.get("productionEntryNumber", "").startswith("PE"):
            try:
                last_number = int(last_doc["productionEntryNumber"][2:])
            except ValueError:
                last_number = 0
        else:
            last_number = 0

        next_number = last_number + 1
        production_entry_number = f"PE{next_number:04d}"

        # --- Prepare document ---
        new_entry = production_entry.dict()
        new_entry["productionEntryNumber"] = production_entry_number
        new_entry["date"] = new_entry.get("date") or datetime.utcnow()

        # --- Insert into MongoDB ---
        result = await coll.insert_one(new_entry)
        new_entry["productionEntryId"] = str(result.inserted_id)
        new_entry["_id"] = str(result.inserted_id)

        # --- Update warehouse stock for each item ---
        codes = new_entry.get("itemCode", []) or []
        qtys = new_entry.get("qty", []) or []
        weights = new_entry.get("weight", []) or []
        warehouse_name = (new_entry.get("warehouseName") or "").strip().lower()

        if not warehouse_name:
            print("⚠️ Missing warehouseName in production entry.")
            return ProductionEntry(**new_entry)

        for idx, code in enumerate(codes):
            try:
                qty = int(qtys[idx]) if idx < len(qtys) else 0
                weight = float(weights[idx]) if idx < len(weights) else 0.0
            except (ValueError, TypeError):
                qty, weight = 0, 0.0

            # --- Find warehouse item by varianceitemCode ---
            warehouse_item = await warehouse_collection.find_one({"varianceitemCode": code})
            if not warehouse_item:
                print(f"❌ Warehouse item not found: {code}")
                continue

            measurement_type = (warehouse_item.get("measurementType") or "").strip().lower()
            system_stock = warehouse_item.get("system_stock", [])

            if not isinstance(system_stock, list):
                try:
                    existing_stock = float(system_stock)
                except (TypeError, ValueError):
                    existing_stock = 0
                system_stock = [{
                    "warehouseName": warehouse_name,
                    "stock": existing_stock
                }]

            # --- Find or create entry for this warehouse ---
            stock_entry = next(
                (s for s in system_stock if s.get("warehouseName", "").strip().lower() == warehouse_name),
                None
            )
            if not stock_entry:
                stock_entry = {"warehouseName": warehouse_name, "stock": 0}
                system_stock.append(stock_entry)

            old_stock = float(stock_entry.get("stock", 0))

            # --- Apply stock change based on measurementType ---
            if measurement_type == "count":
                stock_entry["stock"] = old_stock + qty
                print(f"⬆ Updated stock (Count) for {code}: {old_stock} → {stock_entry['stock']}")
            elif measurement_type == "weight":
                stock_entry["stock"] = old_stock + weight
                print(f"⬆ Updated stock (Weight) for {code}: {old_stock} → {stock_entry['stock']}")
            else:
                print(f"⚠️ Unknown measurementType '{measurement_type}' for {code}, skipping.")
                continue

            # --- Update warehouse document ---
            await warehouse_collection.update_one(
                {"_id": warehouse_item["_id"]},
                {"$set": {"system_stock": system_stock}}
            )

        return ProductionEntry(**new_entry)

    except Exception as exc:
        print("❌ Error creating production entry:", exc)
        raise HTTPException(status_code=500, detail="Failed to create production entry")


# ------------------ READ ALL ------------------


@router.get("/", response_model=List[ProductionEntry])
async def get_all_production_entries(date: Optional[str] = Query(None)):
    coll = get_productionEntry_collection()
    query = {}

    # 🔹 Optional date filter (DD-MM-YYYY)
    if date:
        try:
            date_obj = datetime.strptime(date, "%d-%m-%Y")
            start_date = date_obj.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(days=1)

            # 🔹 Combine both possible cases (datetime and string)
            query["$or"] = [
                {"date": {"$gte": start_date, "$lt": end_date}},  # datetime type
                {"date": {
                    "$gte": start_date.isoformat(),
                    "$lt": end_date.isoformat()
                }}  # string type
            ]

        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use DD-MM-YYYY.")

    # 🔹 Fetch documents sorted by newest first
    cursor = coll.find(query).sort("date", DESCENDING)
    docs = await cursor.to_list(length=None)

    production_entries = []
    for entry in docs:
        entry["productionEntryId"] = str(entry["_id"])
        entry["_id"] = str(entry["_id"])

        # Normalize date field
        if isinstance(entry.get("date"), str):
            try:
                entry["date"] = date_parser.parse(entry["date"])
            except Exception:
                entry["date"] = None

        production_entries.append(ProductionEntry(**entry))

    return production_entries


# ------------------ READ BY ID ------------------
@router.get("/{production_entry_id}", response_model=ProductionEntry)
async def get_production_entry_by_id(production_entry_id: str):
    coll = get_productionEntry_collection()

    try:
        entry = await coll.find_one({"_id": ObjectId(production_entry_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ObjectId format.")

    if not entry:
        raise HTTPException(status_code=404, detail="ProductionEntry not found")

    entry["productionEntryId"] = str(entry["_id"])
    entry["_id"] = str(entry["_id"])
    return ProductionEntry(**entry)


# ------------------ UPDATE (PUT) ------------------
@router.put("/{production_entry_id}")
async def update_production_entry(production_entry_id: str, production_entry: ProductionEntryPost):
    coll = get_productionEntry_collection()

    try:
        result = await coll.update_one(
            {"_id": ObjectId(production_entry_id)},
            {"$set": production_entry.dict(exclude_unset=True)}
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ObjectId format.")

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="ProductionEntry not found")

    return {"message": "ProductionEntry updated successfully"}


# ------------------ PATCH (PARTIAL UPDATE) ------------------
@router.patch("/{production_entry_id}")
async def patch_production_entry(production_entry_id: str, production_entry_patch: ProductionEntryPost):
    coll = get_productionEntry_collection()
    warehouse_collection = get_collection("warehouseitem")

    # --- Find existing entry ---
    try:
        existing = await coll.find_one({"_id": ObjectId(production_entry_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ObjectId format.")
    if not existing:
        raise HTTPException(status_code=404, detail="ProductionEntry not found")

    # --- Parse patch data safely ---
    updated_fields = {
        k: v for k, v in production_entry_patch.dict(exclude_unset=True).items()
        if v is not None
    }

    # --- Handle stock update if qty is changed ---
    if "qty" in updated_fields:
        new_qtys = updated_fields.get("qty", [])
        old_qtys = existing.get("qty", [])
        item_codes = existing.get("itemCode", [])   # from production entry
        warehouse_name = (existing.get("warehouseName") or "").strip().lower()

        for idx, code in enumerate(item_codes):
            try:
                old_qty = int(old_qtys[idx]) if idx < len(old_qtys) else 0
                new_qty = int(new_qtys[idx]) if idx < len(new_qtys) else old_qty
            except (ValueError, TypeError):
                old_qty, new_qty = 0, 0

            diff = new_qty - old_qty
            if diff == 0:
                continue  # nothing changed

            # ✅ Use varianceitemCode for warehouse lookup
            warehouse_item = await warehouse_collection.find_one({"varianceitemCode": code})
            if not warehouse_item:
                print(f"⚠️ Warehouse item not found for varianceItemCode '{code}', skipping update.")
                continue

            # --- Get system_stock list ---
            system_stock = warehouse_item.get("system_stock", [])
            if not isinstance(system_stock, list):
                system_stock = [{"warehouseName": warehouse_name, "stock": 0}]

            # --- Find matching warehouse entry ---
            stock_entry = next(
                (s for s in system_stock if s.get("warehouseName", "").strip().lower() == warehouse_name),
                None
            )
            if not stock_entry:
                stock_entry = {"warehouseName": warehouse_name, "stock": 0}
                system_stock.append(stock_entry)

            # --- Update stock ---
            old_stock = int(stock_entry.get("stock", 0))
            new_stock = old_stock + diff
            stock_entry["stock"] = max(new_stock, 0)  # prevent negatives

            await warehouse_collection.update_one(
                {"_id": warehouse_item["_id"]},
                {"$set": {"system_stock": system_stock}}
            )

            print(
                f"🔄 Stock updated for varianceItemCode {code} in {warehouse_name}: "
                f"{old_stock} → {stock_entry['stock']} (diff {diff})"
            )

    # --- Apply updates to Production Entry itself ---
    if updated_fields:
        await coll.update_one(
            {"_id": ObjectId(production_entry_id)},
            {"$set": updated_fields}
        )

    # --- Return updated entry ---
    updated_entry = await coll.find_one({"_id": ObjectId(production_entry_id)})
    updated_entry["productionEntryId"] = str(updated_entry["_id"])
    updated_entry["_id"] = str(updated_entry["_id"])

    return ProductionEntry(**updated_entry)

# ------------------ PATCH (deactive) ------------------
@router.patch("/{production_entry_id}/deactivate")
async def deactivate_production_entry(production_entry_id: str):
    coll = get_productionEntry_collection()
    warehouse_collection = get_collection("warehouseitem")

    # --- 🧩 Validate ObjectId ---
    try:
        existing = await coll.find_one({"_id": ObjectId(production_entry_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ObjectId format.")

    if not existing:
        raise HTTPException(status_code=404, detail="Production entry not found.")

    # --- ⚠️ Check current status ---
    current_status = (existing.get("status") or "active").lower()
    if current_status == "deactive":
        raise HTTPException(status_code=400, detail="Production entry already deactivated.")

    # --- 🏭 Extract item details ---
    item_codes = existing.get("itemCode", [])
    qtys = existing.get("qty", [])
    weights = existing.get("weight", [])
    warehouse_name = (existing.get("warehouseName") or "").strip().lower()

    if not warehouse_name:
        raise HTTPException(status_code=400, detail="Missing warehouse name in production entry.")

    if not item_codes:
        raise HTTPException(status_code=400, detail="No items found in production entry.")

    print(f"🔻 Deactivating entry {production_entry_id} → reducing stock in '{warehouse_name}'")

    # --- 📉 Reduce stock for each item ---
    for idx, code in enumerate(item_codes):
        try:
            qty = int(qtys[idx]) if idx < len(qtys) else 0
            weight = float(weights[idx]) if idx < len(weights) else 0.0
        except (ValueError, TypeError):
            qty, weight = 0, 0.0

        # ✅ Lookup warehouse item by varianceitemCode
        warehouse_item = await warehouse_collection.find_one({"varianceitemCode": code})
        if not warehouse_item:
            print(f"⚠️ Warehouse item not found for code '{code}', skipping.")
            continue

        measurement_type = (warehouse_item.get("measurementType") or "").strip().lower()
        system_stock = warehouse_item.get("system_stock", [])
        if not isinstance(system_stock, list):
            system_stock = [{"warehouseName": warehouse_name, "stock": 0}]

        # 🔍 Find matching warehouse entry
        stock_entry = next(
            (s for s in system_stock if s.get("warehouseName", "").strip().lower() == warehouse_name),
            None
        )
        if not stock_entry:
            stock_entry = {"warehouseName": warehouse_name, "stock": 0}
            system_stock.append(stock_entry)

        old_stock = float(stock_entry.get("stock", 0))

        # --- Choose how to subtract based on measurementType ---
        if measurement_type == "count":
            diff = qty
        elif measurement_type == "weight":
            diff = weight
        else:
            print(f"⚠️ Unknown measurementType '{measurement_type}' for {code}, skipping.")
            continue

        new_stock = old_stock - diff
        if new_stock < 0:
            raise HTTPException(
                status_code=400,
                detail=f"Not enough stock for item {code} in {warehouse_name}. "
                       f"Current: {old_stock}, trying to reduce {diff}."
            )

        stock_entry["stock"] = new_stock

        await warehouse_collection.update_one(
            {"_id": warehouse_item["_id"]},
            {"$set": {"system_stock": system_stock}}
        )

        print(
            f"🧾 Reduced {diff} ({measurement_type}) from {code} in {warehouse_name}: "
            f"{old_stock} → {new_stock}"
        )

    # --- ✅ Mark entry as deactivated ---
    await coll.update_one(
        {"_id": ObjectId(production_entry_id)},
        {"$set": {"status": "deactive"}}
    )

    updated_entry = await coll.find_one({"_id": ObjectId(production_entry_id)})
    updated_entry["productionEntryId"] = str(updated_entry["_id"])
    updated_entry["_id"] = str(updated_entry["_id"])

    print(f"✅ Production entry {production_entry_id} successfully deactivated.")

    return ProductionEntry(**updated_entry)



# ------------------ PATCH (cancelitem) ------------------
@router.patch("/{production_entry_id}/remove-item/{item_code}")
async def remove_single_item_from_entry(production_entry_id: str, item_code: str):
    coll = get_productionEntry_collection()
    warehouse_collection = get_collection("warehouseitem")

    # --- 🧩 Validate ObjectId ---
    try:
        existing = await coll.find_one({"_id": ObjectId(production_entry_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ObjectId format.")

    if not existing:
        raise HTTPException(status_code=404, detail="Production entry not found.")

    warehouse_name = (existing.get("warehouseName") or "").strip().lower()
    if not warehouse_name:
        raise HTTPException(status_code=400, detail="Missing warehouse name in production entry.")

    item_codes = existing.get("itemCode", [])
    qtys = existing.get("qty", [])
    weights = existing.get("weight", [])

    if not item_codes:
        raise HTTPException(status_code=400, detail="No items found in production entry.")

    # --- 🔍 Find target item ---
    if item_code not in item_codes:
        raise HTTPException(status_code=404, detail=f"Item '{item_code}' not found in production entry.")

    idx = item_codes.index(item_code)

    # --- Extract item data to move into cancel arrays ---
    cancel_data = {
        "cancelVarianceName": existing.get("varianceName", [])[idx] if idx < len(existing.get("varianceName", [])) else None,
        "cancelItemName": existing.get("itemName", [])[idx] if idx < len(existing.get("itemName", [])) else None,
        "cancelItemCode": item_code,
        "cancelUom": existing.get("uom", [])[idx] if idx < len(existing.get("uom", [])) else None,
        "cancelPrice": existing.get("price", [])[idx] if idx < len(existing.get("price", [])) else 0,
        "cancelQty": existing.get("qty", [])[idx] if idx < len(existing.get("qty", [])) else 0,
        "cancelAmount": existing.get("amount", [])[idx] if idx < len(existing.get("amount", [])) else 0,
        "cancelWeight": existing.get("weight", [])[idx] if idx < len(existing.get("weight", [])) else 0,
    }

    try:
        qty = int(cancel_data["cancelQty"])
        weight = float(cancel_data["cancelWeight"])
    except (ValueError, TypeError):
        qty, weight = 0, 0.0

    # --- 📉 Reduce stock in warehouse based on measurementType ---
    warehouse_item = await warehouse_collection.find_one({"varianceitemCode": item_code})
    if not warehouse_item:
        raise HTTPException(status_code=404, detail=f"Warehouse item '{item_code}' not found.")

    measurement_type = (warehouse_item.get("measurementType") or "").strip().lower()
    system_stock = warehouse_item.get("system_stock", [])
    if not isinstance(system_stock, list):
        system_stock = [{"warehouseName": warehouse_name, "stock": 0}]

    # --- Find or create warehouse entry ---
    stock_entry = next(
        (s for s in system_stock if s.get("warehouseName", "").strip().lower() == warehouse_name),
        None
    )
    if not stock_entry:
        stock_entry = {"warehouseName": warehouse_name, "stock": 0}
        system_stock.append(stock_entry)

    old_stock = float(stock_entry.get("stock", 0))

    # --- Determine reduction amount ---
    if measurement_type == "count":
        diff = qty
    elif measurement_type == "weight":
        diff = weight
    else:
        print(f"⚠️ Unknown measurementType '{measurement_type}' for {item_code}, skipping stock update.")
        diff = 0

    new_stock = old_stock - diff
    if new_stock < 0:
        raise HTTPException(
            status_code=400,
            detail=f"Not enough stock for item {item_code} in {warehouse_name}. "
                   f"Current: {old_stock}, trying to reduce {diff}."
        )

    stock_entry["stock"] = new_stock

    await warehouse_collection.update_one(
        {"_id": warehouse_item["_id"]},
        {"$set": {"system_stock": system_stock}}
    )

    print(
        f"📦 Reduced {diff} ({measurement_type}) from {item_code} in {warehouse_name}: "
        f"{old_stock} → {new_stock}"
    )

    # --- 🗑️ Move item to cancel arrays ---
    cancel_fields = [
        "cancelVarianceName", "cancelItemName", "cancelItemCode",
        "cancelUom", "cancelPrice", "cancelQty", "cancelAmount", "cancelWeight"
    ]
    active_fields = [
        "varianceName", "itemName", "itemCode", "uom", "price", "qty", "amount", "weight"
    ]

    # Initialize cancel lists if they don’t exist
    for f in cancel_fields:
        if f not in existing or not isinstance(existing[f], list):
            existing[f] = []

    # Append canceled item details
    for key, value in cancel_data.items():
        if value is not None:
            existing[key].append(value)

    # Remove from active lists
    for field in active_fields:
        values = existing.get(field, [])
        if isinstance(values, list) and idx < len(values):
            del values[idx]

    # If no active items left, deactivate entry
    if not existing.get("itemCode"):
        existing["status"] = "deactive"

    # --- Save updated document ---
    await coll.update_one(
        {"_id": ObjectId(production_entry_id)},
        {"$set": existing}
    )

    updated_entry = await coll.find_one({"_id": ObjectId(production_entry_id)})
    updated_entry["_id"] = str(updated_entry["_id"])
    updated_entry["productionEntryId"] = updated_entry["_id"]

    print(f"✅ Moved item '{item_code}' to cancel lists in entry {production_entry_id}.")

    return updated_entry


# ------------------ DELETE ------------------
@router.delete("/{production_entry_id}")
async def delete_production_entry(production_entry_id: str):
    coll = get_productionEntry_collection()

    try:
        result = await coll.delete_one({"_id": ObjectId(production_entry_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ObjectId format.")

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="ProductionEntry not found")

    return {"message": "ProductionEntry deleted successfully"}

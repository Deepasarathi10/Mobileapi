import csv
from datetime import datetime, timedelta
import io
import logging
from typing import List
from fastapi import APIRouter, File, HTTPException, UploadFile
from bson import ObjectId
from fastapi.responses import StreamingResponse
import pytz
from .models import PurchaseSubcategory, PurchaseSubcategoryPost, get_iso_datetime
from .utils import get_purchaseitem_collection, get_purchasesubcategory_collection
from storeDispatch.utils import get_dispatch_collection , get_purchasesubcategory_collection



# User-friendly header mapping for subcategory import and export
subcategory_header_mapping = {
    'Subcategory ID': 'randomId',
    'Subcategory': 'varianceName',
    'Status': 'status',
    'Created Date': 'createdDate',
    'Updated Date': 'lastUpdatedDate'
}

router = APIRouter()


def get_localized_datetime():
    """Get current UTC datetime adjusted from IST."""
    ist = pytz.timezone("Asia/Kolkata")
    localized_now = datetime.now(ist)
    adjusted_time = localized_now + timedelta(hours=5, minutes=30)
    return adjusted_time.astimezone(pytz.UTC)


async def set_counter_value(value: int, counter_id: str = "dispatchId"):
    """Set the counter value in the database."""
    counter_collection = get_purchasesubcategory_collection().database["counters"]
    await counter_collection.update_one(
        {"_id": counter_id},
        {"$set": {"sequence_value": value}},
        upsert=True
    )


async def get_current_counter_value(counter_id: str = "dispatchId"):
    """Get the current counter value from the database."""
    counter_collection = get_purchasesubcategory_collection().database["counters"]
    counter = await counter_collection.find_one({"_id": counter_id})
    return counter["sequence_value"] if counter else 0


async def initialize_counter_if_needed(counter_id: str = "dispatchId"):
    """Initialize counter to the highest existing ID number (PCxxx or PSxxx)."""
    if counter_id == "dispatchId":
        collection = get_purchasesubcategory_collection()
        id_prefix = "PS"
    else:
        raise ValueError(f"Invalid counter_id: {counter_id}")

    counter_collection = collection.database["counters"]

    highest_item = await collection.find_one(
        {"randomId": {"$regex": f"^{id_prefix}\\d+$"}},
        sort=[("randomId", -1)]
    )

    if highest_item:
        try:
            last_number = int(highest_item["randomId"][2:])
        except (ValueError, TypeError):
            last_number = 0
            logging.warning(f"Malformed randomId found: {highest_item['randomId']}")
        await counter_collection.update_one(
            {"_id": counter_id},
            {"$set": {"sequence_value": last_number}},
            upsert=True
        )
    else:
        await counter_collection.update_one(
            {"_id": counter_id},
            {"$set": {"sequence_value": 0}},
            upsert=True
        )


async def generate_sequential_subcategoryid():
    """Generate a PSxxx ID, filling gaps in the sequence."""
    collection = get_purchasesubcategory_collection()
    counter_collection = collection.database["counters"]

    counter = await counter_collection.find_one({"_id": "dispatchId"})
    current_counter = counter["sequence_value"] if counter else 0

    existing_ids = await collection.find(
        {"randomId": {"$regex": "^PS\\d+$"}}, {"randomId": 1}
    ).to_list(length=None)

    id_numbers = [int(item["randomId"][2:]) for item in existing_ids if item["randomId"].startswith("PS")]

    next_number = 1
    if id_numbers:
        expected = 1
        for num in sorted(id_numbers):
            if num > expected:
                next_number = expected
                break
            expected = num + 1
        else:
            next_number = expected

    next_number = max(next_number, current_counter + 1)

    await counter_collection.update_one(
        {"_id": "dispatchId"},
        {"$set": {"sequence_value": next_number}},
        upsert=True
    )

    return f"PS{next_number:03d}"


@router.post("/reset-counter")
async def reset_sequence():
    """Reset the counter to 0. Next ID will be PS001."""
    await set_counter_value(0)
    return {"message": "Counter reset successfully. Next ID will be PS001"}


@router.post("/", response_model=str)
async def create_purchasesubcategory(purchasesubcategory: PurchaseSubcategoryPost):
    """Create a new purchase subcategory with a sequential ID."""
    current_datetime = get_localized_datetime()

    await initialize_counter_if_needed("dispatchId")
    sequential_id = await generate_sequential_subcategoryid()

    new_purchasesubcategory_data = purchasesubcategory.dict()
    new_purchasesubcategory_data.update({
        'randomId': sequential_id,
        'status': 'active',
        'createdDate': current_datetime,
        'createdTime': current_datetime,
        'lastUpdatedDate': current_datetime,
        'lastUpdatedTime': current_datetime
    })

    result = await get_purchasesubcategory_collection().insert_one(new_purchasesubcategory_data)
    return str(result.inserted_id)


@router.get("/", response_model=List[PurchaseSubcategory])
async def get_all_purchasesubcategory():
    """Get all purchase subcategories."""
    purchasesubcategories = await get_purchasesubcategory_collection().find().to_list(length=None)
    formatted_purchasesubcategory = [
        {**sub, "dispatchId": str(sub["_id"])} for sub in purchasesubcategories
    ]
    return [PurchaseSubcategory(**sub) for sub in formatted_purchasesubcategory]


@router.get("/{purchasesubcategory_id}", response_model=PurchaseSubcategory)
async def get_purchasesubcategory_by_id(purchasesubcategory_id: str):
    """Get a specific purchase subcategory by ID."""
    try:
        subcategory = await get_purchasesubcategory_collection().find_one({"_id": ObjectId(purchasesubcategory_id)})
        if subcategory:
            subcategory["dispatchId"] = str(subcategory["_id"])
            return PurchaseSubcategory(**subcategory)
        raise HTTPException(status_code=404, detail="PurchaseSubcategory not found")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid dispatchId format")


@router.put("/{purchasesubcategory_id}")
async def update_purchasesubcategory(purchasesubcategory_id: str, purchasesubcategory: PurchaseSubcategoryPost):
    """Replace an existing purchase subcategory."""
    current_datetime = get_localized_datetime()

    updated_purchasesubcategory = purchasesubcategory.dict(exclude_unset=True)
    updated_purchasesubcategory.update({
        'lastUpdatedDate': current_datetime,
        'lastUpdatedTime': current_datetime
    })

    result = await get_purchasesubcategory_collection().update_one(
        {"_id": ObjectId(purchasesubcategory_id)},
        {"$set": updated_purchasesubcategory}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="PurchaseSubcategory not found")
    return {"message": "PurchaseSubcategory updated successfully"}


@router.patch("/{purchasesubcategory_id}")
async def patch_purchasesubcategory(purchasesubcategory_id: str, purchasesubcategory_patch: PurchaseSubcategoryPost):
    """Update specific fields of an existing purchase subcategory."""
    current_datetime = get_localized_datetime()

    existing_subcategory = await get_purchasesubcategory_collection().find_one({"_id": ObjectId(purchasesubcategory_id)})
    if not existing_subcategory:
        raise HTTPException(status_code=404, detail="PurchaseSubcategory not found")

    updated_fields = {key: value for key, value in purchasesubcategory_patch.dict(exclude_unset=True).items() if value is not None}
    if updated_fields:
        updated_fields.update({
            'lastUpdatedDate': current_datetime,
            'lastUpdatedTime': current_datetime
        })

        result = await get_purchasesubcategory_collection().update_one(
            {"_id": ObjectId(purchasesubcategory_id)},
            {"$set": updated_fields}
        )
        if result.modified_count == 0:
            raise HTTPException(status_code=500, detail="Failed to update PurchaseSubcategory")

    return {"message": "PurchaseSubcategory updated successfully"}


# --- CSV IMPORT (UPDATED) ---

def normalize(text: str) -> str:
    """Normalize for case-insensitive + space-insensitive matching."""
    return text.replace(" ", "").lower() if text else ""
@router.post("/import-csv-single-record")
async def import_item(
    file: UploadFile = File(...),
    location: str = None,
    sentDate: str = None
):
    """
    Import purchase subcategories and quantities from CSV into a single record.
    Use dispatchNumber from storeDispatch as the identifier instead of sequential PSxxx ID.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Invalid file format. Please upload a CSV file.")

    try:
        purchasesub_col = get_purchasesubcategory_collection()
        store_dispatch_col = get_dispatch_collection()
        rawmaterial_col = get_purchaseitem_collection()

        content = await file.read()
        decoded = content.decode('utf-8-sig', errors='replace')
        csv_reader = csv.DictReader(io.StringIO(decoded))

        # --- Collect rows with valid Qty ---
        rows_to_process = []
        for row in csv_reader:
            name = row.get("ItemName") or row.get("itemname") or row.get("VarianceName") or row.get("varianceName")
            qty = row.get("Qty") or row.get("qty")
            if name and qty and str(qty).strip() != "":
                rows_to_process.append((name.strip(), row))

        if not rows_to_process:
            return "Import Failed: No valid items with Qty found in CSV"

        # --- Fetch all valid items ---
        rm_docs = await rawmaterial_col.find({}, {"itemName": 1, "uom": 1, "purchasePrice": 1, "itemCode": 1}).to_list(length=None)
        valid_items = {doc["itemName"].strip(): doc for doc in rm_docs if "itemName" in doc}

        missing_items = [row[0] for row in rows_to_process if row[0] not in valid_items]
        if missing_items:
            return f"Import Failed: Items not found - {missing_items}"

        # --- Validate Qty ---
        variance_names, qty_list, weight_list, uom_list, price_list, itemcode_list, amount_list = ([] for _ in range(7))
        invalid_qty_items = []
        filtered_rows = []

        for name, row in rows_to_process:
            qty_val = row.get("Qty") or row.get("qty")
            try:
                qty_val = float(qty_val)
                if qty_val <= 0:
                    invalid_qty_items.append(name)
                else:
                    filtered_rows.append((name, qty_val))
            except ValueError:
                invalid_qty_items.append(name)

        if invalid_qty_items:
            return f"Import Failed: Invalid Qty for items: {invalid_qty_items}. Only positive numbers allowed."

        # --- Process valid rows ---
        for name, qty_val in filtered_rows:
            doc = valid_items[name]
            variance_names.append(doc["itemName"])
            uom = doc.get("uom", "")
            uom_list.append(uom)
            price = int(float(doc.get("purchasePrice", 0)))
            price_list.append(price)
            itemcode_list.append(doc.get("itemCode", ""))

            if str(uom).lower() in ["kg", "kgs"]:
                weight_list.append(qty_val)
                qty_list.append(0)
            else:
                qty_list.append(int(qty_val))
                weight_list.append(0)

            amount_list.append(int(qty_val * price))

        if not variance_names:
            return "Import Failed: No valid items to import after filtering"

        # --- Get the latest dispatchNumber from storeDispatch ---
        latest_dispatch = await store_dispatch_col.find({}, {"dispatchNumber": 1}).sort("dispatchNumber", -1).to_list(length=1)
        if latest_dispatch:
            dispatch_number = latest_dispatch[0].get("dispatchNumber", 0)
        else:
            dispatch_number = 1  # default if none exist

        sentDate_str = None
        if sentDate:
            try:
                parsed_sent_date = datetime.fromisoformat(sentDate)
                sentDate_str = parsed_sent_date.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                sentDate_str = str(sentDate)

        # --- Insert document using dispatchNumber as ID ---
        document = {
            "randomId": dispatch_number,  # <-- using dispatchNumber from storeDispatch
            "location": location,
            "itemName": variance_names,
            "price": price_list,
            "uom": uom_list,
            "varianceName": variance_names,
            "qty": qty_list,
            "weight": weight_list,
            "amount": amount_list,
            "itemCode": itemcode_list,
            "sentDate": sentDate_str,
            "date": get_iso_datetime(),
            "status": "active",
            "dispatchNumber": dispatch_number  # store it as well
        }

        await purchasesub_col.insert_one(document)

        return f"Imported Successfully: {len(variance_names)} items with dispatchNumber {dispatch_number}"

    except Exception as e:
        logging.error(f"Import error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
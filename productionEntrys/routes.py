from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from bson import ObjectId
from .models import ProductionEntry, ProductionEntryPost, get_iso_datetime
from .utils import get_productionEntry_collection
from datetime import datetime
from dateutil import parser as date_parser
from pymongo import DESCENDING
import pytz

router = APIRouter()


@router.post("/", response_model=ProductionEntry)
# async def create_production_entry(production_entry: ProductionEntryPost):
#     coll = get_productionEntry_collection()

#     # Find the last document with a productionEntryNumber
#     last_doc = await coll.find_one(
#         {"productionEntryNumber": {"$exists": True}},
#         sort=[("productionEntryNumber", DESCENDING)]
#     )

#     # Extract the numeric part from "PE000X"
#     if last_doc and last_doc.get("productionEntryNumber"):
#         try:
#             last_number_str = last_doc["productionEntryNumber"].replace("PE", "")
#             last_number = int(last_number_str)
#         except (ValueError, TypeError):
#             last_number = 0
#     else:
#         last_number = 0

#     # Increment and format as PE0001, PE0002, etc.
#     next_number = last_number + 1
#     production_entry_number = f"PE{next_number:04d}"

#     # Prepare new document
#     new_production = production_entry.dict(exclude_unset=True)
#     new_production["productionEntryNumber"] = production_entry_number
    
#     # Parse date if provided as string, else use current time
#     date_val = new_production.get("date")
#     if isinstance(date_val, str):
#         try:
#             new_production["date"] = date_parser.parse(date_val)
#         except ValueError:
#             new_production["date"] = datetime.now(pytz.timezone("Asia/Kolkata"))
#     else:
#         new_production["date"] = datetime.now(pytz.timezone("Asia/Kolkata"))

#     # Insert into MongoDB
#     result = await coll.insert_one(new_production)
    
#     # Prepare response
#     new_production["productionEntryId"] = str(result.inserted_id)
#     return ProductionEntry(**new_production)



async def create_production_entry(production_entry: ProductionEntryPost):
    coll = get_productionEntry_collection()

    # Find the last document with a productionEntryNumber
    last_doc = await coll.find_one(
        {"productionEntryNumber": {"$regex": "^PE\\d+$"}},  # Only match "PE" followed by digits
        sort=[("productionEntryNumber", DESCENDING)]
    )

    # Extract the numeric part from "PE000X"
    if last_doc and last_doc.get("productionEntryNumber"):
        try:
            last_number_str = last_doc["productionEntryNumber"].replace("PE", "")
            last_number = int(last_number_str)
        except (ValueError, TypeError) as e:
            # Log the error for debugging (optional)
            print(f"Error parsing productionEntryNumber {last_doc['productionEntryNumber']}: {e}")
            last_number = 0
    else:
        last_number = 0

    # Increment and format as PE0001, PE0002, etc.
    next_number = last_number + 1
    production_entry_number = f"PE{next_number:04d}"

    # Prepare new document
    new_production = production_entry.dict(exclude_unset=True)
    new_production["productionEntryNumber"] = production_entry_number
    
    # Parse date if provided as string, else use current time
    date_val = new_production.get("date")
    if isinstance(date_val, str):
        try:
            new_production["date"] = date_parser.parse(date_val)
        except ValueError:
            new_production["date"] = datetime.now(pytz.timezone("Asia/Kolkata"))
    else:
        new_production["date"] = datetime.now(pytz.timezone("Asia/Kolkata"))

    # Insert into MongoDB with retry to handle concurrency
    try:
        result = await coll.insert_one(new_production)
    except Exception as e:
        # Check if the number already exists (possible in concurrent scenarios)
        if "duplicate key" in str(e).lower():
            raise HTTPException(status_code=409, detail=f"ProductionEntryNumber {production_entry_number} already exists")
        raise HTTPException(status_code=500, detail="Failed to insert production entry")

    # Prepare response
    new_production["productionEntryId"] = str(result.inserted_id)
    try:
        return ProductionEntry(**new_production)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create ProductionEntry response: {str(e)}")
    
@router.get("/", response_model=List[ProductionEntry])
async def get_all_production_entries(date: Optional[str] = Query(None)):
    coll = get_productionEntry_collection()
    query = {}

    if date:
        try:
            date_obj = datetime.strptime(date, "%d-%m-%Y")
            start_date = date_obj.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = date_obj.replace(hour=23, minute=59, second=59, microsecond=999999)
            query["date"] = {"$gte": start_date, "$lte": end_date}  # Use datetime objects
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use DD-MM-YYYY.")

    cursor = coll.find(query)
    production_entries = await cursor.to_list(length=None)

    formatted = []
    for entry in production_entries:
        entry["productionEntryId"] = str(entry.pop("_id", None))
        
        # Ensure date is a datetime object
        date_val = entry.get("date")
        if isinstance(date_val, str):
            try:
                entry["date"] = date_parser.parse(date_val)
            except Exception:
                entry["date"] = None
        elif not isinstance(date_val, datetime):
            entry["date"] = None

        formatted.append(ProductionEntry(**entry))

    return formatted

# Other endpoints (unchanged)
@router.get("/{production_entry_id}", response_model=ProductionEntry)
async def get_production_entry_by_id(production_entry_id: str):
    entry = await get_productionEntry_collection().find_one({"_id": ObjectId(production_entry_id)})
    if not entry:
        raise HTTPException(status_code=404, detail="ProductionEntry not found")
    entry["productionEntryId"] = str(entry["_id"])
    entry.pop("_id", None)
    # Ensure date is a datetime object
    if isinstance(entry.get("date"), str):
        try:
            entry["date"] = date_parser.parse(entry["date"])
        except Exception:
            entry["date"] = None
    return ProductionEntry(**entry)

#-------------- Put------------------

@router.put("/{production_entry_id}")
async def update_production_entry(production_entry_id: str, production_entry: ProductionEntryPost):
    updated = production_entry.dict(exclude_unset=True)
    # Parse date if provided
    if "date" in updated and isinstance(updated["date"], str):
        try:
            updated["date"] = date_parser.parse(updated["date"])
        except ValueError:
            updated["date"] = datetime.now(pytz.timezone("Asia/Kolkata"))
    result = await get_productionEntry_collection().update_one(
        {"_id": ObjectId(production_entry_id)}, {"$set": updated}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="ProductionEntry not found")
    return {"message": "ProductionEntry updated successfully"}


#-------------- Patch------------------
@router.patch("/{production_entry_id}")
async def patch_production_entry(production_entry_id: str, production_entry_patch: ProductionEntryPost):
    coll = get_productionEntry_collection()
    existing = await coll.find_one({"_id": ObjectId(production_entry_id)})
    if not existing:
        raise HTTPException(status_code=404, detail="ProductionEntry not found")

    updated_fields = {
        k: v for k, v in production_entry_patch.dict(exclude_unset=True).items() if v is not None
    }
    if updated_fields:
        result = await coll.update_one({"_id": ObjectId(production_entry_id)}, {"$set": updated_fields})
        if result.modified_count == 0:
            raise HTTPException(status_code=500, detail="Failed to update ProductionEntry")

    updated_entry = await coll.find_one({"_id": ObjectId(production_entry_id)})
    updated_entry["_id"] = str(updated_entry["_id"])
    return updated_entry

#-------------- Delete------------------

@router.delete("/{production_entry_id}")
async def delete_production_entry(production_entry_id: str):
    result = await get_productionEntry_collection().delete_one({"_id": ObjectId(production_entry_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="ProductionEntry not found")
    return {"message": "ProductionEntry deleted successfully"}
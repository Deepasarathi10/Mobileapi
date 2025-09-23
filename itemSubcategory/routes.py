from datetime import datetime, timedelta
import logging
import re
from typing import List, Optional
from fastapi import APIRouter, HTTPException, File, UploadFile
from bson import ObjectId
from fastapi.responses import StreamingResponse
import pytz
import csv
import io
from pydantic import BaseModel
from pymongo import InsertOne, UpdateOne
from typing import Optional

from .models import itemSubcategory, itemSubcategoryPost
from .utils import get_itemsubcategory_collection, convert_to_string_or_none

router = APIRouter()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Header mapping for user-friendly CSV columns
header_mapping = {
    'Item Subcategory ID': 'randomId',
    'Item Subcategory': 'subCategoryName',
    'Status': 'status',
    'Created Date': 'createdDate',
    'Updated Date': 'lastUpdatedDate'
}

def get_localized_datetime():
    """Get current UTC datetime adjusted from IST."""
    ist = pytz.timezone("Asia/Kolkata")
    return datetime.now(ist).astimezone(pytz.UTC)

def set_counter_value(value: int, counter_id: str = "subCategoryId"):
    """Set the counter value in the database."""
    counter_collection = get_itemsubcategory_collection().database["counters"]
    counter_collection.update_one(
        {"_id": counter_id},
        {"$set": {"sequence_value": value}},
        upsert=True
    )

def get_current_counter_value(counter_id: str = "subCategoryId"):
    """Get the current counter value from the database."""
    counter_collection = get_itemsubcategory_collection().database["counters"]
    counter = counter_collection.find_one({"_id": counter_id})
    return counter["sequence_value"] if counter else 0

def initialize_counter_if_needed(counter_id: str = "subCategoryId"):
    """Initialize counter to the highest existing ID number (ISxxx)."""
    collection = get_itemsubcategory_collection()
    counter_collection = collection.database["counters"]

    highest_item = collection.find_one(
        {"randomId": {"$regex": "^IS\\d+$"}},
        sort=[("randomId", -1)]
    )

    if highest_item:
        try:
            last_number = int(highest_item["randomId"][2:])
        except (ValueError, TypeError):
            last_number = 0
            logger.warning(f"Malformed randomId found: {highest_item['randomId']}")
        counter_collection.update_one(
            {"_id": counter_id},
            {"$set": {"sequence_value": last_number}},
            upsert=True
        )
    else:
        counter_collection.update_one(
            {"_id": counter_id},
            {"$set": {"sequence_value": 0}},
            upsert=True
        )

def generate_sequential_id(used_ids: set = None):
    """Generate an ISxxx ID, filling gaps in the sequence, considering used_ids."""
    collection = get_itemsubcategory_collection()
    counter_collection = collection.database["counters"]

    initialize_counter_if_needed()
    counter = counter_collection.find_one({"_id": "subCategoryId"})
    current_counter = counter["sequence_value"] if counter else 0

    # Find all existing ISxxx IDs in the database
    existing_ids = collection.find({"randomId": {"$regex": "^IS\\d+$"}}, {"randomId": 1})
    id_numbers = set()
    for item in existing_ids:
        try:
            if item["randomId"].startswith("IS"):
                num = int(item["randomId"][2:])
                id_numbers.add(num)
        except (ValueError, TypeError):
            continue

    # Include used_ids from CSV if provided
    if used_ids:
        for rid in used_ids:
            try:
                if rid.startswith("IS") and rid[2:].isdigit():
                    num = int(rid[2:])
                    id_numbers.add(num)
            except (ValueError, TypeError):
                continue

    # Find the first available gap or next number
    next_number = 1
    if id_numbers:
        sorted_ids = sorted(id_numbers)
        for i in range(len(sorted_ids)):
            if sorted_ids[i] > i + 1:
                next_number = i + 1
                break
        else:
            next_number = sorted_ids[-1] + 1

    # Ensure we don't go below current counter
    next_number = max(next_number, current_counter + 1)

    # Update the counter atomically
    counter_collection.update_one(
        {"_id": "subCategoryId"},
        {"$set": {"sequence_value": next_number}},
        upsert=True
    )

    return f"IS{next_number:03d}"

@router.post("/reset-counter")
async def reset_sequence():
    """Reset the counter to 0. Next ID will be IS001."""
    set_counter_value(0)
    return {"message": "Counter reset successfully. Next ID will be IS001"}

@router.get("/export-csv")
async def export_all_itemsubcategories_to_csv():
    """Export active item subcategories to a CSV file."""
    try:
        logger.info("Received request for /itemsubcategories/export-csv")
        collection = get_itemsubcategory_collection()
        records = list(collection.find({"status": "active"}, {'_id': 0}))
        
        if not records:
            logger.warning("No active item subcategories found for export")
            raise HTTPException(status_code=404, detail="No active item subcategories found to export")

        csv_stream = io.StringIO()
        fieldnames = list(header_mapping.keys())
        writer = csv.DictWriter(csv_stream, fieldnames=fieldnames)
        writer.writeheader()

        ist = pytz.timezone('Asia/Kolkata')

        for record in records:
            created_date = record.get('createdDate')
            created_str = ""
            if created_date and isinstance(created_date, datetime):
                if created_date.tzinfo is None:
                    created_date = pytz.UTC.localize(created_date)
                created_date_ist = created_date.astimezone(ist)
                created_str = created_date_ist.strftime('%d-%m-%Y')

            last_updated_date = record.get('lastUpdatedDate')
            updated_str = ""
            if last_updated_date and isinstance(last_updated_date, datetime):
                if last_updated_date.tzinfo is None:
                    last_updated_date = pytz.UTC.localize(last_updated_date)
                last_updated_date_ist = last_updated_date.astimezone(ist)
                updated_str = last_updated_date_ist.strftime('%d-%m-%Y')

            writer.writerow({
                'Item Subcategory ID': record.get('randomId', ''),
                'Item Subcategory': record.get('subCategoryName', ''),
                'Status': record.get('status', ''),
                'Created Date': created_str,
                'Updated Date': updated_str
            })

        csv_stream.seek(0)
        filename = f"item_subcategories_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        logger.info(f"Successfully generated CSV file: {filename}")
        return StreamingResponse(
            csv_stream,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except HTTPException as he:
        logger.error(f"HTTPException in export-csv: {he.detail}", exc_info=True)
        raise he
    except Exception as e:
        logger.error(f"Unexpected error in export-csv: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error exporting item subcategories: {str(e)}")

@router.post("/import-csv")
async def import_csv_data(file: UploadFile = File(...)):
    """Import item subcategories from a CSV file, preserving valid randomIds and handling duplicates."""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Invalid file format. Please upload a CSV file.")

    try:
        collection = get_itemsubcategory_collection()
        current_datetime = get_localized_datetime()

        content = await file.read()
        decoded = content.decode('utf-8-sig', errors='replace')
        csv_reader = csv.DictReader(io.StringIO(decoded))

        headers = [header_mapping.get(header.strip(), header.strip()) for header in csv_reader.fieldnames or []]
        csv_reader.fieldnames = headers

        required_fields = ['subCategoryName']
        missing_headers = [header for header in required_fields if header not in headers]
        if missing_headers:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Missing required headers in CSV file",
                    "missing": [header_mapping.get(field, field) for field in missing_headers],
                    "required": [header_mapping.get(field, field) for field in required_fields]
                }
            )

        rows = []
        seen_names = {}
        seen_ids = {}
        for idx, row in enumerate(csv_reader, 1):
            cleaned_row = {k: str(v).strip() if v is not None else "" for k, v in row.items()}
            rows.append((idx, cleaned_row))

            name = cleaned_row.get('subCategoryName', '').lower()
            if name:
                if name in seen_names:
                    seen_names[name].append(idx)
                else:
                    seen_names[name] = [idx]

            random_id = cleaned_row.get('randomId', '').strip()
            if random_id:
                if random_id in seen_ids:
                    seen_ids[random_id].append(idx)
                else:
                    seen_ids[random_id] = [idx]

        # Get existing subcategories by randomId and subCategoryName
        existing_subcategories_by_name = {g['subCategoryName'].lower(): g for g in collection.find({}, {'subCategoryName': 1, '_id': 1, 'randomId': 1, 'status': 1})}
        existing_subcategories_by_id = {g['randomId']: g for g in collection.find({"randomId": {"$regex": "^IS\\d+$"}}, {'subCategoryName': 1, '_id': 1, 'randomId': 1, 'status': 1})}
        used_ids = set(collection.distinct("randomId", {"randomId": {"$regex": "^IS\\d+$"}}))

        initialize_counter_if_needed()
        max_id_number = get_current_counter_value()

        inserted_count = 0
        updated_count = 0
        successful = []
        updated = []
        failed = []
        batch = []

        for idx, row in rows:
            try:
                # Validate required fields
                missing_fields = [field for field in required_fields if not row.get(field)]
                if missing_fields:
                    failed.append({
                        "row": idx,
                        "data": row,
                        "error": "Missing required fields",
                        "missingFields": [header_mapping.get(field, field) for field in missing_fields]
                    })
                    continue

                subcategory_name = row.get('subCategoryName')
                # Check for duplicate subCategoryName in CSV
                if subcategory_name.lower() in seen_names and len(seen_names[subcategory_name.lower()]) > 1:
                    failed.append({
                        "row": idx,
                        "data": row,
                        "error": f"Duplicate Item Subcategory in CSV: '{subcategory_name}'",
                        "missingFields": []
                    })
                    continue

                # Validate status
                status = row.get('status', 'active').lower()
                if status not in ['active', 'inactive']:
                    status = 'active'

                # Parse dates
                created_date = current_datetime
                if row.get('createdDate'):
                    try:
                        created_date_ist = datetime.strptime(row['createdDate'], '%d-%m-%Y')
                        created_date_ist = pytz.timezone('Asia/Kolkata').localize(created_date_ist)
                        created_date = created_date_ist.astimezone(pytz.UTC)
                    except ValueError:
                        failed.append({
                            "row": idx,
                            "data": row,
                            "error": "Invalid Created Date format: must be DD-MM-YYYY",
                            "missingFields": []
                        })
                        continue

                last_updated_date = current_datetime
                if row.get('lastUpdatedDate'):
                    try:
                        last_updated_date_ist = datetime.strptime(row['lastUpdatedDate'], '%d-%m-%Y')
                        last_updated_date_ist = pytz.timezone('Asia/Kolkata').localize(last_updated_date_ist)
                        last_updated_date = last_updated_date_ist.astimezone(pytz.UTC)
                    except ValueError:
                        failed.append({
                            "row": idx,
                            "data": row,
                            "error": "Invalid Updated Date format: must be DD-MM-YYYY",
                            "missingFields": []
                        })
                        continue

                provided_id = row.get('randomId', '').strip()
                assigned_id = None

                # Handle randomId
                if provided_id:
                    if not (provided_id.startswith('IS') and provided_id[2:].isdigit()):
                        failed.append({
                            "row": idx,
                            "data": row,
                            "error": f"Invalid randomId format: '{provided_id}'. Must be 'IS' followed by digits.",
                            "missingFields": []
                        })
                        continue
                    # Check for duplicate randomId in CSV
                    if provided_id in seen_ids and seen_ids[provided_id][0] != idx:
                        failed.append({
                            "row": idx,
                            "data": row,
                            "error": f"Duplicate randomId in CSV: '{provided_id}'. First used in row {seen_ids[provided_id][0]}.",
                            "missingFields": []
                        })
                        continue
                    # Check if randomId exists in the database
                    if provided_id in existing_subcategories_by_id:
                        existing_subcategory = existing_subcategories_by_id[provided_id]
                        # Update existing record
                        update_data = {
                            'subCategoryName': subcategory_name,
                            'status': status,
                            'lastUpdatedDate': last_updated_date
                        }
                        if row.get('createdDate'):
                            update_data['createdDate'] = created_date
                        batch.append(UpdateOne(
                            {'_id': existing_subcategory['_id']},
                            {'$set': update_data}
                        ))
                        updated.append({
                            "row": idx,
                            "data": row,
                            "message": f"Item Subcategory updated for randomId: '{provided_id}'"
                        })
                        updated_count += 1
                        max_id_number = max(max_id_number, int(provided_id[2:]))
                        # Update existing_subcategories_by_name to prevent duplicate name errors
                        if existing_subcategory['subCategoryName'].lower() != subcategory_name.lower():
                            del existing_subcategories_by_name[existing_subcategory['subCategoryName'].lower()]
                            existing_subcategories_by_name[subcategory_name.lower()] = existing_subcategory
                        continue
                    # Valid, unused randomId from CSV
                    assigned_id = provided_id
                    used_ids.add(assigned_id)
                    max_id_number = max(max_id_number, int(assigned_id[2:]))
                else:
                    # Generate sequential ID for rows without a valid randomId
                    assigned_id = generate_sequential_id(used_ids)
                    used_ids.add(assigned_id)
                    max_id_number = max(max_id_number, int(assigned_id[2:]))

                # Check for duplicate subCategoryName in the database
                if subcategory_name.lower() in existing_subcategories_by_name:
                    existing_subcategory = existing_subcategories_by_name[subcategory_name.lower()]
                    if existing_subcategory['randomId'] != assigned_id:
                        failed.append({
                            "row": idx,
                            "data": row,
                            "error": f"Item Subcategory '{subcategory_name}' already exists with randomId: '{existing_subcategory['randomId']}'",
                            "missingFields": []
                        })
                        continue

                # Create new record
                subcategory_data = {
                    'subCategoryName': subcategory_name,
                    'randomId': assigned_id,
                    'status': status,
                    'createdDate': created_date,
                    'lastUpdatedDate': last_updated_date
                }

                batch.append(InsertOne(subcategory_data))
                successful.append({
                    "row": idx,
                    "data": row,
                    "assignedId": assigned_id
                })
                existing_subcategories_by_name[subcategory_name.lower()] = subcategory_data
                existing_subcategories_by_id[assigned_id] = subcategory_data
                inserted_count += 1

                if len(batch) >= 500:
                    collection.bulk_write(batch, ordered=False)
                    batch = []

            except Exception as e:
                failed.append({
                    "row": idx,
                    "data": row,
                    "error": f"Unexpected error: {str(e)}",
                    "missingFields": []
                })
                logger.error(f"Row {idx} error: {str(e)}")

        if batch:
            collection.bulk_write(batch, ordered=False)

        set_counter_value(max_id_number)

        response = {
            "message": "CSV import processed successfully" if not failed else "CSV import completed with errors",
            "inserted_count": inserted_count,
            "updated_count": updated_count,
            "successful": successful,
            "updated": updated,
            "failed": failed,
            "errorCount": len(failed),
            "max_id_number": max_id_number
        }
        logger.info(f"Import response: {response}")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Import error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@router.post("/", response_model=str)
async def create_itemsubcategory(itemsubcategory: itemSubcategoryPost):
    """Create a new item subcategory with a sequential ID."""
    current_datetime = get_localized_datetime()

    initialize_counter_if_needed()
    sequential_id = generate_sequential_id()

    new_itemsubcategory_data = itemsubcategory.dict()
    new_itemsubcategory_data.update({
        'randomId': sequential_id,
        'status': 'active',
        'createdDate': current_datetime,
        'lastUpdatedDate': current_datetime
    })

    result = get_itemsubcategory_collection().insert_one(new_itemsubcategory_data)
    return str(result.inserted_id)

@router.get("/", response_model=List[itemSubcategory])
async def get_all_itemsubcategory():
    """Get all item subcategories."""
    itemsubcategories = list(get_itemsubcategory_collection().find())
    formatted_itemsubcategory = []
    for itemsubcategory in itemsubcategories:
        for key, value in itemsubcategory.items():
            itemsubcategory[key] = convert_to_string_or_none(value)
        itemsubcategory["subCategoryId"] = str(itemsubcategory["_id"])
        formatted_itemsubcategory.append(itemSubcategory(**itemsubcategory))
    return formatted_itemsubcategory

@router.get("/{itemsubcategory_id}", response_model=itemSubcategory)
async def get_itemsubcategory_by_id(itemsubcategory_id: str):
    """Get a specific item subcategory by ID."""
    try:
        logger.info(f"Received request for /itemsubcategories/{itemsubcategory_id}")
        itemsubcategory = get_itemsubcategory_collection().find_one({"_id": ObjectId(itemsubcategory_id)})
        if itemsubcategory:
            for key, value in itemsubcategory.items():
                itemsubcategory[key] = convert_to_string_or_none(value)
            itemsubcategory["subCategoryId"] = str(itemsubcategory["_id"])
            return itemSubcategory(**itemsubcategory)
        raise HTTPException(status_code=404, detail=f"Item subcategory not found: {itemsubcategory_id}")
    except Exception as e:
        logger.error(f"Invalid itemsubcategoryId format: {itemsubcategory_id}, error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Invalid itemsubcategoryId format: {itemsubcategory_id}, must be a 24-character hexadecimal string")

@router.put("/{itemsubcategory_id}")
async def update_itemsubcategory(itemsubcategory_id: str, itemsubcategory: itemSubcategoryPost):
    """Replace an existing item subcategory."""
    try:
        current_datetime = get_localized_datetime()
        updated_itemsubcategory = itemsubcategory.dict(exclude_unset=True)
        updated_itemsubcategory.update({
            'lastUpdatedDate': current_datetime
        })

        result = get_itemsubcategory_collection().update_one(
            {"_id": ObjectId(itemsubcategory_id)},
            {"$set": updated_itemsubcategory}
        )
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail=f"Item subcategory not found: {itemsubcategory_id}")
        return {"message": "Item subcategory updated successfully"}
    except Exception as e:
        logger.error(f"Invalid itemsubcategoryId format: {itemsubcategory_id}, error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Invalid itemsubcategoryId format: {itemsubcategory_id}, must be a 24-character hexadecimal string")

@router.patch("/{itemsubcategory_id}", response_model=itemSubcategory)
async def patch_itemsubcategory(itemsubcategory_id: str, itemsubcategory_patch: itemSubcategoryPost):
    """Update specific fields of an existing item subcategory."""
    try:
        current_datetime = get_localized_datetime()
        collection = get_itemsubcategory_collection()

        # Validate ObjectId
        try:
            oid = ObjectId(itemsubcategory_id)
        except Exception:
            logger.error(f"Invalid itemsubcategoryId format: {itemsubcategory_id}")
            raise HTTPException(status_code=400, detail="Invalid itemsubcategoryId format: must be a 24-character hexadecimal string")

        # Check if item subcategory exists
        existing_itemsubcategory = collection.find_one({"_id": oid})
        if not existing_itemsubcategory:
            logger.info(f"Item subcategory not found: {itemsubcategory_id}")
            raise HTTPException(status_code=404, detail="Item subcategory not found")

        # Prepare update fields
        updated_fields = {
            key: value
            for key, value in itemsubcategory_patch.dict(exclude_unset=True).items()
            if value is not None
        }
        if not updated_fields:
            logger.info(f"No fields to update for item subcategory: {itemsubcategory_id}")
            formatted_itemsubcategory = {**existing_itemsubcategory}
            for key, value in formatted_itemsubcategory.items():
                formatted_itemsubcategory[key] = convert_to_string_or_none(value)
            formatted_itemsubcategory["subCategoryId"] = str(formatted_itemsubcategory["_id"])
            return itemSubcategory(**formatted_itemsubcategory)

        updated_fields.update({"lastUpdatedDate": current_datetime})

        # Perform update
        result = collection.update_one({"_id": oid}, {"$set": updated_fields})
        if result.modified_count == 0:
            logger.warning(f"No changes applied to item subcategory: {itemsubcategory_id}")
            formatted_itemsubcategory = {**existing_itemsubcategory}
            for key, value in formatted_itemsubcategory.items():
                formatted_itemsubcategory[key] = convert_to_string_or_none(value)
            formatted_itemsubcategory["subCategoryId"] = str(formatted_itemsubcategory["_id"])
            return itemSubcategory(**formatted_itemsubcategory)

        # Fetch updated document
        updated_itemsubcategory = collection.find_one({"_id": oid})
        if not updated_itemsubcategory:
            logger.error(f"Failed to retrieve updated item subcategory: {itemsubcategory_id}")
            raise HTTPException(status_code=500, detail="Failed to retrieve updated item subcategory")

        # Convert ObjectId to string and return as itemSubcategory model
        for key, value in updated_itemsubcategory.items():
            updated_itemsubcategory[key] = convert_to_string_or_none(value)
        updated_itemsubcategory["subCategoryId"] = str(updated_itemsubcategory["_id"])
        logger.info(f"Item subcategory updated successfully: {itemsubcategory_id}")
        return itemSubcategory(**updated_itemsubcategory)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating item subcategory {itemsubcategory_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@router.delete("/{itemsubcategory_id}")
async def delete_itemsubcategory(itemsubcategory_id: str):
    """Delete an item subcategory."""
    try:
        result = get_itemsubcategory_collection().delete_one({"_id": ObjectId(itemsubcategory_id)})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Item subcategory not found")
        return {"message": "Item subcategory deleted successfully"}
    except Exception as e:
        logger.error(f"Invalid itemsubcategoryId format: {itemsubcategory_id}, error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Invalid itemsubcategoryId format: {itemsubcategory_id}, must be a 24-character hexadecimal string")
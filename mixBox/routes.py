from datetime import datetime, timedelta
import logging
import json
from typing import List, Optional
from fastapi import APIRouter, HTTPException, File, UploadFile
from bson import ObjectId
from fastapi.responses import StreamingResponse
import pytz
import csv
import io
from pydantic import BaseModel
from pymongo import InsertOne, UpdateOne

from mixBox.models import MixBox, MixBoxPost
from mixBox.utils import get_mixbox_collection

router = APIRouter()
collection = get_mixbox_collection()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Header mapping for user-friendly CSV columns
header_mapping = {
    'MixBox ID': 'randomId',
    'MixBox Name': 'mixboxName',
    'Total Grams': 'totalGrams',
    'Items': 'items',
    'Status': 'status',
    'Created Date': 'createdDate',
    'Updated Date': 'lastUpdatedDate'
}

def get_localized_datetime():
    """Get current UTC datetime adjusted from IST."""
    ist = pytz.timezone("Asia/Kolkata")
    return datetime.now(ist).astimezone(pytz.UTC)

# Helper function to convert ObjectId and other types to string or None
def convert_to_string_or_none(value):
    if isinstance(value, ObjectId):
        return str(value)
    elif value is None:
        return None
    elif isinstance(value, dict):
        return {k: convert_to_string_or_none(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [convert_to_string_or_none(v) for v in value]
    return value

# Original counter functions (keeping existing functionality)
def get_next_counter_value():
    counter_collection = get_mixbox_collection().database["counters"]
    counter = counter_collection.find_one_and_update(
        {"_id": "mixboxId"},
        {"$inc": {"sequence_value": 1}},
        upsert=True,
        return_document=True
    )
    return counter["sequence_value"]

def reset_counter():
    counter_collection = get_mixbox_collection().database["counters"]
    counter_collection.update_one(
        {"_id": "mixboxId"},
        {"$set": {"sequence_value": 0}},
        upsert=True
    )

def generate_random_id():
    counter_value = get_next_counter_value()
    return f"M{counter_value:03d}"

# New CSV-specific counter functions
def set_counter_value(value: int, counter_id: str = "mixboxId"):
    """Set the counter value in the database."""
    counter_collection = get_mixbox_collection().database["counters"]
    counter_collection.update_one(
        {"_id": counter_id},
        {"$set": {"sequence_value": value}},
        upsert=True
    )

def get_current_counter_value(counter_id: str = "mixboxId"):
    """Get the current counter value from the database."""
    counter_collection = get_mixbox_collection().database["counters"]
    counter = counter_collection.find_one({"_id": counter_id})
    return counter["sequence_value"] if counter else 0

def initialize_counter_if_needed(counter_id: str = "mixboxId"):
    """Initialize counter to the highest existing ID number (Mxxx)."""
    collection = get_mixbox_collection()
    counter_collection = collection.database["counters"]

    highest_item = collection.find_one(
        {"randomId": {"$regex": "^M\\d+$"}},
        sort=[("randomId", -1)]
    )

    if highest_item:
        try:
            last_number = int(highest_item["randomId"][1:])
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
    """Generate a Mxxx ID, filling gaps in the sequence, considering used_ids."""
    collection = get_mixbox_collection()
    counter_collection = collection.database["counters"]

    initialize_counter_if_needed()
    counter = counter_collection.find_one({"_id": "mixboxId"})
    current_counter = counter["sequence_value"] if counter else 0

    # Find all existing Mxxx IDs in the database
    existing_ids = collection.find({"randomId": {"$regex": "^M\\d+$"}}, {"randomId": 1})
    id_numbers = set()
    for item in existing_ids:
        try:
            if item["randomId"].startswith("M"):
                num = int(item["randomId"][1:])
                id_numbers.add(num)
        except (ValueError, TypeError):
            continue

    # Include used_ids from CSV if provided
    if used_ids:
        for rid in used_ids:
            try:
                if rid.startswith("M") and rid[1:].isdigit():
                    num = int(rid[1:])
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
        {"_id": "mixboxId"},
        {"$set": {"sequence_value": next_number}},
        upsert=True
    )

    return f"M{next_number:03d}"

def format_items_for_csv(items):
    """Format items list for CSV export."""
    if not items:
        return ""
    
    formatted_items = []
    for item in items:
        item_str = f"{item.get('item_name', '')};{item.get('uom', '')};{item.get('grams', 0)}"
        formatted_items.append(item_str)
    return "|".join(formatted_items)

def parse_items_from_csv(items_str):
    """Parse items from CSV string format."""
    if not items_str or items_str.strip() == "":
        return []
    
    items = []
    try:
        item_parts = items_str.split("|")
        for part in item_parts:
            if part.strip():
                components = part.split(";")
                if len(components) >= 3:
                    item = {
                        "item_name": components[0].strip() if components[0].strip() else None,
                        "uom": components[1].strip() if components[1].strip() else None,
                        "grams": float(components[2].strip()) if components[2].strip() else 0.0
                    }
                    items.append(item)
    except Exception as e:
        logger.error(f"Error parsing items: {e}")
        return []
    
    return items

# CSV-specific routes
@router.post("/reset-counter")
async def reset_sequence():
    """Reset the counter to 0. Next ID will be M001."""
    set_counter_value(0)
    return {"message": "Counter reset successfully. Next ID will be M001"}

@router.get("/export-csv")
async def export_all_mixboxes_to_csv():
    """Export active mixboxes to a CSV file."""
    try:
        logger.info("Received request for /mixboxes/export-csv")
        collection = get_mixbox_collection()
        records = list(collection.find({"status": "active"}, {'_id': 0}))
        
        if not records:
            logger.warning("No active mixboxes found for export")
            raise HTTPException(status_code=404, detail="No active mixboxes found to export")

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
                'MixBox ID': record.get('randomId', ''),
                'MixBox Name': record.get('mixboxName', ''),
                'Total Grams': record.get('totalGrams', ''),
                'Items': format_items_for_csv(record.get('items', [])),
                'Status': record.get('status', ''),
                'Created Date': created_str,
                'Updated Date': updated_str
            })

        csv_stream.seek(0)
        filename = f"mixboxes_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
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
        raise HTTPException(status_code=500, detail=f"Error exporting mixboxes: {str(e)}")

@router.post("/import-csv")
async def import_csv_data(file: UploadFile = File(...)):
    """Import mixboxes from a CSV file, preserving valid randomIds and handling duplicates."""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Invalid file format. Please upload a CSV file.")

    try:
        collection = get_mixbox_collection()
        current_datetime = get_localized_datetime()

        content = await file.read()
        decoded = content.decode('utf-8-sig', errors='replace')
        csv_reader = csv.DictReader(io.StringIO(decoded))

        headers = [header_mapping.get(header.strip(), header.strip()) for header in csv_reader.fieldnames or []]
        csv_reader.fieldnames = headers

        required_fields = ['mixboxName', 'totalGrams']
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

            name = cleaned_row.get('mixboxName', '').lower()
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

        # Get existing mixboxes by randomId and mixboxName
        existing_mixboxes_by_name = {m['mixboxName'].lower(): m for m in collection.find({}, {'mixboxName': 1, '_id': 1, 'randomId': 1, 'status': 1})}
        existing_mixboxes_by_id = {m['randomId']: m for m in collection.find({"randomId": {"$regex": "^M\\d+$"}}, {'mixboxName': 1, '_id': 1, 'randomId': 1, 'status': 1})}
        used_ids = set(collection.distinct("randomId", {"randomId": {"$regex": "^M\\d+$"}}))

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

                mixbox_name = row.get('mixboxName')
                total_grams = row.get('totalGrams')

                # Validate total grams
                try:
                    total_grams_value = float(total_grams)
                    if total_grams_value < 0:
                        failed.append({
                            "row": idx,
                            "data": row,
                            "error": "Total grams must be non-negative",
                            "missingFields": []
                        })
                        continue
                except ValueError:
                    failed.append({
                        "row": idx,
                        "data": row,
                        "error": "Invalid total grams format",
                        "missingFields": []
                    })
                    continue

                # Parse items
                items_data = parse_items_from_csv(row.get('items', ''))

                # Check for duplicate mixboxName in CSV
                if mixbox_name.lower() in seen_names and len(seen_names[mixbox_name.lower()]) > 1:
                    failed.append({
                        "row": idx,
                        "data": row,
                        "error": f"Duplicate MixBox Name in CSV: '{mixbox_name}'",
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
                    if not (provided_id.startswith('M') and provided_id[1:].isdigit()):
                        failed.append({
                            "row": idx,
                            "data": row,
                            "error": f"Invalid randomId format: '{provided_id}'. Must be 'M' followed by digits.",
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
                    if provided_id in existing_mixboxes_by_id:
                        existing_mixbox = existing_mixboxes_by_id[provided_id]
                        # Update existing record
                        update_data = {
                            'mixboxName': mixbox_name,
                            'totalGrams': total_grams_value,
                            'items': items_data,
                            'status': status,
                            'lastUpdatedDate': last_updated_date
                        }
                        if row.get('createdDate'):
                            update_data['createdDate'] = created_date
                        batch.append(UpdateOne(
                            {'_id': existing_mixbox['_id']},
                            {'$set': update_data}
                        ))
                        updated.append({
                            "row": idx,
                            "data": row,
                            "message": f"MixBox updated for randomId: '{provided_id}'"
                        })
                        updated_count += 1
                        max_id_number = max(max_id_number, int(provided_id[1:]))
                        # Update existing_mixboxes_by_name to prevent duplicate name errors
                        if existing_mixbox['mixboxName'].lower() != mixbox_name.lower():
                            del existing_mixboxes_by_name[existing_mixbox['mixboxName'].lower()]
                            existing_mixboxes_by_name[mixbox_name.lower()] = existing_mixbox
                        continue
                    # Valid, unused randomId from CSV
                    assigned_id = provided_id
                    used_ids.add(assigned_id)
                    max_id_number = max(max_id_number, int(assigned_id[1:]))
                else:
                    # Generate sequential ID for rows without a valid randomId
                    assigned_id = generate_sequential_id(used_ids)
                    used_ids.add(assigned_id)
                    max_id_number = max(max_id_number, int(assigned_id[1:]))

                # Check for duplicate mixboxName in the database
                if mixbox_name.lower() in existing_mixboxes_by_name:
                    existing_mixbox = existing_mixboxes_by_name[mixbox_name.lower()]
                    if existing_mixbox['randomId'] != assigned_id:
                        failed.append({
                            "row": idx,
                            "data": row,
                            "error": f"MixBox '{mixbox_name}' already exists with randomId: '{existing_mixbox['randomId']}'",
                            "missingFields": []
                        })
                        continue

                # Create new record
                mixbox_data = {
                    'mixboxName': mixbox_name,
                    'totalGrams': total_grams_value,
                    'items': items_data,
                    'randomId': assigned_id,
                    'status': status,
                    'createdDate': created_date,
                    'lastUpdatedDate': last_updated_date
                }

                batch.append(InsertOne(mixbox_data))
                successful.append({
                    "row": idx,
                    "data": row,
                    "assignedId": assigned_id
                })
                existing_mixboxes_by_name[mixbox_name.lower()] = mixbox_data
                existing_mixboxes_by_id[assigned_id] = mixbox_data
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

# Original routes (unchanged)
@router.post("/", response_model=str)
async def create_mixbox(mixbox: MixBoxPost):
    # Prepare data including randomId and status
    mixbox_dict = mixbox.dict()
    # mixbox_dict['randomId'] = random_id
    mixbox_dict['status'] = "active"

    # Insert into MongoDB
    result = collection.insert_one(mixbox_dict)
    return str(result.inserted_id)

@router.get("/", response_model=List[MixBox])
async def get_all_mixboxes():
    try:
        mixboxes = list(collection.find())
        formatted_mixboxes = []
        for mixbox in mixboxes:
            for key, value in mixbox.items():
                mixbox[key] = convert_to_string_or_none(value)
            mixbox["id"] = str(mixbox["_id"])
            formatted_mixboxes.append(MixBox(**mixbox))
        return formatted_mixboxes
    except Exception as e:
        print(f"Error fetching mixboxes: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/{id}", response_model=MixBox)
async def get_mixbox(id: str):
    try:
        mixbox = collection.find_one({"_id": ObjectId(id)})
        if mixbox:
            for key, value in mixbox.items():
                mixbox[key] = convert_to_string_or_none(value)
            mixbox["id"] = str(mixbox["_id"])
            return MixBox(**mixbox)
        else:
            raise HTTPException(status_code=404, detail="MixBox not found")
    except Exception as e:
        print(f"Error fetching mixbox by ID: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.put("/{id}", response_model=MixBox)
async def update_mixbox(id: str, mixbox: MixBoxPost):
    updated_mixbox = mixbox.dict(exclude_unset=True)
    result = collection.replace_one({"_id": ObjectId(id)}, updated_mixbox)
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="MixBox not found")
    return await get_mixbox(id)

@router.patch("/{id}", response_model=MixBox)
async def partial_update_mixbox(id: str, mixbox: MixBoxPost):
    updated_mixbox = {k: v for k, v in mixbox.dict(exclude_unset=True).items() if v is not None}
    result = collection.update_one({"_id": ObjectId(id)}, {"$set": updated_mixbox})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="MixBox not found")
    return await get_mixbox(id)

@router.patch("/{id}/status", response_model=MixBox)
async def patch_mixbox_status(id: str, mixbox_patch: MixBoxPost):
    existing_mixbox = collection.find_one({"_id": ObjectId(id)})
    if not existing_mixbox:
        raise HTTPException(status_code=404, detail="MixBox not found")

    updated_fields = {key: value for key, value in mixbox_patch.dict(exclude_unset=True).items() if value is not None}
    if updated_fields:
        result = collection.update_one({"_id": ObjectId(id)}, {"$set": updated_fields})
        if result.modified_count == 0:
            raise HTTPException(status_code=500, detail="Failed to update mixbox")

    updated_mixbox = collection.find_one({"_id": ObjectId(id)})
    for key, value in updated_mixbox.items():
        updated_mixbox[key] = convert_to_string_or_none(value)
    updated_mixbox["id"] = str(updated_mixbox["_id"])
    return MixBox(**updated_mixbox)

@router.delete("/{id}", response_model=dict)
async def delete_mixbox(mixbox_id: str):
    result = collection.delete_one({"_id": ObjectId(mixbox_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="MixBox not found")
    return {"message": "MixBox deleted successfully"}
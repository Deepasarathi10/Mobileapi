from datetime import datetime
import logging
import re
from typing import List, Optional
from fastapi import APIRouter, HTTPException, File, UploadFile
from bson import ObjectId
from fastapi.responses import StreamingResponse
import pytz
import csv
import io
from pymongo import InsertOne, UpdateOne

from .models import ItemGroup, ItemGroupPost
from .utils import get_itemgroup_collection

router = APIRouter()

logging.basicConfig(level=logging.INFO) 
logger = logging.getLogger(__name__)

# Header mapping for user-friendly CSV columns
header_mapping = {
    'Item Group ID': 'randomId',
    'Item Group': 'itemGroupName',
    'Status': 'status',
    'Created Date': 'createdDate',
    'Updated Date': 'lastUpdatedDate'
}

def get_localized_datetime():
    """Get current UTC datetime adjusted from IST."""
    ist = pytz.timezone("Asia/Kolkata")
    return datetime.now(ist).astimezone(pytz.UTC)

def set_counter_value(value: int, counter_id: str = "itemGroupId"):
    """Set the counter value in the database."""
    counter_collection = get_itemgroup_collection().database["counters"]
    counter_collection.update_one(
        {"_id": counter_id},
        {"$set": {"sequence_value": value}},
        upsert=True
    )

def get_current_counter_value(counter_id: str = "itemGroupId"):
    """Get the current counter value from the database."""
    counter_collection = get_itemgroup_collection().database["counters"]
    counter = counter_collection.find_one({"_id": counter_id})
    return counter["sequence_value"] if counter else 0

def initialize_counter_if_needed(counter_id: str = "itemGroupId"):
    """Initialize counter to the highest existing ID number (IGxxx)."""
    collection = get_itemgroup_collection()
    counter_collection = collection.database["counters"]

    highest_item = collection.find_one(
        {"randomId": {"$regex": "^IG\\d+$"}},
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
    """Generate an IGxxx ID, filling gaps in the sequence, considering used_ids."""
    collection = get_itemgroup_collection()
    counter_collection = collection.database["counters"]

    initialize_counter_if_needed()
    counter = counter_collection.find_one({"_id": "itemGroupId"})
    current_counter = counter["sequence_value"] if counter else 0

    # Find all existing IGxxx IDs in the database
    existing_ids = collection.find({"randomId": {"$regex": "^IG\\d+$"}}, {"randomId": 1})
    id_numbers = set()
    for item in existing_ids:
        try:
            if item["randomId"].startswith("IG"):
                num = int(item["randomId"][2:])
                id_numbers.add(num)
        except (ValueError, TypeError):
            continue

    # Include used_ids from CSV if provided
    if used_ids:
        for rid in used_ids:
            try:
                if rid.startswith("IG") and rid[2:].isdigit():
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
        {"_id": "itemGroupId"},
        {"$set": {"sequence_value": next_number}},
        upsert=True
    )

    return f"IG{next_number:03d}"

@router.post("/reset-counter")
async def reset_sequence():
    """Reset the counter to 0. Next ID will be IG001."""
    set_counter_value(0)
    return {"message": "Counter reset successfully. Next ID will be IG001"}

@router.get("/export-csv")
async def export_all_itemgroups_to_csv():
    """Export active item groups to a CSV file."""
    try:
        logger.info("Received request for /itemgroups/export-csv")
        collection = get_itemgroup_collection()
        records = list(collection.find({"status": "active"}, {'_id': 0}))
        
        if not records:
            logger.warning("No active item groups found for export")
            raise HTTPException(status_code=404, detail="No active item groups found to export")

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
                'Item Group ID': record.get('randomId', ''),
                'Item Group': record.get('itemGroupName', ''),
                'Status': record.get('status', ''),
                'Created Date': created_str,
                'Updated Date': updated_str
            })

        csv_stream.seek(0)
        filename = f"itemgroups_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
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
        raise HTTPException(status_code=500, detail=f"Error exporting item groups: {str(e)}")






@router.post("/import-csv")
async def import_csv_data(file: UploadFile = File(...)):
    """Import item groups from a CSV file, preserving valid randomIds and handling duplicates."""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Invalid file format. Please upload a CSV file.")

    try:
        collection = get_itemgroup_collection()
        current_datetime = get_localized_datetime()

        content = await file.read()
        decoded = content.decode('utf-8-sig', errors='replace')
        csv_reader = csv.DictReader(io.StringIO(decoded))

        headers = [header_mapping.get(header.strip(), header.strip()) for header in csv_reader.fieldnames or []]
        csv_reader.fieldnames = headers

        required_fields = ['itemGroupName']
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

            name = cleaned_row.get('itemGroupName', '').lower()
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

        # Get existing item groups by randomId and itemGroupName
        existing_itemgroups_by_name = {g['itemGroupName'].lower(): g for g in collection.find({}, {'itemGroupName': 1, '_id': 1, 'randomId': 1, 'status': 1})}
        existing_itemgroups_by_id = {g['randomId']: g for g in collection.find({"randomId": {"$regex": "^IG\\d+$"}}, {'itemGroupName': 1, '_id': 1, 'randomId': 1, 'status': 1})}
        used_ids = set(collection.distinct("randomId", {"randomId": {"$regex": "^IG\\d+$"}}))

        initialize_counter_if_needed()
        max_id_number = get_current_counter_value()

        inserted = []
        duplicates = []
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

                itemgroup_name = row.get('itemGroupName').strip()
                # Check for duplicate itemGroupName in CSV or database
                if itemgroup_name.lower() in seen_names and len(seen_names[itemgroup_name.lower()]) > 1:
                    duplicates.append(itemgroup_name)
                    logger.info(f"Item Group '{itemgroup_name}' is duplicated in CSV, skipping row {idx}.")
                    continue

                if itemgroup_name.lower() in existing_itemgroups_by_name:
                    existing_itemgroup = existing_itemgroups_by_name[itemgroup_name.lower()]
                    duplicates.append(itemgroup_name)
                    logger.info(f"Item Group '{itemgroup_name}' already exists with randomId: '{existing_itemgroup['randomId']}', skipping row {idx}.")
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
                    if not (provided_id.startswith('IG') and provided_id[2:].isdigit()):
                        failed.append({
                            "row": idx,
                            "data": row,
                            "error": f"Invalid randomId format: '{provided_id}'. Must be 'IG' followed by digits.",
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
                    if provided_id in existing_itemgroups_by_id:
                        existing_itemgroup = existing_itemgroups_by_id[provided_id]
                        # Update existing record
                        update_data = {
                            'itemGroupName': itemgroup_name,
                            'status': status,
                            'lastUpdatedDate': last_updated_date
                        }
                        if row.get('createdDate'):
                            update_data['createdDate'] = created_date
                        batch.append(UpdateOne(
                            {'_id': existing_itemgroup['_id']},
                            {'$set': update_data}
                        ))
                        updated.append({
                            "row": idx,
                            "data": row,
                            "message": f"Item Group updated for randomId: '{provided_id}'"
                        })
                        max_id_number = max(max_id_number, int(provided_id[2:]))
                        # Update existing_itemgroups_by_name to prevent duplicate name errors
                        if existing_itemgroup['itemGroupName'].lower() != itemgroup_name.lower():
                            del existing_itemgroups_by_name[existing_itemgroup['itemGroupName'].lower()]
                            existing_itemgroups_by_name[itemgroup_name.lower()] = existing_itemgroup
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

                # Create new record
                itemgroup_data = {
                    'itemGroupName': itemgroup_name,
                    'randomId': assigned_id,
                    'status': status,
                    'createdDate': created_date,
                    'lastUpdatedDate': last_updated_date
                }

                batch.append(InsertOne(itemgroup_data))
                inserted.append(assigned_id)
                existing_itemgroups_by_name[itemgroup_name.lower()] = itemgroup_data
                existing_itemgroups_by_id[assigned_id] = itemgroup_data
                logger.info(f"Inserted item group {itemgroup_name} with ID {assigned_id}")

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
            "message": f"Import completed: {len(inserted)} new item groups, {len(duplicates)} duplicates skipped, {len(updated)} updated.",
            "inserted_ids": inserted,
            "duplicates": duplicates,
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
async def create_itemgroup(itemgroup: ItemGroupPost):
    """Create a new item group with a sequential ID."""
    current_datetime = get_localized_datetime()
    initialize_counter_if_needed()
    random_id = generate_sequential_id()

    # Prepare data including randomId
    new_itemgroup_data = itemgroup.dict()
    new_itemgroup_data['randomId'] = random_id
    new_itemgroup_data['status'] = "active"
    new_itemgroup_data['createdDate'] = current_datetime
    new_itemgroup_data['lastUpdatedDate'] = current_datetime

    # Insert into MongoDB
    try:
        result = get_itemgroup_collection().insert_one(new_itemgroup_data)
        return str(result.inserted_id)
    except Exception as e:
        logger.error(f"Error creating item group: {e}")
        raise HTTPException(status_code=500, detail="Failed to create item group")

@router.get("/", response_model=List[ItemGroup])
async def get_all_itemgroup():
    """Get all item groups."""
    try:
        itemgroups = list(get_itemgroup_collection().find())
        formatted_itemgroup = []
        for itemgroup in itemgroups:
            itemgroup["itemGroupId"] = str(itemgroup["_id"])
            formatted_itemgroup.append(ItemGroup(**itemgroup))
        return formatted_itemgroup
    except Exception as e:
        logger.error(f"Error fetching item groups: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/{itemgroup_id}", response_model=ItemGroup)
async def get_itemgroup_by_id(itemgroup_id: str):
    """Get a specific item group by ID."""
    try:
        itemgroup = get_itemgroup_collection().find_one({"_id": ObjectId(itemgroup_id)})
        if itemgroup:
            itemgroup["itemGroupId"] = str(itemgroup["_id"])
            return ItemGroup(**itemgroup)
        else:
            raise HTTPException(status_code=404, detail="Item group not found")
    except Exception as e:
        logger.error(f"Error fetching item group by ID: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.put("/{itemgroup_id}")
async def update_itemgroup(itemgroup_id: str, itemgroup: ItemGroupPost):
    """Update all fields of an existing item group."""
    try:
        current_datetime = get_localized_datetime()
        updated_itemgroup = itemgroup.dict(exclude_unset=True)
        updated_itemgroup['lastUpdatedDate'] = current_datetime
        result = get_itemgroup_collection().update_one(
            {"_id": ObjectId(itemgroup_id)},
            {"$set": updated_itemgroup}
        )
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Item group not found")
        return {"message": "Item group updated successfully"}
    except Exception as e:
        logger.error(f"Error updating item group: {e}")
        raise HTTPException(status_code=500, detail="Failed to update item group")

@router.patch("/{itemgroup_id}", response_model=ItemGroup)
async def patch_itemgroup(itemgroup_id: str, itemgroup_patch: ItemGroupPost):
    """Update specific fields of an existing item group."""
    try:
        existing_itemgroup = get_itemgroup_collection().find_one({"_id": ObjectId(itemgroup_id)})
        if not existing_itemgroup:
            raise HTTPException(status_code=404, detail="Item group not found")

        updated_fields = {key: value for key, value in itemgroup_patch.dict(exclude_unset=True).items() if value is not None}
        updated_fields['lastUpdatedDate'] = get_localized_datetime()
        if updated_fields:
            result = get_itemgroup_collection().update_one(
                {"_id": ObjectId(itemgroup_id)},
                {"$set": updated_fields}
            )
            if result.modified_count == 0:
                raise HTTPException(status_code=500, detail="Failed to update item group")

        updated_itemgroup = get_itemgroup_collection().find_one({"_id": ObjectId(itemgroup_id)})
        updated_itemgroup["itemGroupId"] = str(updated_itemgroup["_id"])
        return ItemGroup(**updated_itemgroup)
    except Exception as e:
        logger.error(f"Error patching item group: {e}")
        raise HTTPException(status_code=500, detail="Failed to patch item group")

@router.delete("/{itemgroup_id}")
async def delete_itemgroup(itemgroup_id: str):
    """Delete an item group."""
    try:
        result = get_itemgroup_collection().delete_one({"_id": ObjectId(itemgroup_id)})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Item group not found")
        return {"message": "Item group deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting item group: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete item group")
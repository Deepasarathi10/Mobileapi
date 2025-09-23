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
from .models import Discount, DiscountPost
from .utils import get_discount_collection, convert_to_string_or_none

router = APIRouter()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Header mapping for user-friendly CSV columns
header_mapping = {
    'Discount ID': 'randomId',
    'Discount Name': 'discountName',
    'Discount Percentage': 'discountPercentage',
    'Status': 'status',
    'Created Date': 'createdDate',
    'Updated Date': 'lastUpdatedDate'
}

def get_localized_datetime():
    """Get current UTC datetime adjusted from IST."""
    ist = pytz.timezone("Asia/Kolkata")
    return datetime.now(ist).astimezone(pytz.UTC)

# Original counter functions (keeping existing functionality)
def get_next_counter_value():
    counter_collection = get_discount_collection().database["counters"]
    counter = counter_collection.find_one_and_update(
        {"_id": "discountId"},
        {"$inc": {"sequence_value": 1}},
        upsert=True,
        return_document=True
    )
    return counter["sequence_value"]

def reset_counter():
    counter_collection = get_discount_collection().database["counters"]
    counter_collection.update_one(
        {"_id": "discountId"},
        {"$set": {"sequence_value": 0}},
        upsert=True
    )

def generate_random_id():
    counter_value = get_next_counter_value()
    return f"D{counter_value:03d}"

# New CSV-specific counter functions
def set_counter_value(value: int, counter_id: str = "discountId"):
    """Set the counter value in the database."""
    counter_collection = get_discount_collection().database["counters"]
    counter_collection.update_one(
        {"_id": counter_id},
        {"$set": {"sequence_value": value}},
        upsert=True
    )

def get_current_counter_value(counter_id: str = "discountId"):
    """Get the current counter value from the database."""
    counter_collection = get_discount_collection().database["counters"]
    counter = counter_collection.find_one({"_id": counter_id})
    return counter["sequence_value"] if counter else 0

def initialize_counter_if_needed(counter_id: str = "discountId"):
    """Initialize counter to the highest existing ID number (Dxxx)."""
    collection = get_discount_collection()
    counter_collection = collection.database["counters"]

    highest_item = collection.find_one(
        {"randomId": {"$regex": "^D\\d+$"}},
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
    """Generate a Dxxx ID, filling gaps in the sequence, considering used_ids."""
    collection = get_discount_collection()
    counter_collection = collection.database["counters"]

    initialize_counter_if_needed()
    counter = counter_collection.find_one({"_id": "discountId"})
    current_counter = counter["sequence_value"] if counter else 0

    # Find all existing Dxxx IDs in the database
    existing_ids = collection.find({"randomId": {"$regex": "^D\\d+$"}}, {"randomId": 1})
    id_numbers = set()
    for item in existing_ids:
        try:
            if item["randomId"].startswith("D"):
                num = int(item["randomId"][1:])
                id_numbers.add(num)
        except (ValueError, TypeError):
            continue

    # Include used_ids from CSV if provided
    if used_ids:
        for rid in used_ids:
            try:
                if rid.startswith("D") and rid[1:].isdigit():
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
        {"_id": "discountId"},
        {"$set": {"sequence_value": next_number}},
        upsert=True
    )

    return f"D{next_number:03d}"

# CSV-specific routes
@router.post("/reset-counter")
async def reset_sequence():
    """Reset the counter to 0. Next ID will be D001."""
    set_counter_value(0)
    return {"message": "Counter reset successfully. Next ID will be D001"}

@router.get("/export-csv")
async def export_all_discounts_to_csv():
    """Export active discounts to a CSV file."""
    try:
        logger.info("Received request for /discounts/export-csv")
        collection = get_discount_collection()
        records = list(collection.find({"status": "active"}, {'_id': 0}))
        
        if not records:
            logger.warning("No active discounts found for export")
            raise HTTPException(status_code=404, detail="No active discounts found to export")

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
                'Discount ID': record.get('randomId', ''),
                'Discount Name': record.get('discountName', ''),
                'Discount Percentage': record.get('discountPercentage', ''),
                'Status': record.get('status', ''),
                'Created Date': created_str,
                'Updated Date': updated_str
            })

        csv_stream.seek(0)
        filename = f"discounts_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
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
        raise HTTPException(status_code=500, detail=f"Error exporting discounts: {str(e)}")

@router.post("/import-csv")
async def import_csv_data(file: UploadFile = File(...)):
    """Import discounts from a CSV file, preserving valid randomIds and handling duplicates."""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Invalid file format. Please upload a CSV file.")

    try:
        collection = get_discount_collection()
        current_datetime = get_localized_datetime()

        content = await file.read()
        decoded = content.decode('utf-8-sig', errors='replace')
        csv_reader = csv.DictReader(io.StringIO(decoded))

        headers = [header_mapping.get(header.strip(), header.strip()) for header in csv_reader.fieldnames or []]
        csv_reader.fieldnames = headers

        required_fields = ['discountName', 'discountPercentage']
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

            name = cleaned_row.get('discountName', '').lower()
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

        # Get existing discounts by randomId and discountName
        existing_discounts_by_name = {d['discountName'].lower(): d for d in collection.find({}, {'discountName': 1, '_id': 1, 'randomId': 1, 'status': 1})}
        existing_discounts_by_id = {d['randomId']: d for d in collection.find({"randomId": {"$regex": "^D\\d+$"}}, {'discountName': 1, '_id': 1, 'randomId': 1, 'status': 1})}
        used_ids = set(collection.distinct("randomId", {"randomId": {"$regex": "^D\\d+$"}}))

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

                discount_name = row.get('discountName')
                discount_percentage = row.get('discountPercentage')

                # Validate discount percentage
                try:
                    percentage_value = float(discount_percentage)
                    if percentage_value < 0 or percentage_value > 100:
                        failed.append({
                            "row": idx,
                            "data": row,
                            "error": "Discount percentage must be between 0 and 100",
                            "missingFields": []
                        })
                        continue
                except ValueError:
                    failed.append({
                        "row": idx,
                        "data": row,
                        "error": "Invalid discount percentage format",
                        "missingFields": []
                    })
                    continue

                # Check for duplicate discountName in CSV
                if discount_name.lower() in seen_names and len(seen_names[discount_name.lower()]) > 1:
                    failed.append({
                        "row": idx,
                        "data": row,
                        "error": f"Duplicate Discount Name in CSV: '{discount_name}'",
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
                    if not (provided_id.startswith('D') and provided_id[1:].isdigit()):
                        failed.append({
                            "row": idx,
                            "data": row,
                            "error": f"Invalid randomId format: '{provided_id}'. Must be 'D' followed by digits.",
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
                    if provided_id in existing_discounts_by_id:
                        existing_discount = existing_discounts_by_id[provided_id]
                        # Update existing record
                        update_data = {
                            'discountName': discount_name,
                            'discountPercentage': discount_percentage,
                            'status': status,
                            'lastUpdatedDate': last_updated_date
                        }
                        if row.get('createdDate'):
                            update_data['createdDate'] = created_date
                        batch.append(UpdateOne(
                            {'_id': existing_discount['_id']},
                            {'$set': update_data}
                        ))
                        updated.append({
                            "row": idx,
                            "data": row,
                            "message": f"Discount updated for randomId: '{provided_id}'"
                        })
                        updated_count += 1
                        max_id_number = max(max_id_number, int(provided_id[1:]))
                        # Update existing_discounts_by_name to prevent duplicate name errors
                        if existing_discount['discountName'].lower() != discount_name.lower():
                            del existing_discounts_by_name[existing_discount['discountName'].lower()]
                            existing_discounts_by_name[discount_name.lower()] = existing_discount
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

                # Check for duplicate discountName in the database
                if discount_name.lower() in existing_discounts_by_name:
                    existing_discount = existing_discounts_by_name[discount_name.lower()]
                    if existing_discount['randomId'] != assigned_id:
                        failed.append({
                            "row": idx,
                            "data": row,
                            "error": f"Discount '{discount_name}' already exists with randomId: '{existing_discount['randomId']}'",
                            "missingFields": []
                        })
                        continue

                # Create new record
                discount_data = {
                    'discountName': discount_name,
                    'discountPercentage': discount_percentage,
                    'randomId': assigned_id,
                    'status': status,
                    'createdDate': created_date,
                    'lastUpdatedDate': last_updated_date
                }

                batch.append(InsertOne(discount_data))
                successful.append({
                    "row": idx,
                    "data": row,
                    "assignedId": assigned_id
                })
                existing_discounts_by_name[discount_name.lower()] = discount_data
                existing_discounts_by_id[assigned_id] = discount_data
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
async def create_discount(discount: DiscountPost):
    # Check if the collection is empty
    if get_discount_collection().count_documents({}) == 0:
        reset_counter()

    # Generate randomId
    random_id = generate_random_id()

    # Prepare data including randomId
    new_discount_data = discount.dict()
    new_discount_data['randomId'] = random_id
    new_discount_data['status'] = "active"

    # Insert into MongoDB
    result = get_discount_collection().insert_one(new_discount_data)
    return str(result.inserted_id)

@router.get("/", response_model=List[Discount])
async def get_all_discounts():
    try:
        item_discounts = list(get_discount_collection().find())
        formatted_discounts = []
        for discount in item_discounts:
            for key, value in discount.items():
                discount[key] = convert_to_string_or_none(value)
            discount["discountId"] = str(discount["_id"])
            formatted_discounts.append(Discount(**discount))
        return formatted_discounts
    except Exception as e:
        print(f"Error fetching discounts: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/{discount_id}", response_model=Discount)
async def get_discount_by_id(discount_id: str):
    try:
        discount_data = get_discount_collection().find_one({"_id": ObjectId(discount_id)})
        if discount_data:
            for key, value in discount_data.items():
                discount_data[key] = convert_to_string_or_none(value)
            discount_data["discountId"] = str(discount_data["_id"])
            return Discount(**discount_data)
        else:
            raise HTTPException(status_code=404, detail="Discount not found")
    except Exception as e:
        print(f"Error fetching discount by ID: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.patch("/{discount_id}")
async def update_discount(discount_id: str, discount: DiscountPost):
    updated_discount = discount.dict(exclude_unset=True)  # exclude_unset=True prevents sending None values to MongoDB
    result = get_discount_collection().update_one({"_id": ObjectId(discount_id)}, {"$set": updated_discount})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Discount not found")
    return {"message": "Discount updated successfully"}

@router.patch("/{discount_id}/status")
async def patch_discount_status(discount_id: str, discount_patch: DiscountPost):
    existing_discount = get_discount_collection().find_one({"_id": ObjectId(discount_id)})
    if not existing_discount:
        raise HTTPException(status_code=404, detail="Discount not found")

    updated_fields = {key: value for key, value in discount_patch.dict(exclude_unset=True).items() if value is not None}
    if updated_fields:
        result = get_discount_collection().update_one({"_id": ObjectId(discount_id)}, {"$set": updated_fields})
        if result.modified_count == 0:
            raise HTTPException(status_code=500, detail="Failed to update discount")

    updated_discount = get_discount_collection().find_one({"_id": ObjectId(discount_id)})
    for key, value in updated_discount.items():
        updated_discount[key] = convert_to_string_or_none(value)
    updated_discount["discountId"] = str(updated_discount["_id"])
    return updated_discount

@router.delete("/{discount_id}")
async def delete_discount(discount_id: str):
    result = get_discount_collection().delete_one({"_id": ObjectId(discount_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Discount not found")
    return {"message": "Discount deleted successfully"}
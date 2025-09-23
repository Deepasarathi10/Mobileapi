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

from .models import uom, uomPost
from .utils import get_uom_collection, convert_to_string_or_none

router = APIRouter()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Header mapping for user-friendly CSV columns
header_mapping = {
    'UOM ID': 'randomId',
    'Measurement Type': 'measurementType',
    'UOM': 'uom',
    'Precision': 'precision',
    'Status': 'status'
}

def get_localized_datetime():
    """Get current UTC datetime adjusted from IST."""
    ist = pytz.timezone("Asia/Kolkata")
    return datetime.now(ist).astimezone(pytz.UTC)

def set_counter_value(value: int, counter_id: str = "uomId"):
    """Set the counter value in the database."""
    counter_collection = get_uom_collection().database["counters"]
    counter_collection.update_one(
        {"_id": counter_id},
        {"$set": {"sequence_value": value}},
        upsert=True
    )

def get_current_counter_value(counter_id: str = "uomId"):
    """Get the current counter value from the database."""
    counter_collection = get_uom_collection().database["counters"]
    counter = counter_collection.find_one({"_id": counter_id})
    return counter["sequence_value"] if counter else 0

def initialize_counter_if_needed(counter_id: str = "uomId"):
    """Initialize counter to the highest existing ID number (IUxxx)."""
    collection = get_uom_collection()
    counter_collection = collection.database["counters"]

    highest_item = collection.find_one(
        {"randomId": {"$regex": "^IU\\d+$"}},
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

def get_next_counter_value():
    counter_collection = get_uom_collection().database["counters"]
    counter = counter_collection.find_one_and_update(
        {"_id": "uomId"},
        {"$inc": {"sequence_value": 1}},
        upsert=True,
        return_document=True
    )
    return counter["sequence_value"]

def reset_counter():
    counter_collection = get_uom_collection().database["counters"]
    counter_collection.update_one(
        {"_id": "uomId"},
        {"$set": {"sequence_value": 0}},
        upsert=True
    )

def generate_random_id(used_ids: set = None):
    """Generate an IUxxx ID, filling gaps in the sequence, considering used_ids."""
    collection = get_uom_collection()
    counter_collection = collection.database["counters"]

    initialize_counter_if_needed()
    counter = counter_collection.find_one({"_id": "uomId"})
    current_counter = counter["sequence_value"] if counter else 0

    # Find all existing IUxxx IDs in the database
    existing_ids = collection.find({"randomId": {"$regex": "^IU\\d+$"}}, {"randomId": 1})
    id_numbers = set()
    for item in existing_ids:
        try:
            if item["randomId"].startswith("IU"):
                num = int(item["randomId"][2:])
                id_numbers.add(num)
        except (ValueError, TypeError):
            continue

    # Include used_ids from CSV if provided
    if used_ids:
        for rid in used_ids:
            try:
                if rid.startswith("IU") and rid[2:].isdigit():
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
        {"_id": "uomId"},
        {"$set": {"sequence_value": next_number}},
        upsert=True
    )

    return f"IU{next_number:03d}"

@router.post("/reset-counter")
async def reset_sequence():
    """Reset the counter to 0. Next ID will be IU001."""
    set_counter_value(0)
    return {"message": "Counter reset successfully. Next ID will be IU001"}

@router.get("/export-csv")
async def export_all_uoms_to_csv():
    """Export active uoms to a CSV file."""
    try:
        logger.info("Received request for /uoms/export-csv")
        collection = get_uom_collection()
        records = list(collection.find({"status": "active"}, {'_id': 0}))
        
        if not records:
            logger.warning("No active uoms found for export")
            raise HTTPException(status_code=404, detail="No active uoms found to export")

        csv_stream = io.StringIO()
        fieldnames = list(header_mapping.keys())
        writer = csv.DictWriter(csv_stream, fieldnames=fieldnames)
        writer.writeheader()

        for record in records:
            writer.writerow({
                'UOM ID': record.get('randomId', ''),
                'Measurement Type': record.get('measurementType', ''),
                'UOM': record.get('uom', ''),
                'Precision': str(record.get('precision', '')),
                'Status': record.get('status', '')
            })

        csv_stream.seek(0)
        filename = f"uoms_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
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
        raise HTTPException(status_code=500, detail=f"Error exporting uoms: {str(e)}")

@router.post("/import-csv")
async def import_csv_data(file: UploadFile = File(...)):
    """Import uoms from a CSV file, preserving valid randomIds and handling duplicates."""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Invalid file format. Please upload a CSV file.")

    try:
        collection = get_uom_collection()
        current_datetime = get_localized_datetime()

        content = await file.read()
        decoded = content.decode('utf-8-sig', errors='replace')
        csv_reader = csv.DictReader(io.StringIO(decoded))

        # Validate headers
        if not csv_reader.fieldnames:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "CSV file has no headers",
                    "required": list(header_mapping.keys())
                }
            )

        # Map headers, handling case-insensitive matches and direct field names
        headers = []
        unmapped_headers = []
        for header in csv_reader.fieldnames:
            header_clean = header.strip()
            # Check if header matches header_mapping keys (case-insensitive) or values
            mapped_field = next(
                (value for key, value in header_mapping.items() if key.lower() == header_clean.lower()),
                header_clean if header_clean in header_mapping.values() else None
            )
            if mapped_field:
                headers.append(mapped_field)
            else:
                headers.append(header_clean)
                unmapped_headers.append(header_clean)

        csv_reader.fieldnames = headers

        required_fields = ['measurementType', 'uom']
        missing_headers = [field for field in required_fields if field not in headers]
        if missing_headers:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Missing required headers in CSV file",
                    "missing": [header_mapping.get(field, field) for field in missing_headers],
                    "required": list(header_mapping.keys()),
                    "unmapped": unmapped_headers
                }
            )

        failed = []  # Initialize failed list
        rows = []
        seen_uoms = {}
        seen_ids = {}
        for idx, row in enumerate(csv_reader, 1):
            cleaned_row = {k: str(v).strip() if v is not None else "" for k, v in row.items()}
            rows.append((idx, cleaned_row))

            # Validate required fields in row
            missing_fields = [field for field in required_fields if not cleaned_row.get(field)]
            if missing_fields:
                failed.append({
                    "row": idx,
                    "data": cleaned_row,
                    "error": f"Missing required fields: {', '.join([header_mapping.get(field, field) for field in missing_fields])}",
                    "missingFields": [header_mapping.get(field, field) for field in missing_fields]
                })
                continue

            uom_key = (cleaned_row['measurementType'].lower(), cleaned_row['uom'].lower())
            if uom_key[0] and uom_key[1]:
                if uom_key in seen_uoms:
                    seen_uoms[uom_key].append(idx)
                else:
                    seen_uoms[uom_key] = [idx]

            random_id = cleaned_row.get('randomId', '').strip()
            if random_id:
                if random_id in seen_ids:
                    seen_ids[random_id].append(idx)
                else:
                    seen_ids[random_id] = [idx]

        # Get existing uoms by randomId and measurementType+uom
        existing_uoms_by_key = {}
        existing_uoms_by_id = {}
        for u in collection.find({}, {'measurementType': 1, 'uom': 1, '_id': 1, 'randomId': 1, 'status': 1, 'precision': 1}):
            # Skip documents missing measurementType or uom
            if not (u.get('measurementType') and u.get('uom')):
                logger.warning(f"Skipping invalid document with _id: {u.get('_id')} - missing measurementType or uom")
                continue
            existing_uoms_by_key[(u['measurementType'].lower(), u['uom'].lower())] = u
            if u.get('randomId') and re.match(r"^IU\d+$", u['randomId']):
                existing_uoms_by_id[u['randomId']] = u

        used_ids = set(collection.distinct("randomId", {"randomId": {"$regex": "^IU\\d+$"}}))

        initialize_counter_if_needed()
        max_id_number = get_current_counter_value()

        inserted_count = 0
        updated_count = 0
        successful = []
        updated = []
        batch = []

        for idx, row in rows:
            try:
                # Validate required fields
                missing_fields = [field for field in required_fields if not row.get(field)]
                if missing_fields:
                    failed.append({
                        "row": idx,
                        "data": row,
                        "error": f"Missing required fields: {', '.join([header_mapping.get(field, field) for field in missing_fields])}",
                        "missingFields": [header_mapping.get(field, field) for field in missing_fields]
                    })
                    continue

                measurement_type = row['measurementType']
                uom_value = row['uom']
                uom_key = (measurement_type.lower(), uom_value.lower())

                # Check for duplicate measurementType+uom in CSV
                if uom_key in seen_uoms and len(seen_uoms[uom_key]) > 1:
                    failed.append({
                        "row": idx,
                        "data": row,
                        "error": f"Duplicate UOM in CSV: measurementType='{measurement_type}', uom='{uom_value}'",
                        "missingFields": []
                    })
                    continue

                # Validate status
                status = row.get('status', 'active').lower()
                if status not in ['active', 'inactive']:
                    status = 'active'

                # Parse precision
                precision = row.get('precision', None)
                try:
                    precision = float(precision) if precision else None
                except (ValueError, TypeError):
                    precision = None

                provided_id = row.get('randomId', '').strip()
                assigned_id = None

                # Handle randomId
                if provided_id:
                    if not (provided_id.startswith('IU') and provided_id[2:].isdigit()):
                        failed.append({
                            "row": idx,
                            "data": row,
                            "error": f"Invalid randomId format: '{provided_id}'. Must be 'IU' followed by digits.",
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
                    if provided_id in existing_uoms_by_id:
                        existing_uom = existing_uoms_by_id[provided_id]
                        # Update existing record
                        update_data = {
                            'measurementType': measurement_type,
                            'uom': uom_value,
                            'precision': precision,
                            'status': status
                        }
                        batch.append(UpdateOne(
                            {'_id': existing_uom['_id']},
                            {'$set': update_data}
                        ))
                        updated.append({
                            "row": idx,
                            "data": row,
                            "message": f"UOM updated for randomId: '{provided_id}'"
                        })
                        updated_count += 1
                        max_id_number = max(max_id_number, int(provided_id[2:]))
                        # Update existing_uoms_by_key to prevent duplicate name errors
                        if (existing_uom['measurementType'].lower(), existing_uom['uom'].lower()) != uom_key:
                            del existing_uoms_by_key[(existing_uom['measurementType'].lower(), existing_uom['uom'].lower())]
                            existing_uoms_by_key[uom_key] = existing_uom
                        continue
                    # Valid, unused randomId from CSV
                    assigned_id = provided_id
                    used_ids.add(assigned_id)
                    max_id_number = max(max_id_number, int(assigned_id[2:]))
                else:
                    # Generate sequential ID for rows without a valid randomId
                    assigned_id = generate_random_id(used_ids)
                    used_ids.add(assigned_id)
                    max_id_number = max(max_id_number, int(assigned_id[2:]))

                # Check for duplicate measurementType+uom in the database
                if uom_key in existing_uoms_by_key:
                    existing_uom = existing_uoms_by_key[uom_key]
                    if existing_uom['randomId'] != assigned_id:
                        failed.append({
                            "row": idx,
                            "data": row,
                            "error": f"UOM with measurementType='{measurement_type}', uom='{uom_value}' already exists with randomId: '{existing_uom['randomId']}'",
                            "missingFields": []
                        })
                        continue

                # Create new record
                uom_data = {
                    'measurementType': measurement_type,
                    'uom': uom_value,
                    'precision': precision,
                    'status': status,
                    'randomId': assigned_id
                }

                batch.append(InsertOne(uom_data))
                successful.append({
                    "row": idx,
                    "data": row,
                    "assignedId": assigned_id
                })
                existing_uoms_by_key[uom_key] = uom_data
                existing_uoms_by_id[assigned_id] = uom_data
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
async def create_uom(uom: uomPost):
    # Check if the collection is empty
    if get_uom_collection().count_documents({}) == 0:
        reset_counter()

    # Generate randomId
    random_id = generate_random_id()

    # Prepare data including randomId
    new_uom_data = uom.dict()
    new_uom_data['randomId'] = random_id
    new_uom_data['status'] = "active"

    # Insert into MongoDB
    result = get_uom_collection().insert_one(new_uom_data)
    return str(result.inserted_id)

@router.get("/", response_model=List[uom])
async def get_all_uom():
    try:
        itemuom = list(get_uom_collection().find())
        formatted_uom = []
        for uoms in itemuom:
            for key, value in uoms.items():
                uoms[key] = convert_to_string_or_none(value)
            uoms["uomId"] = str(uoms["_id"])
            formatted_uom.append(uom(**uoms))
        return formatted_uom
    except Exception as e:
        logger.error(f"Error fetching uoms: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/{uom_id}", response_model=uom)
async def get_uom_by_id(uom_id: str):
    try:
        uom_data = get_uom_collection().find_one({"_id": ObjectId(uom_id)})
        if uom_data:
            uom_data["uomId"] = str(uom_data["_id"])
            return uom(**uom_data)
        else:
            raise HTTPException(status_code=404, detail="UOM not found")
    except Exception as e:
        logger.error(f"Error fetching uom by ID: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.patch("/{uom_id}")
async def update_uom(uom_id: str, uom: uomPost):
    updated_uom = uom.dict(exclude_unset=True)  # exclude_unset=True prevents sending None values to MongoDB
    result = get_uom_collection().update_one({"_id": ObjectId(uom_id)}, {"$set": updated_uom})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="UOM not found")
    return {"message": "UOM updated successfully"}
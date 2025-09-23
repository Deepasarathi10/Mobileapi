from typing import List, Optional
from fastapi import APIRouter, HTTPException, File, UploadFile
from bson import ObjectId
from fastapi.responses import StreamingResponse
import pytz
import csv
import io
from pymongo import InsertOne, UpdateOne
from datetime import datetime
import logging
import re

from .models import tax, taxPost
from .utils import get_tax_collection, convert_to_string_or_none

router = APIRouter()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Header mapping for user-friendly CSV columns
header_mapping = {
    'Tax ID': 'randomId',
    'Tax Name': 'taxName',
    'Tax Percentage': 'taxPercentage',
    'Status': 'status'
}

def get_localized_datetime():
    """Get current UTC datetime adjusted from IST."""
    ist = pytz.timezone("Asia/Kolkata")
    return datetime.now(ist).astimezone(pytz.UTC)

def set_counter_value(value: int, counter_id: str = "taxId"):
    """Set the counter value in the database."""
    counter_collection = get_tax_collection().database["counters"]
    counter_collection.update_one(
        {"_id": counter_id},
        {"$set": {"sequence_value": value}},
        upsert=True
    )

def get_current_counter_value(counter_id: str = "taxId"):
    """Get the current counter value from the database."""
    counter_collection = get_tax_collection().database["counters"]
    counter = counter_collection.find_one({"_id": counter_id})
    return counter["sequence_value"] if counter else 0

def initialize_counter_if_needed(counter_id: str = "taxId"):
    """Initialize counter to the highest existing ID number (ITxxx)."""
    collection = get_tax_collection()
    counter_collection = collection.database["counters"]

    highest_item = collection.find_one(
        {"randomId": {"$regex": "^IT\\d+$"}},
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
    counter_collection = get_tax_collection().database["counters"]
    counter = counter_collection.find_one_and_update(
        {"_id": "taxId"},
        {"$inc": {"sequence_value": 1}},
        upsert=True,
        return_document=True
    )
    return counter["sequence_value"]

def reset_counter():
    counter_collection = get_tax_collection().database["counters"]
    counter_collection.update_one(
        {"_id": "taxId"},
        {"$set": {"sequence_value": 0}},
        upsert=True
    )

def generate_random_id(used_ids: set = None):
    """Generate an ITxxx ID, filling gaps in the sequence, considering used_ids."""
    collection = get_tax_collection()
    counter_collection = collection.database["counters"]

    initialize_counter_if_needed()
    counter = counter_collection.find_one({"_id": "taxId"})
    current_counter = counter["sequence_value"] if counter else 0

    # Find all existing ITxxx IDs in the database
    existing_ids = collection.find({"randomId": {"$regex": "^IT\\d+$"}}, {"randomId": 1})
    id_numbers = set()
    for item in existing_ids:
        try:
            if item["randomId"].startswith("IT"):
                num = int(item["randomId"][2:])
                id_numbers.add(num)
        except (ValueError, TypeError):
            continue

    # Include used_ids from CSV if provided
    if used_ids:
        for rid in used_ids:
            try:
                if rid.startswith("IT") and rid[2:].isdigit():
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
        {"_id": "taxId"},
        {"$set": {"sequence_value": next_number}},
        upsert=True
    )

    return f"IT{next_number:03d}"

@router.post("/reset-counter")
async def reset_sequence():
    """Reset the counter to 0. Next ID will be IT001."""
    set_counter_value(0)
    return {"message": "Counter reset successfully. Next ID will be IT001"}

@router.get("/export-csv")
async def export_all_tax_to_csv():
    """Export active taxes to a CSV file."""
    try:
        logger.info("Received request for /tax/export-csv")
        collection = get_tax_collection()
        records = list(collection.find({"status": "active"}, {'_id': 0}))
        
        if not records:
            logger.warning("No active taxes found for export")
            raise HTTPException(status_code=404, detail="No active taxes found to export")

        csv_stream = io.StringIO()
        fieldnames = list(header_mapping.keys())
        writer = csv.DictWriter(csv_stream, fieldnames=fieldnames)
        writer.writeheader()

        for record in records:
            writer.writerow({
                'Tax ID': record.get('randomId', ''),
                'Tax Name': record.get('taxName', ''),
                'Tax Percentage': str(record.get('taxPercentage', '')),
                'Status': record.get('status', '')
            })

        csv_stream.seek(0)
        filename = f"tax_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
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
        raise HTTPException(status_code=500, detail=f"Error exporting taxes: {str(e)}")

@router.post("/import-csv")
async def import_csv_data(file: UploadFile = File(...)):
    """Import taxes from a CSV file, preserving valid randomIds and handling duplicates."""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Invalid file format. Please upload a CSV file.")

    try:
        collection = get_tax_collection()
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

        required_fields = ['taxName', 'taxPercentage']
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

        failed = []
        rows = []
        seen_taxes = {}
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

            tax_key = (cleaned_row['taxName'].lower(), cleaned_row['taxPercentage'].lower())
            if tax_key[0] and tax_key[1]:
                if tax_key in seen_taxes:
                    seen_taxes[tax_key].append(idx)
                else:
                    seen_taxes[tax_key] = [idx]

            random_id = cleaned_row.get('randomId', '').strip()
            if random_id:
                if random_id in seen_ids:
                    seen_ids[random_id].append(idx)
                else:
                    seen_ids[random_id] = [idx]

        # Get existing taxes by randomId and taxName+taxPercentage
        existing_taxes_by_key = {}
        existing_taxes_by_id = {}
        for t in collection.find({}, {'taxName': 1, 'taxPercentage': 1, '_id': 1, 'randomId': 1, 'status': 1}):
            if not (t.get('taxName') and t.get('taxPercentage')):
                logger.warning(f"Skipping invalid document with _id: {t.get('_id')} - missing taxName or taxPercentage")
                continue
            existing_taxes_by_key[(t['taxName'].lower(), t['taxPercentage'].lower())] = t
            if t.get('randomId') and re.match(r"^IT\d+$", t['randomId']):
                existing_taxes_by_id[t['randomId']] = t

        used_ids = set(collection.distinct("randomId", {"randomId": {"$regex": "^IT\\d+$"}}))

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

                tax_name = row['taxName']
                tax_percentage = row['taxPercentage']
                tax_key = (tax_name.lower(), tax_percentage.lower())

                # Check for duplicate taxName+taxPercentage in CSV
                if tax_key in seen_taxes and len(seen_taxes[tax_key]) > 1:
                    failed.append({
                        "row": idx,
                        "data": row,
                        "error": f"Duplicate tax in CSV: taxName='{tax_name}', taxPercentage='{tax_percentage}'",
                        "missingFields": []
                    })
                    continue

                # Validate status
                status = row.get('status', 'active').lower()
                if status not in ['active', 'inactive']:
                    status = 'active'

                provided_id = row.get('randomId', '').strip()
                assigned_id = None

                # Handle randomId
                if provided_id:
                    if not (provided_id.startswith('IT') and provided_id[2:].isdigit()):
                        failed.append({
                            "row": idx,
                            "data": row,
                            "error": f"Invalid randomId format: '{provided_id}'. Must be 'IT' followed by digits.",
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
                    if provided_id in existing_taxes_by_id:
                        existing_tax = existing_taxes_by_id[provided_id]
                        # Update existing record
                        update_data = {
                            'taxName': tax_name,
                            'taxPercentage': tax_percentage,
                            'status': status
                        }
                        batch.append(UpdateOne(
                            {'_id': existing_tax['_id']},
                            {'$set': update_data}
                        ))
                        updated.append({
                            "row": idx,
                            "data": row,
                            "message": f"Tax updated for randomId: '{provided_id}'"
                        })
                        updated_count += 1
                        max_id_number = max(max_id_number, int(provided_id[2:]))
                        # Update existing_taxes_by_key to prevent duplicate name errors
                        if (existing_tax['taxName'].lower(), existing_tax['taxPercentage'].lower()) != tax_key:
                            del existing_taxes_by_key[(existing_tax['taxName'].lower(), existing_tax['taxPercentage'].lower())]
                            existing_taxes_by_key[tax_key] = existing_tax
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

                # Check for duplicate taxName+taxPercentage in the database
                if tax_key in existing_taxes_by_key:
                    existing_tax = existing_taxes_by_key[tax_key]
                    if existing_tax['randomId'] != assigned_id:
                        failed.append({
                            "row": idx,
                            "data": row,
                            "error": f"Tax with taxName='{tax_name}', taxPercentage='{tax_percentage}' already exists with randomId: '{existing_tax['randomId']}'",
                            "missingFields": []
                        })
                        continue

                # Create new record
                tax_data = {
                    'taxName': tax_name,
                    'taxPercentage': tax_percentage,
                    'status': status,
                    'randomId': assigned_id
                }

                batch.append(InsertOne(tax_data))
                successful.append({
                    "row": idx,
                    "data": row,
                    "assignedId": assigned_id
                })
                existing_taxes_by_key[tax_key] = tax_data
                existing_taxes_by_id[assigned_id] = tax_data
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
async def create_tax(tax: taxPost):
    # Check if the collection is empty
    if get_tax_collection().count_documents({}) == 0:
        reset_counter()

    # Generate randomId
    random_id = generate_random_id()

    # Prepare data including randomId
    new_tax_data = tax.dict()
    new_tax_data['randomId'] = random_id
    new_tax_data['status'] = "active"

    # Insert into MongoDB
    result = get_tax_collection().insert_one(new_tax_data)
    return str(result.inserted_id)

@router.get("/", response_model=List[tax])
async def get_all_tax():
    try:
        itemtax = list(get_tax_collection().find())
        formatted_tax = []
        for taxs in itemtax:
            for key, value in taxs.items():
                taxs[key] = convert_to_string_or_none(value)
            taxs["taxId"] = str(taxs["_id"])
            formatted_tax.append(tax(**taxs))
        return formatted_tax
    except Exception as e:
        print(f"Error fetching taxs: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/{tax_id}", response_model=tax)
async def get_tax_by_id(tax_id: str):
    try:
        tax_data = get_tax_collection().find_one({"_id": ObjectId(tax_id)})
        if tax_data:
            tax_data["taxId"] = str(tax_data["_id"])
            return tax(**tax_data)
        else:
            raise HTTPException(status_code=404, detail="tax not found")
    except Exception as e:
        print(f"Error fetching tax by ID: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.patch("/{tax_id}")
async def update_tax(tax_id: str, tax: taxPost):
    updated_tax = tax.dict(exclude_unset=True)  # exclude_unset=True prevents sending None values to MongoDB
    result = get_tax_collection().update_one({"_id": ObjectId(tax_id)}, {"$set": updated_tax})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="tax not found")
    return {"message": "tax updated successfully"}

@router.delete("/{tax_id}")
async def delete_tax(tax_id: str):
    result = get_tax_collection().delete_one({"_id": ObjectId(tax_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="tax not found")
    return {"message": "tax deleted successfully"}
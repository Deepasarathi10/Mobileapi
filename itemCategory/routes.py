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
from pydantic import BaseModel
from pymongo import InsertOne, UpdateOne

from .models import Category, CategoryPost
from .utils import get_category_collection, convert_to_string_or_none

router = APIRouter()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Header mapping for user-friendly CSV columns
header_mapping = {
    'Item Category ID': 'randomId',
    'Item Category': 'categoryName',
    'Subcategories': 'subCategory',
    'Status': 'status',
    'Created Date': 'createdDate',
    'Updated Date': 'lastUpdatedDate'
}

def get_localized_datetime():
    """Get current UTC datetime adjusted from IST."""
    ist = pytz.timezone("Asia/Kolkata")
    return datetime.now(ist).astimezone(pytz.UTC)

def set_counter_value(value: int, counter_id: str = "categoryId"):
    """Set the counter value in the database."""
    counter_collection = get_category_collection().database["counters"]
    counter_collection.update_one(
        {"_id": counter_id},
        {"$set": {"sequence_value": value}},
        upsert=True
    )

def get_current_counter_value(counter_id: str = "categoryId"):
    """Get the current counter value from the database."""
    counter_collection = get_category_collection().database["counters"]
    counter = counter_collection.find_one({"_id": counter_id})
    return counter["sequence_value"] if counter else 0

def initialize_counter_if_needed(counter_id: str = "categoryId"):
    """Initialize counter to the highest existing ID number (ICxxx)."""
    collection = get_category_collection()
    counter_collection = collection.database["counters"]

    highest_item = collection.find_one(
        {"randomId": {"$regex": "^IC\\d+$"}},
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
    """Generate an ICxxx ID, filling gaps in the sequence, considering used_ids."""
    collection = get_category_collection()
    counter_collection = collection.database["counters"]

    initialize_counter_if_needed()
    counter = counter_collection.find_one({"_id": "categoryId"})
    current_counter = counter["sequence_value"] if counter else 0

    # Find all existing ICxxx IDs in the database
    existing_ids = collection.find({"randomId": {"$regex": "^IC\\d+$"}}, {"randomId": 1})
    id_numbers = set()
    for item in existing_ids:
        try:
            if item["randomId"].startswith("IC"):
                num = int(item["randomId"][2:])
                id_numbers.add(num)
        except (ValueError, TypeError):
            continue

    # Include used_ids from CSV if provided
    if used_ids:
        for rid in used_ids:
            try:
                if rid.startswith("IC") and rid[2:].isdigit():
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
        {"_id": "categoryId"},
        {"$set": {"sequence_value": next_number}},
        upsert=True
    )

    return f"IC{next_number:03d}"

@router.post("/reset-counter")
async def reset_sequence():
    """Reset the counter to 0. Next ID will be IC001."""
    set_counter_value(0)
    return {"message": "Counter reset successfully. Next ID will be IC001"}

@router.get("/export-csv")
async def export_all_categories_to_csv():
    """Export active categories to a CSV file."""
    try:
        logger.info("Received request for /categories/export-csv")
        collection = get_category_collection()
        records = list(collection.find({"status": "active"}, {'_id': 0}))
        
        if not records:
            logger.warning("No active categories found for export")
            raise HTTPException(status_code=404, detail="No active categories found to export")

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

            subcategories = record.get('subCategory', [])
            if isinstance(subcategories, list):
                subcategories_str = ",".join(subcategories)
            else:
                subcategories_str = str(subcategories)

            writer.writerow({
                'Item Category ID': record.get('randomId', ''),
                'Item Category': record.get('categoryName', ''),
                'Subcategories': subcategories_str,
                'Status': record.get('status', ''),
                'Created Date': created_str,
                'Updated Date': updated_str
            })

        csv_stream.seek(0)
        filename = f"categories_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
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
        raise HTTPException(status_code=500, detail=f"Error exporting categories: {str(e)}")



@router.post("/import-csv")
async def import_csv_data(file: UploadFile = File(...)):
    """Import categories from a CSV file, preserving valid randomIds and handling duplicates."""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Invalid file format. Please upload a CSV file.")

    try:
        collection = get_category_collection()
        current_datetime = get_localized_datetime()

        content = await file.read()
        decoded = content.decode('utf-8-sig', errors='replace')
        csv_reader = csv.DictReader(io.StringIO(decoded))

        headers = [header_mapping.get(header.strip(), header.strip()) for header in csv_reader.fieldnames or []]
        csv_reader.fieldnames = headers

        required_fields = ['categoryName']
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

            name = cleaned_row.get('categoryName', '').lower()
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

        # Get existing categories by randomId and categoryName
        existing_categories_by_name = {g['categoryName'].lower(): g for g in collection.find({}, {'categoryName': 1, '_id': 1, 'randomId': 1, 'status': 1})}
        existing_categories_by_id = {g['randomId']: g for g in collection.find({"randomId": {"$regex": "^IC\\d+$"}}, {'categoryName': 1, '_id': 1, 'randomId': 1, 'status': 1})}
        used_ids = set(collection.distinct("randomId", {"randomId": {"$regex": "^IC\\d+$"}}))

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

                category_name = row.get('categoryName').strip()
                # Check for duplicate categoryName in CSV or database
                if category_name.lower() in seen_names and len(seen_names[category_name.lower()]) > 1:
                    duplicates.append(category_name)
                    logger.info(f"Category '{category_name}' is duplicated in CSV, skipping row {idx}.")
                    continue

                if category_name.lower() in existing_categories_by_name:
                    existing_category = existing_categories_by_name[category_name.lower()]
                    duplicates.append(category_name)
                    logger.info(f"Category '{category_name}' already exists with randomId: '{existing_category['randomId']}', skipping row {idx}.")
                    continue

                # Validate status
                status = row.get('status', 'active').lower()
                if status not in ['active', 'inactive']:
                    status = 'active'

                # Parse subcategories
                subcategories = []
                if row.get('subCategory'):
                    subcategories = [s.strip() for s in row['subCategory'].split(',') if s.strip()]
                if not subcategories:
                    subcategories = []

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
                    if not (provided_id.startswith('IC') and provided_id[2:].isdigit()):
                        failed.append({
                            "row": idx,
                            "data": row,
                            "error": f"Invalid randomId format: '{provided_id}'. Must be 'IC' followed by digits.",
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
                    if provided_id in existing_categories_by_id:
                        existing_category = existing_categories_by_id[provided_id]
                        # Update existing record
                        update_data = {
                            'categoryName': category_name,
                            'subCategory': subcategories,
                            'status': status,
                            'lastUpdatedDate': last_updated_date
                        }
                        if row.get('createdDate'):
                            update_data['createdDate'] = created_date
                        batch.append(UpdateOne(
                            {'_id': existing_category['_id']},
                            {'$set': update_data}
                        ))
                        updated.append({
                            "row": idx,
                            "data": row,
                            "message": f"Item Category updated for randomId: '{provided_id}'"
                        })
                        max_id_number = max(max_id_number, int(provided_id[2:]))
                        # Update existing_categories_by_name to prevent duplicate name errors
                        if existing_category['categoryName'].lower() != category_name.lower():
                            del existing_categories_by_name[existing_category['categoryName'].lower()]
                            existing_categories_by_name[category_name.lower()] = existing_category
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
                category_data = {
                    'categoryName': category_name,
                    'subCategory': subcategories,
                    'randomId': assigned_id,
                    'status': status,
                    'createdDate': current_datetime,
                    'lastUpdatedDate': current_datetime
                }

                batch.append(InsertOne(category_data))
                inserted.append(assigned_id)
                existing_categories_by_name[category_name.lower()] = category_data
                existing_categories_by_id[assigned_id] = category_data
                logger.info(f"Inserted category {category_name} with ID {assigned_id}")

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
            "message": f"Import completed: {len(inserted)} new categories, {len(duplicates)} duplicates skipped, {len(updated)} updated.",
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
async def create_category(category: CategoryPost):
    """Create a new category with a sequential ID."""
    # Ensure subCategory is a list
    if category.subCategory is None:
        category.subCategory = []

    current_datetime = get_localized_datetime()
    initialize_counter_if_needed()
    random_id = generate_sequential_id()

    # Prepare data including randomId
    new_category_data = category.dict()
    new_category_data['randomId'] = random_id
    new_category_data['status'] = "active"
    new_category_data['createdDate'] = current_datetime
    new_category_data['lastUpdatedDate'] = current_datetime

    # Insert into MongoDB
    try:
        result = get_category_collection().insert_one(new_category_data)
        return str(result.inserted_id)
    except Exception as e:
        logger.error(f"Error creating category: {e}")
        raise HTTPException(status_code=500, detail="Failed to create category")

@router.get("/", response_model=List[Category])
async def get_all_category():
    """Get all categories."""
    try:
        categories = list(get_category_collection().find())
        formatted_categories = []
        for cat in categories:
            for key, value in cat.items():
                cat[key] = convert_to_string_or_none(value)
            cat["categoryId"] = str(cat["_id"])
            if isinstance(cat.get("subCategory"), str):
                cat["subCategory"] = [cat["subCategory"]]  # Convert string to list
            elif cat.get("subCategory") is None:
                cat["subCategory"] = []  # Ensure it's a list
            formatted_categories.append(Category(**cat))
        return formatted_categories
    except Exception as e:
        logger.error(f"Error fetching categories: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/{category_id}", response_model=Category)
async def get_category_by_id(category_id: str):
    """Get a specific category by ID."""
    try:
        category = get_category_collection().find_one({"_id": ObjectId(category_id)})
        if category:
            for key, value in category.items():
                category[key] = convert_to_string_or_none(value)
            category["categoryId"] = str(category["_id"])
            if isinstance(category.get("subCategory"), str):
                category["subCategory"] = [category["subCategory"]]  # Convert string to list
            elif category.get("subCategory") is None:
                category["subCategory"] = []  # Ensure it's a list
            return Category(**category)
        else:
            raise HTTPException(status_code=404, detail="Category not found")
    except Exception as e:
        logger.error(f"Error fetching category by ID: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.patch("/{category_id}")
async def update_category(category_id: str, category: CategoryPost):
    """Update specific fields of an existing category."""
    try:
        current_datetime = get_localized_datetime()
        # Ensure subCategory is a list
        if category.subCategory is None:
            category.subCategory = []

        updated_category = category.dict(exclude_unset=True)  # exclude_unset=True prevents sending None values to MongoDB
        updated_category['lastUpdatedDate'] = current_datetime

        result = get_category_collection().update_one(
            {"_id": ObjectId(category_id)},
            {"$set": updated_category}
        )
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Category not found")
        return {"message": "Category updated successfully"}
    except Exception as e:
        logger.error(f"Error updating category: {e}")
        raise HTTPException(status_code=500, detail="Failed to update category")

@router.patch("/{category_id}/status", response_model=Category)
async def patch_category_status(category_id: str, status: str):
    """Update the status of an existing category."""
    try:
        existing_category = get_category_collection().find_one({"_id": ObjectId(category_id)})
        if not existing_category:
            raise HTTPException(status_code=404, detail="Category not found")

        if status not in ["active", "inactive"]:
            raise HTTPException(status_code=400, detail="Invalid status value")

        updated_fields = {
            "status": status,
            "lastUpdatedDate": get_localized_datetime()
        }
        result = get_category_collection().update_one(
            {"_id": ObjectId(category_id)},
            {"$set": updated_fields}
        )
        if result.modified_count == 0:
            raise HTTPException(status_code=500, detail="Failed to update category status")

        updated_category = get_category_collection().find_one({"_id": ObjectId(category_id)})
        for key, value in updated_category.items():
            updated_category[key] = convert_to_string_or_none(value)
        updated_category["categoryId"] = str(updated_category["_id"])
        if isinstance(updated_category.get("subCategory"), str):
            updated_category["subCategory"] = [updated_category["subCategory"]]  # Convert string to list
        elif updated_category.get("subCategory") is None:
            updated_category["subCategory"] = []  # Ensure it's a list
        return Category(**updated_category)
    except Exception as e:
        logger.error(f"Error patching category status: {e}")
        raise HTTPException(status_code=500, detail="Failed to patch category status")

@router.delete("/{category_id}")
async def delete_category(category_id: str):
    """Delete a category."""
    try:
        result = get_category_collection().delete_one({"_id": ObjectId(category_id)})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Category not found")
        return {"message": "Category deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting category: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete category")
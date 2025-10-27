import logging
import traceback
from bson import ObjectId
from fastapi import APIRouter, HTTPException, File, UploadFile
from typing import List
from bson.errors import InvalidId
from pymongo import DESCENDING, InsertOne, UpdateOne
from fastapi.responses import StreamingResponse
import pytz
import csv
import io
import re
from datetime import datetime
from Location.models import CityResponse
from country.utils import get_country_collection

from .models import WareHousePost, WareHouse
from .utils import get_warehouse_collection

router = APIRouter()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Header mapping for user-friendly CSV columns
header_mapping = {
    'Warehouse ID': 'randomId',
    'Warehouse Name': 'wareHouseName',
    'Alias Name': 'aliasName',
    'Status': 'status',
    'Address': 'address',
    'Country': 'country',
    'State': 'state',
    'City': 'city',
    'Postal Code': 'postalCode',
    'Phone Number': 'phoneNumber',
    'Email': 'email',
    'Latitude': 'latitude',
    'Longitude': 'longitude',
    'Description': 'description',
    'Opening Hours': 'openingHours',
    'Closing Hours': 'closingHours',
    'Manager Name': 'managerName',
    'Manager Contact': 'managerContact',
    'Created Date': 'createdDate',
    'Last Updated Date': 'lastUpdatedDate',
    'Created By': 'createdBy'
}

def get_localized_datetime():
    """Get current UTC datetime adjusted from IST."""
    ist = pytz.timezone("Asia/Kolkata")
    return datetime.now(ist).astimezone(pytz.UTC)

def set_counter_value(value: int, counter_id: str = "warehouseId"):
    """Set the counter value in the database."""
    counter_collection = get_warehouse_collection().database["counters"]
    counter_collection.update_one(
        {"_id": counter_id},
        {"$set": {"sequence_value": value}},
        upsert=True
    )

def get_current_counter_value(counter_id: str = "warehouseId"):
    """Get the current counter value from the database."""
    counter_collection = get_warehouse_collection().database["counters"]
    counter = counter_collection.find_one({"_id": counter_id})
    return counter["sequence_value"] if counter else 0

def initialize_counter_if_needed(counter_id: str = "warehouseId"):
    """Initialize counter to the highest existing ID number (WH-xxx)."""
    collection = get_warehouse_collection()
    counter_collection = collection.database["counters"]

    highest_item = collection.find_one(
        {"randomId": {"$regex": "^WH-\\d+$"}},
        sort=[("randomId", -1)]
    )

    if highest_item:
        try:
            last_number = int(highest_item["randomId"].split("-")[-1])
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
    counter_collection = get_warehouse_collection().database["counters"]
    counter = counter_collection.find_one_and_update(
        {"_id": "warehouseId"},
        {"$inc": {"sequence_value": 1}},
        upsert=True,
        return_document=True
    )
    return counter["sequence_value"]

def generate_random_id(used_ids: set = None):
    """Generate a WH-xxx ID, filling gaps in the sequence, considering used_ids."""
    collection = get_warehouse_collection()
    counter_collection = collection.database["counters"]

    initialize_counter_if_needed()
    counter = counter_collection.find_one({"_id": "warehouseId"})
    current_counter = counter["sequence_value"] if counter else 0

    # Find all existing WH-xxx IDs in the database
    existing_ids = collection.find({"randomId": {"$regex": "^WH-\\d+$"}}, {"randomId": 1})
    id_numbers = set()
    for item in existing_ids:
        try:
            if item["randomId"].startswith("WH-"):
                num = int(item["randomId"].split("-")[-1])
                id_numbers.add(num)
        except (ValueError, TypeError):
            continue

    # Include used_ids from CSV if provided
    if used_ids:
        for rid in used_ids:
            try:
                if rid.startswith("WH-") and rid[3:].isdigit():
                    num = int(rid[3:])
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
        {"_id": "warehouseId"},
        {"$set": {"sequence_value": next_number}},
        upsert=True
    )

    return f"WH-{next_number:03d}"

@router.get("/export-csv")
async def export_all_warehouses_to_csv():
    """Export active warehouses to a CSV file."""
    try:
        logger.info("Received request for /warehouses/export-csv")
        collection = get_warehouse_collection()
        records = list(collection.find({"status": 1}, {'_id': 0}))

        if not records:
            logger.warning("No active warehouses found for export")
            raise HTTPException(status_code=404, detail="No active warehouses found to export")

        csv_stream = io.StringIO()
        fieldnames = list(header_mapping.keys())
        writer = csv.DictWriter(csv_stream, fieldnames=fieldnames)
        writer.writeheader()

        for record in records:
            writer.writerow({
                'Warehouse ID': record.get('randomId', ''),
                'Warehouse Name': record.get('wareHouseName', ''),
                'Alias Name': record.get('aliasName', ''),
                'Status': str(record.get('status', '')),
                'Address': record.get('address', ''),
                'Country': record.get('country', ''),
                'State': record.get('state', ''),
                'City': record.get('city', ''),
                'Postal Code': str(record.get('postalCode', '')),
                'Phone Number': record.get('phoneNumber', ''),
                'Email': record.get('email', ''),
                'Latitude': str(record.get('latitude', '')),
                'Longitude': str(record.get('longitude', '')),
                'Description': record.get('description', ''),
                'Opening Hours': record.get('openingHours', '').isoformat() if record.get('openingHours') else '',
                'Closing Hours': record.get('closingHours', '').isoformat() if record.get('closingHours') else '',
                'Manager Name': record.get('managerName', ''),
                'Manager Contact': record.get('managerContact', ''),
                'Created Date': record.get('createdDate', '').isoformat() if record.get('createdDate') else '',
                'Last Updated Date': record.get('lastUpdatedDate', '').isoformat() if record.get('lastUpdatedDate') else '',
                'Created By': record.get('createdBy', '')
            })

        csv_stream.seek(0)
        filename = f"warehouses_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
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
        raise HTTPException(status_code=500, detail=f"Error exporting warehouses: {str(e)}")




@router.post("/import-csv")
async def import_csv_data(file: UploadFile = File(...)):
    """Import warehouses from a CSV file, preserving valid randomIds and handling duplicates."""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Invalid file format. Please upload a CSV file.")

    try:
        collection = get_warehouse_collection()
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

        required_fields = ['wareHouseName']
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

        rows = []
        seen_names = {}
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

            name_key = cleaned_row.get('wareHouseName', '').lower()
            if name_key:
                if name_key in seen_names:
                    seen_names[name_key].append(idx)
                else:
                    seen_names[name_key] = [idx]

            random_id = cleaned_row.get('randomId', '').strip()
            if random_id:
                if random_id in seen_ids:
                    seen_ids[random_id].append(idx)
                else:
                    seen_ids[random_id] = [idx]

        # Get existing warehouses by wareHouseName and randomId
        existing_warehouses_by_name = {wh['wareHouseName'].lower(): wh for wh in collection.find({}, {'wareHouseName': 1, '_id': 1, 'randomId': 1, 'status': 1})}
        existing_warehouses_by_id = {wh['randomId']: wh for wh in collection.find({"randomId": {"$regex": "^WH-\\d+$"}}, {'wareHouseName': 1, '_id': 1, 'randomId': 1, 'status': 1})}
        used_ids = set(collection.distinct("randomId", {"randomId": {"$regex": "^WH-\\d+$"}}))

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
                        "error": f"Missing required fields: {', '.join([header_mapping.get(field, field) for field in missing_fields])}",
                        "missingFields": [header_mapping.get(field, field) for field in missing_fields]
                    })
                    continue

                warehouse_name = row.get('wareHouseName').strip()
                name_key = warehouse_name.lower()

                # Check for duplicate wareHouseName in CSV or database
                if name_key in seen_names and len(seen_names[name_key]) > 1:
                    duplicates.append(warehouse_name)
                    logger.info(f"Warehouse '{warehouse_name}' is duplicated in CSV, skipping row {idx}.")
                    continue

                if name_key in existing_warehouses_by_name:
                    existing_warehouse = existing_warehouses_by_name[name_key]
                    duplicates.append(warehouse_name)
                    logger.info(f"Warehouse '{warehouse_name}' already exists with randomId: '{existing_warehouse['randomId']}', skipping row {idx}.")
                    continue

                # Validate status
                status = row.get('status', '1')
                try:
                    status = int(status)
                    if status not in [0, 1]:
                        status = 1
                except (ValueError, TypeError):
                    status = 1

                # Parse numeric fields
                latitude = row.get('latitude', None)
                try:
                    latitude = float(latitude) if latitude else None
                except (ValueError, TypeError):
                    latitude = None

                longitude = row.get('longitude', None)
                try:
                    longitude = float(longitude) if longitude else None
                except (ValueError, TypeError):
                    longitude = None

                postal_code = row.get('postalCode', None)
                try:
                    postal_code = int(postal_code) if postal_code else None
                except (ValueError, TypeError):
                    postal_code = None

                # Parse datetime fields
                opening_hours = row.get('openingHours', None)
                try:
                    opening_hours = datetime.fromisoformat(opening_hours) if opening_hours else current_datetime
                except (ValueError, TypeError):
                    opening_hours = current_datetime

                closing_hours = row.get('closingHours', None)
                try:
                    closing_hours = datetime.fromisoformat(closing_hours) if closing_hours else current_datetime
                except (ValueError, TypeError):
                    closing_hours = current_datetime

                created_date = row.get('createdDate', None)
                try:
                    created_date = datetime.fromisoformat(created_date) if created_date else current_datetime
                except (ValueError, TypeError):
                    created_date = current_datetime

                last_updated_date = row.get('lastUpdatedDate', None)
                try:
                    last_updated_date = datetime.fromisoformat(last_updated_date) if last_updated_date else current_datetime
                except (ValueError, TypeError):
                    last_updated_date = current_datetime

                provided_id = row.get('randomId', '').strip()
                assigned_id = None

                # Handle randomId
                if provided_id:
                    if not (provided_id.startswith('WH-') and provided_id[3:].isdigit()):
                        failed.append({
                            "row": idx,
                            "data": row,
                            "error": f"Invalid randomId format: '{provided_id}'. Must be 'WH-' followed by digits.",
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
                    if provided_id in existing_warehouses_by_id:
                        existing_warehouse = existing_warehouses_by_id[provided_id]
                        # Update existing record
                        update_data = {
                            'wareHouseName': warehouse_name,
                            'aliasName': row.get('aliasName', ''),
                            'status': status,
                            'address': row.get('address', ''),
                            'country': row.get('country', ''),
                            'state': row.get('state', ''),
                            'city': row.get('city', ''),
                            'postalCode': postal_code,
                            'phoneNumber': row.get('phoneNumber', ''),
                            'email': row.get('email', ''),
                            'latitude': latitude,
                            'longitude': longitude,
                            'description': row.get('description', ''),
                            'openingHours': opening_hours,
                            'closingHours': closing_hours,
                            'managerName': row.get('managerName', ''),
                            'managerContact': row.get('managerContact', ''),
                            'createdDate': created_date,
                            'lastUpdatedDate': last_updated_date,
                            'createdBy': row.get('createdBy', '')
                        }
                        batch.append(UpdateOne(
                            {'_id': existing_warehouse['_id']},
                            {'$set': update_data}
                        ))
                        updated.append({
                            "row": idx,
                            "data": row,
                            "message": f"Warehouse updated for randomId: '{provided_id}'"
                        })
                        max_id_number = max(max_id_number, int(provided_id[3:]))
                        # Update existing_warehouses_by_name to prevent duplicate name errors
                        if existing_warehouse['wareHouseName'].lower() != name_key:
                            del existing_warehouses_by_name[existing_warehouse['wareHouseName'].lower()]
                            existing_warehouses_by_name[name_key] = existing_warehouse
                        continue
                    # Valid, unused randomId from CSV
                    assigned_id = provided_id
                    used_ids.add(assigned_id)
                    max_id_number = max(max_id_number, int(assigned_id[3:]))
                else:
                    # Generate sequential ID for rows without a valid randomId
                    assigned_id = generate_random_id(used_ids)
                    used_ids.add(assigned_id)
                    max_id_number = max(max_id_number, int(assigned_id[3:]))

                # Create new record
                warehouse_data = {
                    'wareHouseName': warehouse_name,
                    'aliasName': row.get('aliasName', ''),
                    'status': status,
                    'randomId': assigned_id,
                    'address': row.get('address', ''),
                    'country': row.get('country', ''),
                    'state': row.get('state', ''),
                    'city': row.get('city', ''),
                    'postalCode': postal_code,
                    'phoneNumber': row.get('phoneNumber', ''),
                    'email': row.get('email', ''),
                    'latitude': latitude,
                    'longitude': longitude,
                    'description': row.get('description', ''),
                    'openingHours': opening_hours,
                    'closingHours': closing_hours,
                    'managerName': row.get('managerName', ''),
                    'managerContact': row.get('managerContact', ''),
                    'createdDate': created_date,
                    'lastUpdatedDate': last_updated_date,
                    'createdBy': row.get('createdBy', '')
                }

                batch.append(InsertOne(warehouse_data))
                inserted.append(assigned_id)
                existing_warehouses_by_name[name_key] = warehouse_data
                existing_warehouses_by_id[assigned_id] = warehouse_data
                logger.info(f"Inserted warehouse {warehouse_name} with ID {assigned_id}")

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
            "message": f"Import completed: {len(inserted)} new warehouses, {len(duplicates)} duplicates skipped, {len(updated)} updated.",
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
    





# Existing endpoints (unchanged)
def get_next_random_id():
    last_location = get_warehouse_collection().find_one(
        {"randomId": {"$exists": True}}, 
        sort=[("createdDate", DESCENDING)]
    )
    
    if last_location and "randomId" in last_location:
        last_random_id = last_location["randomId"]
        try:
            last_number = int(last_random_id.split("-")[-1]) if last_random_id else 0
        except (ValueError, IndexError):
            last_number = 0
    else:
        last_number = 0

    next_number = last_number + 1
    return f"WH-{next_number:03d}"


@router.get("/", response_model=List[WareHouse])
async def get_all_warehouses():
    try:
        warehouse_collection = get_warehouse_collection()
        warehouses = []
        for warehouse in warehouse_collection.find():
            warehouse["wareHouseId"] = str(warehouse.pop("_id"))
            warehouses.append(WareHouse(**warehouse))
        return warehouses
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching warehouses: {str(e)}")


  
    
@router.post("/warehouse", response_model=WareHouse)
async def create_location(location: WareHousePost):
    try:
        print("Received location data:", location)

        location_data = location.dict(exclude_unset=True)

        # Fill missing fields
        location_data["createdDate"] = datetime.utcnow()
        location_data["lastUpdatedDate"] = datetime.utcnow()
        location_data["openingHours"] = datetime.utcnow()
        location_data["closingHours"] = datetime.utcnow()
        location_data["randomId"] = get_next_random_id()

        # Insert into MongoDB
        result = get_warehouse_collection().insert_one(location_data)

        # Prepare created_location for response
        created_location = location_data.copy()
        created_location["wareHouseId"] = str(result.inserted_id)
        created_location.pop("_id", None)  # 🚨 Remove MongoDB _id field

        return WareHouse(**created_location)

    except Exception as e:
        print("Error:", str(e))
        raise HTTPException(status_code=500, detail=f"Failed to create warehouse: {str(e)}")


@router.patch("/warehouse/{location_id}", response_model=WareHouse)
async def update_location(location_id: str, location: WareHousePost):
    try:
        location_data = location.dict(exclude_unset=True)
        location_data["lastUpdatedDate"] = datetime.utcnow()

        obj_id = ObjectId(location_id)

        result = get_warehouse_collection().update_one({"_id": obj_id}, {"$set": location_data})
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Location not found")

        updated_location = get_warehouse_collection().find_one({"_id": obj_id})

        if not updated_location:
            raise HTTPException(status_code=404, detail="Updated location not found")

        # ✅ Fix here: rename correctly
        updated_location["wareHouseId"] = str(updated_location["_id"])
        del updated_location["_id"]

        return WareHouse(**updated_location)

    except Exception as e:
        print(f"Error updating location: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update location: {str(e)}")
 

@router.get("/warehouse/{warehouse_id}", response_model=WareHouse)
async def get_warehouse_by_id(warehouse_id: str):
    try:
        # Validate ID format
        try:
            obj_id = ObjectId(warehouse_id)
        except InvalidId:
            raise HTTPException(
                status_code=400,
                detail="Invalid warehouse ID format - must be 24-character hex string"
            )

        warehouse = get_warehouse_collection().find_one({"_id": obj_id})
        if not warehouse:
            raise HTTPException(
                status_code=404,
                detail=f"Warehouse with ID {warehouse_id} not found"
            )

        warehouse["wareHouseId"] = str(warehouse.pop("_id"))
        return WareHouse(**warehouse)
    except HTTPException:
        raise  # Re-raise the HTTP exceptions we created
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


# Deactivate a location by ID (simulated deactivation by updating the 'status' field)
@router.patch("/location/{location_id}/deactivate")
async def deactivate_location(location_id: str):
    try:
        # print(f"Deactivate request for ID: {location_id}")  # 🛠 debug print
        result = get_warehouse_collection().update_one(
            {"_id": ObjectId(location_id)}, 
            {"$set": {"status": 0}}  # ✅ you wrote 'inactive' not 'deactivate'
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Location not found")
        return {"message": "Location deactivated successfully"}
    except Exception as e:
        print(traceback.format_exc())  # 👈 full error log in console
        raise HTTPException(status_code=500, detail=str(e))  # 👈 send real error

@router.patch("/location/{location_id}/activate")
async def activate_location(location_id: str):
    try:
        result = get_warehouse_collection().update_one(
            {"_id": ObjectId(location_id)},  # ✅ Converted here
            {"$set": {"status": 1}}
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Location not found")
        return {"message": "Location activated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to activate location")



@router.get("/countries", response_model=List[str])
async def get_countries():
    try:
        # Only fetch COUNTRY field
        countries_cursor = get_country_collection().find({}, {"_id": 0, "COUNTRY": 1})
        countries = [country["COUNTRY"] for country in countries_cursor]    
        
        # Make it unique
        unique_countries = list(set(countries))
        
        # (Optional) Sort the list alphabetically
        unique_countries.sort()
        
        return unique_countries
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching countries: {str(e)}")


# Fetch states for a specific country
@router.get("/countries/{country_code}/states", response_model=List[str])
async def get_states_for_country(country_code: str):
    try:
        # Fetch the locations that match the given country code
        country_data = get_country_collection().find({"COUNTRY": country_code})
        
        if not country_data:
            raise HTTPException(status_code=404, detail="Country not found")
        
        states = set()  # Using a set to avoid duplicates
        for location in country_data:
            states.add(location["STATE"])
        
        return list(states)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error fetching states")


from fastapi import Query

@router.get("/countries/{country_code}/states/{state_name}/cities", response_model=List[str])
async def get_cities_for_state(
    country_code: str,
    state_name: str,
#     skip: int = Query(0, ge=0),
#     limit: int = Query(50, ge=1, le=100)  # You can adjust max limit if needed
):
    try:
        cursor = get_country_collection().find(
            {
                "COUNTRY": {"$regex": f"^{country_code}$", "$options": "i"},
                "STATE": {"$regex": f"^{state_name}$", "$options": "i"}
            },
            {"DISTRICT": 1, "_id": 0}
        )

        districts = set()
        for location in cursor:
            district = location.get("DISTRICT")
            if district:
                districts.add(district.strip())

        return sorted(list(districts))  # Sorting optional

    except Exception as e:
        logger.error(f"Error fetching cities for {country_code}, {state_name}: {str(e)}")
        logger.error(f"Stack Trace: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Error fetching cities")

@router.get("/countries/{country_code}/states/{state_name}/cities/{district}/details", response_model=CityResponse)
async def get_city_details(country_code: str, state_name: str, district: str):
    try:
        location = get_country_collection().find_one(
            {
                "COUNTRY": country_code,
                "STATE": state_name,
                "DISTRICT": district,
            },
            {
                "POSTAL_CODE": 1,
                "LATITUDE": 1,
                "LONGITUDE": 1,
            #     "_id": 0
            }
        )

        if not location:
            raise HTTPException(status_code=404, detail="Location details not found")

        return {
            "POSTAL_CODE": location.get("POSTAL_CODE", ""),
            "LATITUDE": location.get("LATITUDE", ""),
            "LONGITUDE": location.get("LONGITUDE", "")
        }

    except Exception as e:
        logger.error(f"Error fetching details for city {district}: {str(e)}")
        logger.error(f"Stack Trace: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Error fetching city details")  


@router.get("/warehouse/{warehouse_id}", response_model=WareHouse)
async def get_warehouse_by_id(warehouse_id: str):
    try:
        # Validate ObjectId
        if not ObjectId.is_valid(warehouse_id):
            raise HTTPException(status_code=400, detail="Invalid warehouse ID format")

        _id = ObjectId(warehouse_id)
        warehouse = get_warehouse_collection().find_one({"_id": _id})

        if warehouse is None:
            raise HTTPException(status_code=404, detail="Warehouse not found")

        # Handle _id
        warehouse["wareHouseId"] = str(warehouse["_id"])  # 👈 Set new field
        del warehouse["_id"]  # 👈 Remove _id because Pydantic cannot parse it

        return WareHouse(**warehouse)

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch warehouse: {str(e)}")
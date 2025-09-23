import logging
import traceback
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from typing import List, Dict, Any
from pymongo import DESCENDING
from .models import Location, LocationPost, CityResponse, Country
from datetime import datetime
from country.utils import get_country_collection
from .utils import get_location_collection
import pandas as pd
from io import StringIO, BytesIO
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ValidationError

router = APIRouter()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ImportResult model for CSV import response
class ImportResult(BaseModel):
    message: str
    inserted_count: int
    updated_count: int
    errorCount: int
    successful: List[Dict[str, Any]]
    updated: List[Dict[str, Any]]
    failed: List[Dict[str, Any]]

def get_next_random_id():
    # Find the last inserted document with a randomId
    last_location = get_location_collection().find_one(
        {"randomId": {"$exists": True}}, 
        sort=[("createdDate", DESCENDING)]
    )
    
    if last_location and "randomId" in last_location:
        last_random_id = last_location["randomId"]
        try:
            # Check if randomId is valid and properly formatted
            last_number = int(last_random_id.split("-")[-1]) if last_random_id else 0
        except (ValueError, IndexError):
            last_number = 0
    else:
        last_number = 0

    next_number = last_number + 1
    # Format it with leading zeros, like LOC-001
    return f"LOC-{next_number:03d}"


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

    

@router.get("/locations", response_model=List[Location])
async def get_all_locations():
    try:
        locations_cursor = get_location_collection().find()
        locations = []
        for location in locations_cursor:
            location["branchId"] = str(location["_id"])  # Ensure 'id' field matches your Location model
            locations.append(Location(**location))
        return locations
    except Exception as e:
        logger.error(f"Error fetching all locations: {str(e)}")
        logger.error(f"Stack Trace: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Failed to fetch locations")    
    
@router.post("/location", response_model=Location)
async def create_location(location: LocationPost):
    try:
        print("Received location data:", location)
        location_data = location.dict(exclude_unset=True)
        print("Prepared location data:", location_data)
        
        # Check and ensure that fields like 'country', 'state', 'city' are not None
        if location_data.get("country") is None:
            location_data["country"] = ""  # Set to empty string or default value
        if location_data.get("state") is None:  
            location_data["state"] = ""
        if location_data.get("city") is None:
            location_data["city"] = ""

        # Continue with the rest of the processing
        location_data["createdDate"] = datetime.utcnow()
        location_data["lastUpdatedDate"] = datetime.utcnow()
        location_data["openingHours"] = datetime.utcnow()
        location_data["closingHours"] = datetime.utcnow()

        location_data["randomId"] = get_next_random_id()

        result = get_location_collection().insert_one(location_data)

        location_data["branchId"] = str(result.inserted_id)

        return Location(**location_data)

    except Exception as e:
        print("Error:", str(e))  # Debugging print
        raise HTTPException(status_code=500, detail=f"Failed to create location: {str(e)}")

# Fetch a specific location by ID
@router.get("/location/{location_id}", response_model=Location)
async def get_location_by_id(location_id: str):
    try:
        location_data = get_location_collection().find_one({"_id": location_id})
        if not location_data:
            raise HTTPException(status_code=404, detail="Location not found")

        return Location(**location_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error fetching location")

# Update a specific location by ID
@router.patch("/location/{location_id}", response_model=Location)
async def update_location(location_id: str, location: LocationPost):
    try:
        location_data = location.dict(exclude_unset=True)
        location_data["lastUpdatedDate"] = datetime.utcnow()

        # 🔥 Convert location_id to ObjectId
        obj_id = ObjectId(location_id)

        # Update location in MongoDB
        result = get_location_collection().update_one({"_id": obj_id}, {"$set": location_data})
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Location not found")

        updated_location = get_location_collection().find_one({"_id": obj_id})
        updated_location["id"] = str(updated_location["_id"])  # if your model expects `id` instead of `_id`
        
        return Location(**updated_location)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update location: {str(e)}")

# Deactivate a location by ID (simulated deactivation by updating the 'status' field)
@router.get("/location/{location_id}", response_model=Location)
async def get_location_by_id(location_id: str):
    try:
        # 1. Validate ObjectId format
        if not ObjectId.is_valid(location_id):
            raise HTTPException(status_code=400, detail="Invalid location ID format")

        # 2. Convert string ID to ObjectId
        _id = ObjectId(location_id)

        # 3. Find document
        location_data = get_location_collection().find_one({"_id": _id})

        # 4. If not found
        if not location_data:
            raise HTTPException(status_code=404, detail="Location not found")

        # 5. Prepare response
        location_data["locationId"] = str(location_data["_id"])  # 👈 Add id as string if needed
        del location_data["_id"]  # 👈 Remove MongoDB's _id field

        # 6. Return clean Location model
        return Location(**location_data)

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching location: {str(e)}")

@router.patch("/location/{location_id}/activate")
async def activate_location(location_id: str):
    try:
        result = get_location_collection().update_one(
            {"_id": ObjectId(location_id)},  # ✅ Converted here
            {"$set": {"status": "active"}}
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Location not found")
        return {"message": "Location activated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to activate location")
    

@router.patch("/location/{location_id}/deactivate")
async def deactivate_location(location_id: str):
    try:
        result = get_location_collection().update_one(
            {"_id": ObjectId(location_id)},  # ✅ Converted here
            {"$set": {"status": "inactive"}}
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Location not found")
        return {"message": "Location activated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to deactivated location")
    

@router.get("/warehouses/export-csv")
async def export_locations_to_csv():
    try:
        # Fetch only active locations
        locations_cursor = get_location_collection().find({"status": "active"})
        locations = []
        for loc in locations_cursor:
            loc["branchId"] = str(loc["_id"])
            del loc["_id"]
            locations.append(loc)
        
        if not locations:
            raise HTTPException(status_code=404, detail="No active locations found")
        
        # Define CSV headers based on Location model
        headers = [
            "branchId", "randomId", "branchName", "aliasName", "status", "address",
            "country", "state", "city", "postalCode", "phoneNumber", "email",
            "latitude", "longitude", "description", "openingHours", "closingHours",
            "managerName", "managerContact", "createdDate", "lastUpdatedDate", "createdBy"
        ]
        
        # Convert to DataFrame
        df = pd.DataFrame(locations, columns=headers)
        # Convert datetime fields to string
        df["openingHours"] = df["openingHours"].apply(lambda x: x.isoformat() if x else "")
        df["closingHours"] = df["closingHours"].apply(lambda x: x.isoformat() if x else "")
        df["createdDate"] = df["createdDate"].apply(lambda x: x.isoformat() if x else "")
        df["lastUpdatedDate"] = df["lastUpdatedDate"].apply(lambda x: x.isoformat() if x else "")
        
        # Generate CSV
        csv_buffer = StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        
        # Create filename with timestamp
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"warehouses_export_{timestamp}.csv"
        
        return StreamingResponse(
            content=BytesIO(csv_buffer.getvalue().encode("utf-8")),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except Exception as e:
        logger.error(f"Error exporting CSV: {str(e)}")
        logger.error(f"Stack Trace: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to export CSV: {str(e)}")

@router.post("/warehouses/import-csv", response_model=ImportResult)
async def import_locations_from_csv(file: UploadFile = File(...)):
    try:
        # Validate file type
        if not file.filename.endswith(".csv"):
            raise HTTPException(status_code=400, detail="Only CSV files are allowed")
        
        # Read CSV file
        try:
            content = await file.read()
            csv_buffer = StringIO(content.decode("utf-8"))
            df = pd.read_csv(csv_buffer)
        except Exception as e:
            logger.error(f"Failed to parse CSV: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Invalid CSV format: {str(e)}")
        
        inserted_count = 0
        error_count = 0
        successful = []
        failed = []
        
        for index, row in df.iterrows():
            try:
                # Prepare data for validation
                row_data = row.to_dict()
                
                # Convert NaN to None and ensure correct types
                for key in row_data:
                    if pd.isna(row_data[key]):
                        row_data[key] = None
                    elif key in ["phoneNumber", "managerContact", "createdBy", "aliasName", "status", "address", "email", "description", "branchName", "country", "state", "city"]:
                        # Convert to string for string fields
                        row_data[key] = str(row_data[key]) if row_data[key] is not None else None
                    elif key == "postalCode":
                        # Ensure integer for postalCode
                        try:
                            row_data[key] = int(float(row_data[key])) if row_data[key] is not None else None
                        except (ValueError, TypeError):
                            row_data[key] = None
                    elif key in ["latitude", "longitude"]:
                        # Ensure float for latitude/longitude
                        try:
                            row_data[key] = float(row_data[key]) if row_data[key] is not None else None
                        except (ValueError, TypeError):
                            row_data[key] = None
                
                # Convert datetime fields if present
                for field in ["openingHours", "closingHours", "createdDate", "lastUpdatedDate"]:
                    if field in row_data and row_data[field] is not None:
                        try:
                            row_data[field] = datetime.fromisoformat(str(row_data[field]).replace("Z", "+00:00"))
                        except ValueError as ve:
                            failed.append({
                                "row": index + 2,
                                "data": row_data,
                                "error": f"Invalid datetime format for {field}: {str(ve)}",
                                "missingFields": []
                            })
                            error_count += 1
                            continue
                
                # Validate required fields
                required_fields = ["branchName", "country", "state", "city"]
                missing_fields = [field for field in required_fields if field not in row_data or row_data[field] is None]
                if missing_fields:
                    failed.append({
                        "row": index + 2,
                        "data": row_data,
                        "error": "Missing required fields",
                        "missingFields": missing_fields
                    })
                    error_count += 1
                    continue
                
                # Validate using LocationPost model
                try:
                    location_data = LocationPost(**row_data)
                except ValidationError as ve:
                    failed.append({
                        "row": index + 2,
                        "data": row_data,
                        "error": str(ve),
                        "missingFields": [error["loc"][0] for error in ve.errors()]
                    })
                    error_count += 1
                    continue
                
                location_dict = location_data.dict(exclude_unset=True)
                
                # Insert new location (no check for existing records)
                location_dict["createdDate"] = datetime.utcnow()
                location_dict["lastUpdatedDate"] = datetime.utcnow()
                location_dict["openingHours"] = location_dict.get("openingHours") or datetime.utcnow()
                location_dict["closingHours"] = location_dict.get("closingHours") or datetime.utcnow()
                location_dict["randomId"] = get_next_random_id()
                
                try:
                    result = get_location_collection().insert_one(location_dict)
                except Exception as e:
                    logger.error(f"Database insert failed for row {index + 2}: {str(e)}")
                    failed.append({
                        "row": index + 2,
                        "data": location_dict,
                        "error": f"Database insert failed: {str(e)}",
                        "missingFields": []
                    })
                    error_count += 1
                    continue
                
                inserted_count += 1
                successful.append({
                    "row": index + 2,
                    "data": location_dict,
                    "assignedId": str(result.inserted_id)
                })
                
            except Exception as e:
                logger.error(f"Error processing row {index + 2}: {str(e)}")
                logger.error(f"Stack Trace: {traceback.format_exc()}")
                failed.append({
                    "row": index + 2,
                    "data": row.to_dict(),
                    "error": f"Unexpected error: {str(e)}",
                    "missingFields": []
                })
                error_count += 1
        
        return ImportResult(
            message="CSV import completed",
            inserted_count=inserted_count,
            updated_count=0,  # No updates, only inserts
            errorCount=error_count,
            successful=successful,
            updated=[],  # No updates
            failed=failed
        )
    except Exception as e:
        logger.error(f"Error importing CSV: {str(e)}")
        logger.error(f"Stack Trace: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to import CSV: {str(e)}")
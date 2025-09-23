


from fastapi import APIRouter, HTTPException, Request
from bson import ObjectId
from pydantic import ValidationError
from pymongo import MongoClient
from typing import List

from .utils import get_tables_collection # Ensure List is imported
from .models import Area, TablesCreate, TablesResponse, Table, UpdateTableModel

router = APIRouter()


def transform_tables_data(tables_data: dict) -> TablesResponse:
    """
    Transform MongoDB document to TablesResponse model.
    """
    return TablesResponse(
        _id=str(tables_data.get('_id')) if tables_data.get('_id') else None,
        totalTableCount=tables_data.get('totalTableCount', 0),
        totalTable=[
            Area(
                areaName=area['areaName'],
                tables=[
                    Table(
                        tableNumber=table.get('tableNumber'),
                        seats=table.get('seats'),
                        tableName=table.get('tableName')
                    ) for table in area['tables']
                ],
                tableCount=len(area['tables'])  # Calculate tableCount dynamically
            ) for area in tables_data.get('totalTable', [])
        ],
        type=tables_data.get('type', ''),
        location=tables_data.get('location', ''),
        status=tables_data.get('status', '')
    )



@router.post("/", response_model=str)
async def create_tables(tables: TablesCreate):
    try:
        # Parse the incoming payload
        new_tables_data = tables.dict()
      
        # Process and validate table fields based on type
        if tables.type == "manual":
            for area in new_tables_data['totalTable']:
                for index, table in enumerate(area['tables']):
                    table.pop('tableName', None)

                    # Validate 'seats' for manual type
                    if table.get('seats') is None:
                        raise HTTPException(
                            status_code=400,
                            detail="Each table must have 'seats' for manual type"
                        )
                    

        elif tables.type == "predefined":
            for area in new_tables_data['totalTable']:
                for index, table in enumerate(area['tables']):
                    table.pop('tableName', None)

                    # Validate 'seats' for predefined type
                    if table.get('seats') is None:
                        raise HTTPException(
                            status_code=400,
                            detail="Each table must have 'seats' for predefined type"
                        )

        # Insert the validated and processed data into MongoDB
        result = get_tables_collection().insert_one(new_tables_data)
        return str(result.inserted_id)

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.errors())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating tables: {str(e)}")

@router.get("/", response_model=List[TablesResponse])
async def read_tables():
    try:
        tables_collection = get_tables_collection()

        # Fetch all documents from the 'table' collection
        tables = list(tables_collection.find())

        # Transform each table document
        result = []
        for table in tables:
            try:
                transformed_table = transform_tables_data(table)
                result.append(transformed_table)
            except Exception as transform_error:
                print(f"Error transforming table with ID {table.get('_id')}: {str(transform_error)}")
                # Optionally, skip this table or log the error for debugging
                continue

        return result

    except Exception as e:
        print(f"Error reading tables from database: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error reading tables: {str(e)}")


@router.get("/{table_id}", response_model=TablesResponse)
async def read_table(table_id: str):
    try:
        table = get_tables_collection().find_one({"_id": ObjectId(table_id)})
        if table:
            return transform_tables_data(table)
        else:
            raise HTTPException(status_code=404, detail="Table not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading table: {str(e)}")
    
## Normal Patch
@router.patch("/{table_id}", response_model=str)
async def update_table(table_id: str, table: UpdateTableModel, request: Request):
    try:
        # Fetch the existing table by ID
        existing_table = get_tables_collection().find_one({"_id": ObjectId(table_id)})
        if not existing_table:
            raise HTTPException(status_code=404, detail="Table not found")

        # Extract the incoming data and filter out unset values
        patched_data = {k: v for k, v in table.dict(exclude_unset=True).items() if v is not None}

        # Log the incoming payload for debugging
        received_payload = await request.json()
        print(f"Received payload for table {table_id}: {received_payload}")

        # Handle the 'totalTable' field specifically (no recalculations)
        if "totalTable" in patched_data:
            updated_total_table = patched_data["totalTable"]

            # Ensure tableNumber is always a string
            for area in updated_total_table:
                for table in area.get("tables", []):
                    table["tableNumber"] = str(table["tableNumber"])  # Ensure tableNumber is a string

            patched_data["totalTable"] = updated_total_table

        # # Log patched data for debugging
        # print(f"Patched data for table {table_id}: {patched_data}")

        # Update the document in the database
        result = get_tables_collection().update_one(
            {"_id": ObjectId(table_id)},
            {"$set": patched_data}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Table not found during update")
        if result.modified_count == 0:
            print(f"No changes were made for table {table_id}. Existing data might match the payload.")

        return "Table patched successfully"

    except Exception as e:
        print(f"Error patching table {table_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error patching table: {str(e)}")


@router.patch("/table/{table_id}", response_model=str)
async def update_table_table(table_id: str, table_data: dict, request: Request):
    try:
        # Fetch the existing table document from MongoDB
        existing_table = get_tables_collection().find_one({"_id": ObjectId(table_id)})
        if not existing_table:
            raise HTTPException(status_code=404, detail="Table not found")

        # Log the incoming payload for debugging
        # received_payload = await request.json()
        # print(f"Received payload for table {table_id}: {received_payload}")

        # Extract table details from the incoming data
        area_name = table_data.get("areaName")
        table_number = table_data.get("tableNumber")
        seats = table_data.get("seats")

        # Check if areaName and seats are present
        if not area_name or seats is None:
            raise HTTPException(status_code=400, detail="areaName and seats must be provided")
        
        # Find the area in totalTable by areaName
        area_found = False
        for area in existing_table.get("totalTable", []):
            if area["areaName"] == area_name:
                area_found = True
                # Find the table in the area by tableNumber
                table_found = False
                for table in area["tables"]:
                    if table_number and table["tableNumber"] == table_number:
                        table["seats"] = seats  # Update the number of seats
                        table_found = True
                        print(f"Updated table {table_number} in area {area_name} with {seats} seats.")
                        break

                if not table_found:
                    # If table doesn't exist, handle adding the new table
                    if table_number is not None:
                        new_table = {"tableNumber": table_number, "seats": seats}  # Create table object
                        area["tables"].append(new_table)  # Append the new table
                        print(f"Added table {table_number} in area {area_name} with {seats} seats.")
                        
                area["tableCount"] = len(area["tables"])  # Recalculate tableCount
                break

        if not area_found:
            # If areaName doesn't exist, create a new area and add the table
            if table_number is not None:
                new_area = {"areaName": area_name, "tables": [{"tableNumber": table_number, "seats": seats}], "tableCount": 1}
                existing_table["totalTable"].append(new_area)
                print(f"Added new area {area_name} with table {table_number} and {seats} seats.")

        # Perform the update in the MongoDB collection
        result = get_tables_collection().update_one({"_id": ObjectId(table_id)}, {"$set": existing_table})
        if result.modified_count == 0:
            raise HTTPException(status_code=500, detail="Failed to patch table")

        return "Table patched successfully"
    except Exception as e:
        print(f"Error patching table {table_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error patching table: {str(e)}")




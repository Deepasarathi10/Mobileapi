# routes.py

import asyncio
import json

import httpx
import numpy as np
from Branches.utils import get_branch_collection
from fastapi import (
    APIRouter,
    HTTPException,
    Query,
    UploadFile,
    File,
    Response,
    Body,
    UploadFile,
    Request
)
from typing import List, Optional, Dict, Any
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from .models import BranchwiseItem, BranchwiseItemPost, ItemUpdate,BranchwiseItemPatch
import pandas as pd
import io
from pymongo import ReturnDocument, UpdateOne
from io import BytesIO
from pathlib import Path
from datetime import datetime
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, parse_obj_as, create_model, Field
import csv
from typing import List, Union, Optional
from io import StringIO
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse
import re
from asyncio import sleep
from confluent_kafka import Producer, Consumer, KafkaError
import cv2
import time
# from pyzbar.pyzbar import decode
from fastapi import APIRouter, status


from promotionalOffer.utils import get_collection




router = APIRouter()
mongo_client = AsyncIOMotorClient("mongodb://admin:YenE580nOOUE6cDhQERP@194.233.78.90:27017/admin?appName=mongosh+2.1.1&authSource=admin&authMechanism=SCRAM-SHA-256&replicaSet=yenerp-cluster")
db = mongo_client["admin2"]

item_collection = db["branchwiseitem"]

branchwiseitem_collection = db["branchwiseitem"]


@router.post("/", response_model=str,status_code=status.HTTP_201_CREATED)
async def create_item(item: BranchwiseItemPost):
    result = await item_collection.insert_one(item.dict())
    return str(result.inserted_id)







branchwise_items_collection = db["branchwiseitem"]
variances_collection = db["variances"]
items_collection23 = db["items"]  # Items collection







# Export Csv
@router.get("/view-items-excel/")
async def get_items_by_branch_or_all(branch_name: Optional[str] = None):
    # Existing logic to fetch data
    if branch_name:
        branchwise_items_query = {
            "$or": [
                {"branch": {"$elemMatch": {"branchName": branch_name}}},
                {"branch": {"$elemMatch": {"branchName": "All"}}},
                {"branchId": "All"},
            ]
        }
    else:
        branchwise_items_query = {}

    # Fetch items logic (pseudo-code)
    branchwise_items = (
        await branchwise_items_collection.find(branchwise_items_query)
        .limit(40)
        .to_list(None)
    )

    # Create a DataFrame from the items data
    data = []
    for item in branchwise_items:
        data.append(
            {
                "Item Name": item.get("itemName"),
                "Item Code": item.get("itemCode"),
                "Default Price": item.get("defaultprice"),
                "UOM": item.get("uom"),
                "Item Type": item.get("itemType"),
                "create_item_Date": item.get("create_item_Date"),
                "varianceItemcode": item.get("varianceItemcode"),
                "subcategory": item.get("subcategory"),
                "netPrice": item.get("netPrice"),
                "reorderLevel": item.get("reorderLevel"),
                "category": item.get("category"),
                "itemGroup": item.get("itemGroup"),
                "tax": item.get("tax"),
                "price": item.get("price"),
                "description": item.get("description"),
                "hsnCode": item.get("hsnCode"),
                "status": item.get("status"),
            }
        )
    df = pd.DataFrame(data)

    # Convert DataFrame to Excel file
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Branchwise Items")
    # No need to call writer.save() here, it's handled by the context manager

    # Set the output position to the beginning of the stream
    output.seek(0)

    # Return the Excel file response
    return Response(
        content=output.read(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=branchwise_items.xlsx"},
    )


# upload CSV

items_collection2 = db["items"]
variances_collection = db["variances"]
order_type_collection = db["orderType"]


def ensure_columns(df, required_columns):
    for column in required_columns:
        if column not in df.columns:
            df[column] = None
    return df


@router.post("/upload-csv/")
async def upload_csv(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        csv_string = io.StringIO(contents.decode("utf-8"))
        df = pd.read_csv(csv_string)

        # Define necessary columns for each collection
        item_fields = [
            "itemCode",
            "itemName",
            "uom",
            "tax",
            "category",
            "itemgroup",
            "status",
            "description",
            "itemtype",
            "create_item_date",
            "updated_item_date",
        ]
        variance_fields = [
            "varianceName",
            "uom",
            "varianceItemcode",
            "status",
            "subcategory",
            "price",
            "netPrice",
            "qr_code",
            "shelfLife",
            "reorderLevel",
            "itemName",
        ]
        order_type_fields = ["orderType"]

        # Ensure all required columns are present in the DataFrame
        df = ensure_columns(df, item_fields + variance_fields + order_type_fields)

        # Match order types from the database
        db_order_types_cursor = order_type_collection.find(
            {}, {"orderTypeName": 1, "_id": 0}
        )
        db_order_types = [
            doc["orderTypeName"] async for doc in db_order_types_cursor
        ]  # Asynchronously iterate over cursor

        # Rename matching columns
        for col in df.columns:
            if col in db_order_types:
                df.rename(columns={col: "orderType"}, inplace=True)

        # Process records and insert into the database
        branchwise_items_data = df.to_dict(orient="records")
        if branchwise_items_data:
            result = await branchwise_items_collection.insert_many(
                branchwise_items_data
            )
            inserted_ids = [str(id) for id in result.inserted_ids]
            return {"status": "success", "inserted_ids": inserted_ids}
        return {"status": "success", "message": "No data to insert"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# patch method for all-items


@router.patch("/update-item/{item_name}")
async def update_item_by_name(item_name: str, item_update: ItemUpdate):
    query = {"itemName": item_name}
    update_data = {
        "$set": {
            key: val for key, val in item_update.updates.items() if val is not None
        }
    }

    result = await branchwise_items_collection.update_one(query, update_data)
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Item not found or no update made")

    updated_item = await branchwise_items_collection.find_one(query)
    updated_item["branchwiseItemId"] = str(updated_item.pop("_id"))
    return updated_item




class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v, values=None, **kwargs):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return str(v)


class BranchwiseItem(BaseModel):
    id: str = Field(..., alias="_id")
    varianceitemCode: Optional[str]= None
    itemName: Optional[str]= None
    varianceName: Optional[str]= None
    category: Optional[str]= None
    subCategory: Optional[str]= None
    itemGroup: Optional[str]= None
    ItemType: Optional[Union[str, None]] = None
    varianceName_Uom: Optional[str]= None
    item_Uom: Optional[str]= None
    tax: Optional[Union[int, float, None]]
    item_Defaultprice: Optional[Union[int, float, None]]
    variance_Defaultprice: Optional[Union[int, float, None]]
    description: Optional[Union[str, None]] = None
    hsnCode: Optional[Union[int, str, None]]
    shelfLife: Optional[Union[int, float, None]]
    reorderLevel: Optional[Union[int, float, None]]
    itemid:Optional[str]=None
    dynamicFields: Dict[str, Any] = {}








# Utility function to fetch branch alias names locally
async def fetch_branch_alias_names_locally() -> List[str]:
    try:
        branch_collection = get_branch_collection()
        branches = branch_collection.find()
        return [branch['aliasName'] for branch in branches if 'aliasName' in branch]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"An error occurred while fetching branch data: {exc}")

@router.post("/upload-csv23/")
async def upload_csv(
    file: UploadFile = File(...), 
    merge: bool = Query(default=False),
    replace: bool = Query(default=False)
):
    # Fetch branch alias names locally
    alias_names = await fetch_branch_alias_names_locally()

    # Read the uploaded CSV file
    content = await file.read()
    df = pd.read_csv(io.BytesIO(content))

    # Validate CSV columns against branch alias names
    for alias in alias_names:
        if f"EnablePrice_{alias}" not in df.columns or f"Price_{alias}" not in df.columns or f"branchwise_item_status_{alias}" not in df.columns:
            raise HTTPException(status_code=400, detail=f"CSV is missing columns for alias name: {alias}")

    # Convert DataFrame to dictionary
    new_data = df.to_dict(orient="records")

    if replace:
        # Delete all existing data and insert new data
        await branchwise_items_collection.delete_many({})
        await branchwise_items_collection.insert_many(new_data)
    elif merge:
        # Fetch existing data from MongoDB
        existing_data = await branchwise_items_collection.find().to_list(None)
        existing_data_dict = {item['_id']: item for item in existing_data}

        for record in new_data:
            record_id = record.get('_id')
            if record_id in existing_data_dict:
                # Update existing record
                await branchwise_items_collection.update_one(
                    {'_id': ObjectId(record_id)},
                    {'$set': record}
                )
            else:
                # Insert new record
                await branchwise_items_collection.insert_one(record)
    else:
        # Insert new data without merging or replacing
        await branchwise_items_collection.insert_many(new_data)

    return {"message": "CSV uploaded successfully", "columns": df.columns.tolist()}



@router.get("/get-all-data23/")
async def get_all_data(
    page: int = Query(1, ge=1),  # Page number, default is 1
    limit: int = Query(20, ge=1, le=100),  # Limit of items per page, default is 20
    item_name: Optional[str] = Query(None),  # Optional search term for itemName
    variance_name: Optional[str] = Query(None)  # Optional search term for varianceName
) -> Dict[str, Any]:
    # Create a query filter for itemName and varianceName if provided
    query_filter = {}

    if item_name and variance_name:
        query_filter["$or"] = [
            {"itemName": {"$regex": item_name, "$options": "i"}},
            {"varianceName": {"$regex": variance_name, "$options": "i"}},
            {"variances.varianceName": {"$regex": variance_name, "$options": "i"}}
        ]
    elif item_name:
        query_filter["itemName"] = {"$regex": item_name, "$options": "i"}
    elif variance_name:
        query_filter["$or"] = [
            {"varianceName": {"$regex": variance_name, "$options": "i"}},
            {"variances.varianceName": {"$regex": variance_name, "$options": "i"}}
        ]

    # Count total items for pagination metadata
    total_items = await branchwise_items_collection.count_documents(query_filter)

    # Calculate the number of items to skip
    skip = (page - 1) * limit

    # Fetch data with pagination and search filter
    data = await branchwise_items_collection.find(query_filter).skip(skip).limit(limit).to_list(None)

    if not data:
        raise HTTPException(status_code=404, detail="No data found")

    def transform_item(item):
        # Handle NaN values
        item = {k: (None if pd.isna(v) else v) for k, v in item.items()}
        item_name = item.get("itemName")

        # Base item transformation
        transformed_item = {
            "item": {
                "branchwiseItemId": str(item.get("_id")),
                "itemName": item.get("itemName"),
                "category": item.get("category"),
                "subcategory": item.get("subCategory"),
                "itemGroup": item.get("itemGroup"),
                "ItemType": item.get("ItemType"),
                "item_Uom": item.get("item_Uom"),
                "tax": item.get("tax"),
                "item_Defaultprice": item.get("item_Defaultprice"),
                "description": item.get("description"),
                "hsnCode": item.get("hsnCode"),
                "status": item.get("status"),
                "create_item_date": item.get("create_item_date"),
                "updated_item_date": item.get("updated_item_date"),
                "netPrice": item.get("netPrice"),
            },
            "variance": {},
        }

        # Process flat structure variance (like first data example)
        if "varianceName" in item:
            variance_name = item.get("varianceName")
            variance_info = {
                "varianceitemCode": item.get("varianceitemCode"),
                "varianceName": variance_name,
                "variance_Defaultprice": item.get("variance_Defaultprice"),
                "variance_Uom": item.get("variance_Uom"),
                "varianceStatus": "Active",
                "qrCode": None,
                "shelfLife": item.get("shelfLife"),
                "reorderLevel": item.get("reorderLevel"),
                "orderType": {},
                "branchwise": {},
            }

            # Dynamically handle orderType for flat structure
            order_types = set([key.split('_')[0] for key in item.keys() if key.endswith('_Price') or key.endswith('_Enable')])
            for order_type in order_types:
                variance_info["orderType"][order_type] = {
                    f"{order_type}_Price": item.get(f"{order_type}_Price"),
                    f"{order_type}_Enable": item.get(f"{order_type}_Enable") == "y",
                }

            # Dynamically handle branchwise for flat structure
            branches = set([key.split('_')[1] for key in item.keys() if (key.startswith('Price_') or key.startswith('EnablePrice_') or key.startswith('branchwise_item_status_')) and key.split('_')[1] != 'item'])
            for branch in branches:
                variance_info["branchwise"][branch] = {
                    f"Price_{branch}": item.get(f"Price_{branch}"),
                    f"EnablePrice_{branch}": item.get(f"EnablePrice_{branch}") == "y",
                    f"itemStatus_{branch}": item.get(f"branchwise_item_status_{branch}") == "y",
                    f"availableStock_{branch}": item.get(f"availableStock_{branch}", 0)
                }

            transformed_item["variance"][variance_name] = variance_info

        # Process nested structure variances (like second data example)
        if "variances" in item:
            for variance in item["variances"]:
                variance_name = variance.get("variance_name")
                variance_info = {
                    "varianceitemCode": variance.get("varianceitemCode"),
                    "varianceName": variance_name,
                    "variance_Defaultprice": variance.get("variance_Defaultprice"),
                    "variance_Uom": variance.get("variance_Uom"),
                    "varianceStatus": "Active",
                    "qrCode": None,
                    "shelfLife": variance.get("shelfLife"),
                    "reorderLevel": variance.get("reorderLevel"),
                    "orderType": variance.get("orderType", {}),
                    "branchwise": variance.get("branchwise", {}),
                }
                transformed_item["variance"][variance_name] = variance_info

        return item_name, transformed_item

    transformed_data = {}
    for item in data:
        item_name, transformed_item = transform_item(item)
        if item_name not in transformed_data:
            transformed_data[item_name] = transformed_item
        else:
            transformed_data[item_name]["variance"].update(transformed_item["variance"])

    # Calculate total pages
    total_pages = (total_items + limit - 1) // limit

    return {
        "page": page,
        "limit": limit,
        "total_items": total_items,
        "total_pages": total_pages,
        "data": transformed_data
    }



@router.get("/getbyid/{item_id}")
async def get_item(item_id: str):
    try:
        item = await branchwise_items_collection.find_one({"_id": ObjectId(item_id)})
        if not item:
            raise HTTPException(status_code=404, detail="Item not found.")
        
        item = {k: (None if pd.isna(v) else v) for k, v in item.items()}
        item_name = item.get("itemName")
        variance_name = item.get("varianceName")
        transformed_item = {
            "item": {
                "branchwiseItemId": str(item.get("_id")),
                "itemName": item.get("itemName"),
                "varianceName": item.get("varianceName"),
                "category": item.get("category"),
                "subcategory": item.get("subCategory"),
                "itemGroup": item.get("itemGroup"),
                "ItemType": item.get("ItemType"),
                "itemUom": item.get("item_Uom"),
                "tax": item.get("tax"),
                "itemDefaultprice": item.get("item_Defaultprice"),
                "description": item.get("description"),
                "hsnCode": item.get("hsnCode"),
                "itemgroup": None,
                "status": None,
                "create_item_date": None,
                "updated_item_date": None,
                "netPrice": None,
            },
            "variance": {},
        }

        variance_info = {
            "varianceitemCode": item.get("varianceitemCode"),
            "varianceName": variance_name,
            "variance_Defaultprice": item.get("variance_Defaultprice"),
            "variance_Uom": item.get("variance_Uom"),
            "varianceStatus": "Active",
            "qrCode": None,
            "shelfLife": item.get("shelfLife"),
            "reorderLevel": item.get("reorderLevel"),
            "orderType": {},
            "branchwise": {},
        }

        def convert_to_bool(value):
            if isinstance(value, str):
                if value.lower() == 'y':
                    return True
                elif value.lower() == 'n':
                    return False
            return value

        order_types = set([key.split('_')[0] for key in item.keys() if key.endswith('_Price') or key.endswith('_Enable')])
        for order_type in order_types:
            variance_info["orderType"][order_type] = {
                f"{order_type}_price": item.get(f"{order_type}_Price"),
                f"{order_type}_enable": convert_to_bool(item.get(f"{order_type}_Enable")),
            }

        branches = set([key.split('_')[1] for key in item.keys() if (key.startswith('Price_') or key.startswith('EnablePrice_') or key.startswith('branchwise_item_status_')) and key.split('_')[1] != 'item'])
        for branch in branches:
            variance_info["branchwise"][branch] = {
                f"Price_{branch}": item.get(f"Price_{branch}"),
                f"EnablePrice_{branch}": convert_to_bool(item.get(f"EnablePrice_{branch}")),
                f"itemStatus_{branch}": convert_to_bool(item.get(f"branchwise_item_status_{branch}")),
                f"availableStock_{branch}": item.get(f"availableStock_{branch}", 0)
            }

        transformed_item["variance"][variance_name] = variance_info
        return transformed_item

    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"An error occurred while fetching the item: {exc}")
    
    
    
    
    
    

    
    
    
@router.delete("/delete-item23/{item_id}")
async def delete_item(item_id: str):
    try:
        # Validate the ObjectId
        if not ObjectId.is_valid(item_id):
            raise HTTPException(status_code=400, detail="Invalid item ID format.")

        # Attempt to delete the item
        result = await branchwise_items_collection.delete_one({"_id": ObjectId(item_id)})

        # Check if the item was deleted
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Item not found.")

        return {"message": "Item deleted successfully"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"An error occurred while deleting the item: {exc}")

    
 
 
@router.get("/export-csv23/", response_class=StreamingResponse)
async def export_csv():
    try:
        # Fetch all data from MongoDB
        data = await branchwise_items_collection.find().to_list(None)

        if not data:
            raise HTTPException(status_code=404, detail="No data found to export.")

        # Convert data to DataFrame
        df = pd.DataFrame(data)

        # Drop the '_id' column to exclude it from the Excel file
        if "_id" in df.columns:
            df.drop(columns=["_id"], inplace=True)

        # Convert DataFrame to Excel
        excel_buffer = io.BytesIO()
        df.to_excel(excel_buffer, index=False)
        excel_buffer.seek(0)

        # Create StreamingResponse for the Excel file
        response = StreamingResponse(
            iter([excel_buffer.getvalue()]),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )   
        response.headers["Content-Disposition"] = "attachment; filename=branchwise_items.xlsx"

        return response

    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"An error occurred while exporting the data: {exc}")


 
    
   
 # Export CSV headers only endpoint
@router.get("/export-csv-headers23/", response_class=StreamingResponse)
async def export_csv_headers():
    try:
        # Fetch one document from MongoDB to infer columns
        sample_document = await branchwise_items_collection.find_one()

        if not sample_document:
            raise HTTPException(status_code=404, detail="No data found to infer headers.")

        # Convert sample document to DataFrame
        df = pd.DataFrame([sample_document])

        # Drop the '_id' column if you do not want it in the CSV headers
        if "_id" in df.columns:
            df.drop(columns=["_id"], inplace=True)

        # Create a DataFrame with only the headers
        headers_only_df = pd.DataFrame(columns=df.columns)

        # Convert DataFrame to CSV with only headers
        csv_buffer = io.StringIO()
        headers_only_df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)

        # Create StreamingResponse for the CSV file
        response = StreamingResponse(
            iter([csv_buffer.getvalue()]),
            media_type="text/csv"
        )
        response.headers["Content-Disposition"] = "attachment; filename=headers_only.csv"

        return response

    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"An error occurred while exporting the headers: {exc}")
  
   
    
    






@router.post("/add-item23/")
async def add_item(item_data: Dict[str, Any] = Body(...)):
    """
    Endpoint to add a new item with variances and branch-specific data.
    Expects a JSON object with a similar structure to the provided example.
    """
    try:
        # Convert input to ensure it has ObjectId where necessary
        item_data["_id"] = ObjectId()  # Automatically generate a new ObjectId for the item

        # Insert the item into the MongoDB collection
        result = await branchwise_items_collection.insert_one(item_data)

        # Return the inserted item's ID
        return {"message": "Item added successfully", "itemId": str(result.inserted_id)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
    
    
    
    
    
    
    
    
    



@router.get("/next-fgcode/")
async def get_next_varianceitemcode():
    try:
        # Fetch all varianceitemCodes from the collection
        codes = await branchwise_items_collection.find({}, {"variances.varianceitemCode": 1, "_id": 0}).to_list(None)
        
        # Extract numeric part of the code and find the maximum value
        max_code = 0
        code_pattern = re.compile(r"FG(\d+)")
        
        for item in codes:
            for variance in item.get("variances", []):
                variance_code = variance.get("varianceitemCode", "")
                match = code_pattern.match(variance_code)
                if match:
                    num = int(match.group(1))
                    if num > max_code:
                        max_code = num
        
        # Generate the next code
        next_code_number = max_code + 1
        next_code = f"FG{next_code_number:03}"  # Formats the number with leading zeros if needed
        
        return {"next_varianceitemCode": next_code}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")








@router.get("/get-all-devices/")
async def get_all_data(
    page: int = Query(1, ge=1),  # Page number, default is 1
    limit: int = Query(20, ge=1, le=100),  # Limit of items per page, default is 20
    item_name: Optional[str] = Query(None),  # Optional search term for itemName
    branch_alias: Optional[str] = Query(None),  # Optional query for branch alias
    order_type: Optional[str] = Query(None),  # Optional query for order type
    category: Optional[str] = Query(None),  # Optional query for category
    paginate: bool = Query(True)  # Optional flag to enable/disable pagination
) -> Dict[str, Any]:
    # Create a query filter for itemName and category if provided
    query_filter = {}
    if item_name:
        query_filter["itemName"] = {"$regex": item_name, "$options": "i"}  # Case-insensitive search
    if category:
        query_filter["category"] = category

    # Count total items for pagination metadata
    total_items = await branchwise_items_collection.count_documents(query_filter)

    if paginate:
        # Calculate the number of items to skip
        skip = (page - 1) * limit

        # Fetch data with pagination and search filter
        data = await branchwise_items_collection.find(query_filter).skip(skip).limit(limit).to_list(None)
    else:
        # Fetch all data without pagination
        data = await branchwise_items_collection.find(query_filter).to_list(None)

    if not data:
        raise HTTPException(status_code=404, detail="No data found")
    
    def transform_item(item):
        # Base item transformation
        transformed_item = {
            "item": {
                "branchwiseItemId": str(item.get("_id")),
                "itemName": item.get("itemName"),
                "category": item.get("category"),
                "subcategory": item.get("subCategory"),
                "itemGroup": item.get("itemGroup"),
                "ItemType": item.get("ItemType"),
                "item_Uom": item.get("item_Uom"),
                "tax": item.get("tax"),
                "item_Defaultprice": item.get("item_Defaultprice"),
                "description": item.get("description"),
                "hsnCode": item.get("hsnCode"),
                "status": item.get("status"),
                "create_item_date": item.get("create_item_date"),
                "updated_item_date": item.get("updated_item_date"),
                "netPrice": item.get("netPrice"),
                "itemid":item.get("itemid")
            },
            "variance": {},
        }

        # Check if varianceName exists for flat structure variances
        if "varianceName" in item:
            variance_name = item.get("varianceName")
            variance_info = {
                "varianceid": str(ObjectId()),  # Generate a new ObjectId for each variance
                "varianceitemCode": item.get("varianceitemCode") or None,  # Ensure non-null values are handled
                "varianceName": variance_name,
                "variance_Defaultprice": item.get("variance_Defaultprice"),  # Ensure non-null values are handled
                "variance_Uom": item.get("variance_Uom"),
                "varianceStatus": "Active",
                "qrCode": None,
                "shelfLife": item.get("shelfLife"),
                "reorderLevel": item.get("reorderLevel"),
                "orderType": {},
                "branchwise": {},
            }

            # Dynamically handle orderType for flat structure
            order_types = set([key.split('_')[0] for key in item.keys() if key.endswith('_Price') or key.endswith('_Enable')])
            for o_type in order_types:
                if order_type is None or order_type == o_type:
                    variance_info["orderType"][o_type] = {
                        f"{o_type}_Price": item.get(f"{o_type}_Price"),
                        f"{o_type}_Enable": item.get(f"{o_type}_Enable") == "y",
                    }

            # Dynamically handle branchwise for flat structure
            branches = set([key.split('_')[1] for key in item.keys() if (key.startswith('Price_') or key.startswith('EnablePrice_') or key.startswith('branchwise_item_status_')) and key.split('_')[1] != 'item'])
            for branch in branches:
                if branch_alias is None or branch_alias == branch:
                    variance_info["branchwise"][branch] = {
                        f"Price_{branch}": item.get(f"Price_{branch}"),
                        f"EnablePrice_{branch}": item.get(f"EnablePrice_{branch}") == "y",
                        f"itemStatus_{branch}": item.get(f"branchwise_item_status_{branch}") == "y",
                        f"availableStock_{branch}": item.get(f"availableStock_{branch}", 0)
                    }

            transformed_item["variance"][variance_name] = variance_info
        
        # Process nested structure variances
        if "variances" in item:
            for variance in item["variances"]:
                variance_name = variance.get("variance_name")
                variance_info = {
                    "varianceid": str(ObjectId()),  # Generate a new ObjectId for each variance
                    "varianceitemCode": variance.get("varianceitemCode"),
                    "varianceName": variance_name,
                    "variance_Defaultprice": variance.get("variance_Defaultprice"),
                    "variance_Uom": variance.get("variance_Uom"),
                    "varianceStatus": "Active",
                    "qrCode": None,
                    "shelfLife": variance.get("shelfLife"),
                    "reorderLevel": variance.get("reorderLevel"),
                    "orderType": {},
                    "branchwise": {},
                }

                # Filter orderType data based on order_type
                for o_type, details in variance.get("orderType", {}).items():
                    if order_type is None or order_type == o_type:
                        variance_info["orderType"][o_type] = details

                # Filter branchwise data based on branch_alias
                for branch, details in variance.get("branchwise", {}).items():
                    if branch_alias is None or branch_alias == branch:
                        variance_info["branchwise"][branch] = details

                transformed_item["variance"][variance_name] = variance_info

        return item.get("itemName"), transformed_item

    transformed_data = {}
    for item in data:
        item_name, transformed_item = transform_item(item)
        if item_name not in transformed_data:
            transformed_data[item_name] = transformed_item
        else:
            transformed_data[item_name]["variance"].update(transformed_item["variance"])

    # Fetch all unique category names
    category_pipeline = [{"$group": {"_id": "$category"}}]
    categories = await branchwise_items_collection.aggregate(category_pipeline).to_list(None)
    category_names = [category["_id"] for category in categories]

    # Calculate total pages only if pagination is enabled
    total_pages = (total_items + limit - 1) // limit if paginate else 1

    return {
        "page": page if paginate else None,
        "limit": limit if paginate else total_items,
        "total_items": total_items,
        "total_pages": total_pages,
        "categories": category_names,   
        "data": transformed_data
    }

    
    
    
    
@router.get("/get-all-devicestest/")
async def get_all_data(
    item_name: Optional[str] = Query(None),  # Optional search term for itemName
    branch_alias: Optional[str] = Query(None),  # Optional query for branch alias
    order_type: Optional[str] = Query(None),  # Optional query for order type
    category: Optional[str] = Query(None),  # Optional query for category
) -> Dict[str, Any]:
    query_filter = {}
    if item_name:
        query_filter["itemName"] = {"$regex": item_name, "$options": "i"}
    if category:
        query_filter["category"] = category

    data = await branchwise_items_collection.find(query_filter).to_list(None)

    if not data:
        raise HTTPException(status_code=404, detail="No data found")

    def transform_item(item):
        # Use a default value (like 0 or None) if the value is missing or NaN
        item = {k: (None if pd.isna(v) else v) for k, v in item.items()}
        item_name = item.get("itemName")

        transformed_item = {
            "item": {
                "branchwiseItemId": str(item.get("_id")),
                "itemName": item.get("itemName"),
                "category": item.get("category"),
                "subcategory": item.get("subCategory"),
                "itemGroup": item.get("itemGroup"),
                "ItemType": item.get("ItemType", None),  # Provide a default value if None
                "item_Uom": item.get("item_Uom"),
                "tax": item.get("tax", 0),  # Default tax to 0 if None
                "item_Defaultprice": item.get("item_Defaultprice", 0),  # Default price to 0 if None
                "description": item.get("description", ""),  # Default description to empty string
                "hsnCode": item.get("hsnCode", 0),  # Default HSN code to 0 if None
                "status": item.get("status", "Inactive"),  # Default status
                "create_item_date": item.get("create_item_date", None),
                "updated_item_date": item.get("updated_item_date", None),
                "netPrice": item.get("netPrice", None),
                "itemid": item.get("itemid", None)
            },
            "variance": {},
        }

        variance_name = item.get("varianceName")
        if variance_name:
            variance_info = {
                "varianceid": str(ObjectId()),
                "varianceitemCode": item.get("varianceitemCode", None),
                "varianceName": variance_name,
                "variance_Defaultprice": item.get("variance_Defaultprice", 0),  # Set default price if None
                "variance_Uom": item.get("variance_Uom", None),
                "varianceStatus": "Active",
                "qrCode": None,
                "shelfLife": item.get("shelfLife", 1),  # Default shelf life
                "reorderLevel": item.get("reorderLevel", 0),  # Default reorder level
                "orderType": {},
                "branchwise": {},
            }

            # Handle different order types
            order_types = set([key.split('_')[0] for key in item.keys() if key.endswith('_Price') or key.endswith('_Enable')])
            for o_type in order_types:
                if order_type is None or order_type == o_type:
                    variance_info["orderType"][o_type] = {
                        f"{o_type}_Price": item.get(f"{o_type}_Price", 0),  # Default price
                        f"{o_type}_Enable": item.get(f"{o_type}_Enable") == "y",
                    }

            # Handle branches
            branches = set([key.split('_')[1] for key in item.keys() if (key.startswith('Price_') or key.startswith('EnablePrice_') or key.startswith('branchwise_item_status_')) and key.split('_')[1] != 'item'])
            for branch in branches:
                if branch_alias is None or branch_alias == branch:
                    variance_info["branchwise"][branch] = {
                        f"Price_{branch}": item.get(f"Price_{branch}", 0),  # Default price
                        f"EnablePrice_{branch}": item.get(f"EnablePrice_{branch}") == "y",
                        f"itemStatus_{branch}": item.get(f"branchwise_item_status_{branch}") == "y",
                        f"availableStock_{branch}": item.get(f"availableStock_{branch}", 0),  # Default available stock
                    }

            transformed_item["variance"][variance_name] = variance_info

        return item_name, transformed_item

    transformed_data = {}
    for item in data:
        item_name, transformed_item = transform_item(item)
        if item_name not in transformed_data:
            transformed_data[item_name] = transformed_item
        else:
            transformed_data[item_name]["variance"].update(transformed_item["variance"])

    category_pipeline = [{"$group": {"_id": "$category"}}]
    categories = await branchwise_items_collection.aggregate(category_pipeline).to_list(None)
    category_names = [category["_id"] for category in categories]

    return {
        "total_items": len(data),
        "categories": category_names,
        "data": transformed_data
    }

    
    
    

# promotional_offer_collection = get_collection('promotionaloffer')

# @router.get("/")
# async def get_all_branchwise_items(
#     branch_alias: str = Query(None, alias="branch_alias"),
#     order_type: str = Query(None, alias="order_type")
# ):
#     try:
#         cursor = branchwise_items_collection.find({}, {'_id': False})
#         items = await cursor.to_list(length=None)
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

#     # Use a set to collect unique categories dynamically
#     categories = set()

#     # Process and clean data
#     result = {}
#     for item in items:
#         item_name = item.get("itemName", "Unnamed")
        
#         # Replace NaN values and reformat the document structure
#         cleaned_item = {k: (None if isinstance(v, float) and np.isnan(v) else v) for k, v in item.items()}
#         if item_name not in result:
#             result[item_name] = {"item": {}, "variance": {}}

#         # Get the category and add it to the categories set
#         category = cleaned_item.get("category", "Uncategorized")
#         categories.add(category)

#         # Assigning direct item attributes
#         item_attributes = ["branchwiseItemId", "itemName", "category", "subcategory", "itemGroup",
#                            "ItemType", "item_Uom", "tax", "item_Defaultprice", "description", "hsnCode",
#                            "status", "create_item_date", "updated_item_date", "netPrice", "itemid"]
#         item_info = {k: cleaned_item[k] for k in item_attributes if k in cleaned_item}
#         result[item_name]["item"].update(item_info)

#         # Assigning variance details
#         variance_attributes = ["varianceid", "varianceitemCode", "varianceName", "variance_Defaultprice",
#                                "variance_Uom", "varianceStatus", "qrCode", "selfLife", "reorderLevel"]
#         variance_info = {k: cleaned_item[k] for k in variance_attributes if k in cleaned_item}
        
#         # Extracting nested branchwise details dynamically (e.g., GH, SB, AR)
#         branchwise_nested_info = {}
#         for key, value in cleaned_item.items():
#             if key.startswith("Price_") or key.startswith("EnablePrice_") or key.startswith("systemStock_") or key.startswith("physicalStock_"):
#                 branch = key.split("_")[1]  # Extract branch name, e.g., "GH" from "Price_GH"
#                 attribute = key.split("_", 1)[0]  # Extract the attribute part, e.g., "Price"
                
#                 # Apply branch alias filter
#                 if branch_alias and branch != branch_alias:
#                     continue  # Skip branches not matching the query

#                 if branch not in branchwise_nested_info:
#                     branchwise_nested_info[branch] = {}
#                 branchwise_nested_info[branch][f"{attribute}_{branch}"] = value

#         # Extracting order type details
#         order_type_info = {}
#         if "TakeAway_Price" in cleaned_item and "TakeAway_Enable" in cleaned_item:
#             order_type_info["TakeAway"] = {
#                 "TakeAway_Price": cleaned_item.get("TakeAway_Price"),
#                 "TakeAway_Enable": cleaned_item.get("TakeAway_Enable")
#             }
        
#         if "Dinning_Price" in cleaned_item and "Dinning_Enable" in cleaned_item:
#             order_type_info["Dinning"] = {
#                 "Dinning_Price": cleaned_item.get("Dinning_Price"),
#                 "Dinning_Enable": cleaned_item.get("Dinning_Enable")
#             }

#         # Apply order type filter
#         if order_type:
#             order_type_info = {k: v for k, v in order_type_info.items() if k == order_type}

#         # If no branchwise or order type info exists after filtering, skip this item
#         if not branchwise_nested_info and not order_type_info:
#             continue

#         variance_name = cleaned_item.get("varianceName", "Default")
#         if variance_name not in result[item_name]["variance"]:
#             result[item_name]["variance"][variance_name] = variance_info
#             result[item_name]["variance"][variance_name].update({
#                 "orderType": order_type_info,
#                 "branchwise": branchwise_nested_info
#             })

#     if not result:
#         raise HTTPException(status_code=404, detail="No items found")

#     # Return categories as a list and the filtered items data
#     return {
#         "categories": list(categories),
#         "data": result
#     }

    


# Assuming the URL of the promotional offers API


# @router.get("/")
# async def get_all_branchwise_items(
#     branch_alias: str = Query(None, alias="branch_alias"),
#     order_type: str = Query(None, alias="order_type")
# ):
#     try:
#         # Fetch promotional offers data
#         async with httpx.AsyncClient() as client:
#             offers_response = await client.get(PROMOTIONAL_OFFERS_API_URL)
#             offers_response.raise_for_status()
#             promotional_offers = offers_response.json()

#         # Fetch branchwise items
#         cursor = branchwise_items_collection.find({}, {'_id': False})
#         items = await cursor.to_list(length=None)
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

#     # Use a set to collect unique categories dynamically
#     categories = set()

#     # Process and clean data
#     result = {}
#     for item in items:
#         item_name = item.get("itemName", "Unnamed")

#         # Replace NaN values and reformat the document structure
#         cleaned_item = {k: (None if isinstance(v, float) and np.isnan(v) else v) for k, v in item.items()}
#         if item_name not in result:
#             result[item_name] = {"item": {}, "variance": {}}

#         # Get the category and add it to the categories set
#         category = cleaned_item.get("category", "Uncategorized")
#         categories.add(category)

#         # Assigning direct item attributes
#         item_attributes = ["branchwiseItemId", "itemName", "category", "subcategory", "itemGroup",
#                            "ItemType", "item_Uom", "tax", "item_Defaultprice", "description", "hsnCode",
#                            "status", "create_item_date", "updated_item_date", "netPrice", "itemid"]
#         item_info = {k: cleaned_item[k] for k in item_attributes if k in cleaned_item}
#         result[item_name]["item"].update(item_info)

#         # Assigning variance details
#         variance_attributes = ["varianceid", "varianceitemCode", "varianceName", "variance_Defaultprice",
#                                "variance_Uom", "varianceStatus", "qrCode", "selfLife", "reorderLevel"]
#         variance_info = {k: cleaned_item[k] for k in variance_attributes if k in cleaned_item}
        
#         # Extracting nested branchwise details dynamically (e.g., GH, SB, AR)
#         branchwise_nested_info = {}
#         for key, value in cleaned_item.items():
#             if key.startswith("Price_") or key.startswith("EnablePrice_") or key.startswith("systemStock_") or key.startswith("physicalStock_"):
#                 branch = key.split("_")[1]  # Extract branch name, e.g., "GH" from "Price_GH"
#                 attribute = key.split("_", 1)[0]  # Extract the attribute part, e.g., "Price"
                
#                 # Apply branch alias filter
#                 if branch_alias and branch != branch_alias:
#                     continue  # Skip branches not matching the query

#                 if branch not in branchwise_nested_info:
#                     branchwise_nested_info[branch] = {}
#                 branchwise_nested_info[branch][f"{attribute}_{branch}"] = value

#         # Extracting order type details
#         order_type_info = {}
#         if "TakeAway_Price" in cleaned_item and "TakeAway_Enable" in cleaned_item:
#             order_type_info["TakeAway"] = {
#                 "TakeAway_Price": cleaned_item.get("TakeAway_Price"),
#                 "TakeAway_Enable": cleaned_item.get("TakeAway_Enable")
#             }
        
#         if "Dinning_Price" in cleaned_item and "Dinning_Enable" in cleaned_item:
#             order_type_info["Dinning"] = {
#                 "Dinning_Price": cleaned_item.get("Dinning_Price"),
#                 "Dinning_Enable": cleaned_item.get("Dinning_Enable")
#             }

#         # Apply order type filter
#         if order_type:
#             order_type_info = {k: v for k, v in order_type_info.items() if k == order_type}

#         # If no branchwise or order type info exists after filtering, skip this item
#         if not branchwise_nested_info and not order_type_info:
#             continue

#         variance_name = cleaned_item.get("varianceName", "Default")
#         if variance_name not in result[item_name]["variance"]:
#             result[item_name]["variance"][variance_name] = variance_info
#             result[item_name]["variance"][variance_name].update({
#                 "orderType": order_type_info,
#                 "branchwise": branchwise_nested_info
#             })

#         # Check for matching promotional offers for item or variance
#         matched_offers = [
#             {
#                 "offerName": offer["offerName"],
#                 "configuration": offer["configuration"],
#                 "discountValue": offer["discountValue"],
#                 "orderDiscountValue": offer["orderDiscountValue"]
#             }
#             for offer in promotional_offers
#             if item_name in offer.get("itemName", []) or variance_name in offer.get("varianceName1", [])
#         ]
        
#         # Include offers if matched
#         if matched_offers:
#             result[item_name]["variance"][variance_name]["offers"] = matched_offers

#     if not result:
#         raise HTTPException(status_code=404, detail="No items found")

#     # Return categories as a list and the filtered items data
#     return {
#         "categories": list(categories),
#         "data": result
#     }


PROMOTIONAL_OFFERS_COLLECTION_NAME = "promotionaloffer"

@router.get("/")
async def get_all_branchwise_items(
    branch_alias: str = Query(None, alias="branch_alias"),
    order_type: str = Query(None, alias="order_type")
):
    try:
        # Fetch promotional offers data from MongoDB collection using get_collection
        promotional_offers_collection = get_collection(PROMOTIONAL_OFFERS_COLLECTION_NAME)
        promotional_offers = await promotional_offers_collection.find({}).to_list(length=None)

        # Fetch branchwise items
        cursor = branchwise_items_collection.find({}, {'_id': False})
        items = await cursor.to_list(length=None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Use a set to collect unique categories dynamically
    categories = set()

    # Process and clean data
    result = {}
    for item in items:
        item_name = item.get("itemName", "Unnamed")

        # Replace NaN values and reformat the document structure
        cleaned_item = {k: (None if isinstance(v, float) and np.isnan(v) else v) for k, v in item.items()}
        if item_name not in result:
            result[item_name] = {"item": {}, "variance": {}}

        # Get the category and add it to the categories set
        category = cleaned_item.get("category", "Uncategorized")
        categories.add(category)

        # Assigning direct item attributes
        item_attributes = ["branchwiseItemId", "itemName", "category", "subcategory", "itemGroup",
                           "ItemType", "item_Uom", "tax", "item_Defaultprice", "description", "hsnCode",
                           "status", "create_item_date", "updated_item_date", "netPrice", "itemid"]
        item_info = {k: cleaned_item[k] for k in item_attributes if k in cleaned_item}
        result[item_name]["item"].update(item_info)

        # Assigning variance details
        variance_attributes = ["varianceid", "varianceitemCode", "varianceName", "variance_Defaultprice",
                               "variance_Uom", "varianceStatus", "qrCode", "selfLife", "reorderLevel"]
        variance_info = {k: cleaned_item[k] for k in variance_attributes if k in cleaned_item}
        
        # Extracting nested branchwise details dynamically (e.g., GH, SB, AR)
        branchwise_nested_info = {}
        for key, value in cleaned_item.items():
            if key.startswith("Price_") or key.startswith("EnablePrice_") or key.startswith("systemStock_") or key.startswith("physicalStock_"):
                branch = key.split("_")[1]  # Extract branch name, e.g., "GH" from "Price_GH"
                attribute = key.split("_", 1)[0]  # Extract the attribute part, e.g., "Price"
                
                # Apply branch alias filter
                if branch_alias and branch != branch_alias:
                    continue  # Skip branches not matching the query

                if branch not in branchwise_nested_info:
                    branchwise_nested_info[branch] = {}
                branchwise_nested_info[branch][f"{attribute}_{branch}"] = value

        # Extracting order type details
        order_type_info = {}
        if "TakeAway_Price" in cleaned_item and "TakeAway_Enable" in cleaned_item:
            order_type_info["TakeAway"] = {
                "TakeAway_Price": cleaned_item.get("TakeAway_Price"),
                "TakeAway_Enable": cleaned_item.get("TakeAway_Enable")
            }
        
        if "Dinning_Price" in cleaned_item and "Dinning_Enable" in cleaned_item:
            order_type_info["Dinning"] = {
                "Dinning_Price": cleaned_item.get("Dinning_Price"),
                "Dinning_Enable": cleaned_item.get("Dinning_Enable")
            }

        # Apply order type filter
        if order_type:
            order_type_info = {k: v for k, v in order_type_info.items() if k == order_type}

        # If no branchwise or order type info exists after filtering, skip this item
        if not branchwise_nested_info and not order_type_info:
            continue

        variance_name = cleaned_item.get("varianceName", "Default")
        if variance_name not in result[item_name]["variance"]:
            result[item_name]["variance"][variance_name] = variance_info
            result[item_name]["variance"][variance_name].update({
                "orderType": order_type_info,
                "branchwise": branchwise_nested_info
            })

        # Check for matching promotional offers for item, variance, category, and subcategory
        matched_offers = []
        for offer in promotional_offers:
            if (
                item_name in offer.get("itemName", []) or
                variance_name in offer.get("varianceName1", []) or
                variance_name in offer.get("varianceName2", []) or
                category in offer.get("category", []) or
                cleaned_item.get("subcategory") in offer.get("subcategory", [])
            ):
                offer_data = {
                    "offerName": offer["offerName"],
                    "configuration": offer["configuration"],
                    "discountValue": offer.get("discountValue", ""),
                    "orderValue": offer.get("orderValue", ""),
                    "orderDiscountValue": offer.get("orderDiscountValue", ""),
                }

                # Add "Buy 1 Get 1" details if applicable
                if offer["configuration"] == "buy1Get1" and offer.get("varianceName1") and offer.get("varianceName2"):
                    offer_data["buy1Get1"] = {
                        "buyVariance": offer["varianceName1"],
                        "getVariance": offer["varianceName2"]
                    }

                matched_offers.append(offer_data)

        # Include offers if matched
        if matched_offers:
            result[item_name]["variance"][variance_name]["offers"] = matched_offers

    if not result:
        raise HTTPException(status_code=404, detail="No items found")

    # Return categories as a list and the filtered items data
    return {
        "categories": list(categories),
        "data": result
    }



@router.get("/variances")
async def get_all_branchwise_items(
   
   
):
    try:
        # Fetch branchwise items
        cursor = branchwise_items_collection.find({}, {'_id': False})
        items = await cursor.to_list(length=None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Process and clean data
    result = []
    for item in items:
        # Clean the item and only return the specified fields
        cleaned_item = {
            "varianceitemCode": item.get("varianceitemCode", ""),
            "varianceName": item.get("varianceName", ""),
            "variance_Defaultprice": item.get("variance_Defaultprice", 0),
            "variance_Uom": item.get("variance_Uom", ""),
            "selfLife": item.get("selfLife", 0),
        }
        
        result.append(cleaned_item)

    if not result:
        raise HTTPException(status_code=404, detail="No items found")

    # Return only the desired fields in the result
    return result



    

    
@router.patch("/update_physicalstock/")
async def update_physical_stock(
    variance_names: list[str] = Query(..., description="List of variance names of the items to update"),
    branch_aliases: list[str] = Query(..., description="List of branch aliases like AR, SB"),
    new_physical_stocks: list[int] = Body(..., description="List of new physical stock counts to update")
):
    if len(variance_names) != len(branch_aliases) or len(variance_names) != len(new_physical_stocks):
        raise HTTPException(status_code=400, detail="The lengths of variance names, branch aliases, and physical stocks must match")

    update_responses = []
    for variance_name, branch_alias, new_physical_stock in zip(variance_names, branch_aliases, new_physical_stocks):
        # Update the physical stock
        update_result = await branchwise_items_collection.update_one(
            {"varianceName": variance_name},
            {
                "$set": {f"physicalStock_{branch_alias}": new_physical_stock}
            }
        )
        
        if update_result.modified_count == 0:
            update_responses.append({"varianceName": variance_name, "branchAlias": branch_alias, "error": "Item not found or no update needed"})
            continue
        
        # Optionally update the system stock to match the new physical stock
        await branchwise_items_collection.update_one(
            {"varianceName": variance_name},
            {
                "$set": {f"systemStock_{branch_alias}": new_physical_stock}
            }   
        )
        
        # Retrieve the updated details to confirm the changes
        item = await branchwise_items_collection.find_one(
            {"varianceName": variance_name},
            {'_id': False}
        )

        # Prepare and send the updated stock details
        updated_stock_details = {
            "varianceName": variance_name,
            "branchAlias": branch_alias,
            "updatedPhysicalStock": item.get(f"physicalStock_{branch_alias}"),
            "updatedSystemStock": item.get(f"systemStock_{branch_alias}")
        }
        update_responses.append(updated_stock_details)

    return update_responses
    
 
 
@router.get("/getsystemstock/")
async def get_system_stock(
    variance_name: str = Query(..., description="Variance name of the item"),
    branch_alias: str = Query(..., description="Branch alias like AR, SB")
):
    # Find the item based on the variance name
    item = await branchwise_items_collection.find_one(
        {"varianceName": variance_name},
        {'_id': False, f"systemStock_{branch_alias}": 1, "varianceName": 1}
    )

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Return the variance name and system stock for the specified branch alias
    system_stock = item.get(f"systemStock_{branch_alias}")
    if system_stock is None:
        raise HTTPException(status_code=404, detail=f"System stock not found for branch alias {branch_alias}")

    return {
        "varianceName": item["varianceName"],
      
        "systemStock": system_stock
    }
 
 
 
 
 
 
 
 
 # @router.get("/sys/")
# async def get_item_stock_details(
#     variance_names: list[str] = Query(..., description="List of variance names of the items"),
#     branch_aliases: list[str] = Query(..., description="List of branch aliases like AR, SB")
# ):
#     try:
#         cursor = branchwise_items_collection.find({}, {'_id': False})
#         items = await cursor.to_list(length=None)
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

#     # Process and extract relevant stock details for multiple variances and branches
#     stock_details = {}
#     for item in items:
#         # Clean the item dictionary to handle NaN values
#         cleaned_item = {k: (None if isinstance(v, float) and np.isnan(v) else v) for k, v in item.items()}
        
#         # Check if current item's variance name is in the list of variance names
#         current_variance_name = cleaned_item.get("varianceName")
#         if current_variance_name in variance_names:
#             # Iterate over branch keys relevant to stock
#             for branch_alias in branch_aliases:
#                 branch_keys = [key for key in cleaned_item.keys() if key.startswith("systemStock_") or key.startswith("physicalStock_")]
#                 for key in branch_keys:
#                     if key.endswith(f"_{branch_alias}"):  # Match branch alias suffix
#                         stock_type = "system" if "systemStock" in key else "physical"
#                         # Structure the result by variance and branch
#                         if current_variance_name not in stock_details:
#                             stock_details[current_variance_name] = {}
#                         if branch_alias not in stock_details[current_variance_name]:
#                             stock_details[current_variance_name][branch_alias] = {}
#                         stock_details[current_variance_name][branch_alias][f"{stock_type}_stock"] = cleaned_item[key]
    
#     if not stock_details:
#         raise HTTPException(status_code=404, detail="No stock information found for specified variances and branches")

#     return stock_details
 
 
 
 
    
 
# @router.patch("/patch-item23/{item_id}")
# async def patch_item(item_id: str, updates: Dict[str, Any]):
#     try:
#         item = await branchwise_items_collection.find_one({"_id": ObjectId(item_id)})
#         if not item:
#             raise HTTPException(status_code=404, detail="Item not found.")

#         # Update the specific fields in the item
#         for key, value in updates.items():
#             if key in item:
#                 item[key] = value
#             else:
#                 # Handle cases where the key might be a nested dictionary
#                 nested_keys = key.split(".")
#                 if len(nested_keys) > 1:
#                     current_level = item
#                     for nested_key in nested_keys[:-1]:
#                         if nested_key not in current_level:
#                             current_level[nested_key] = {}
#                         current_level = current_level[nested_key]
#                     current_level[nested_keys[-1]] = value
#                 else:
#                     item[key] = value

#         # Save the changes back to the collection
#         await branchwise_items_collection.update_one({"_id": ObjectId(item_id)}, {"$set": updates})

#         return {"message": "Item updated successfully"}
#     except Exception as exc:
#         raise HTTPException(status_code=500, detail=f"An error occurred while updating the item: {exc}")
   
    
    
#pagination optional  
# @router.get("/get-all-devices-pagination/")
# async def get_all_data(
#     page: int = Query(1, ge=1),  # Page number, default is 1
#     limit: int = Query(20, ge=1, le=100),  # Limit of items per page, default is 20
#     item_name: Optional[str] = Query(None),  # Optional search term for itemName
#     branch_alias: Optional[str] = Query(None),  # Optional query for branch alias
#     order_type: Optional[str] = Query(None),  # Optional query for order type
#     pagination: bool = Query(True)  # Enable pagination by default
# ) -> Dict[str, Any]:
#     # Create a query filter for itemName if provided
#     query_filter = {}
#     if item_name:
#         query_filter["itemName"] = {"$regex": item_name, "$options": "i"}  # Case-insensitive search

#     # Count total items for pagination metadata
#     total_items = await branchwise_items_collection.count_documents(query_filter)

#     # Calculate the number of items to skip
#     skip = (page - 1) * limit if pagination else 0
#     limit = limit if pagination else total_items

#     # Fetch data with pagination and search filter
#     data = await branchwise_items_collection.find(query_filter).skip(skip).limit(limit).to_list(None)

#     if not data:
#         raise HTTPException(status_code=404, detail="No data found")

#     def transform_item(item):
#         # Handle NaN values
#         item = {k: (None if pd.isna(v) else v) for k, v in item.items()}
#         item_name = item.get("itemName")

#         # Base item transformation
#         transformed_item = {
#             "item": {
#                 "branchwiseItemId": str(item.get("_id")),
#                 "itemName": item.get("itemName"),
#                 "category": item.get("category"),
#                 "subcategory": item.get("subCategory"),
#                 "itemGroup": item.get("itemGroup"),
#                 "ItemType": item.get("ItemType"),
#                 "item_Uom": item.get("item_Uom"),
#                 "tax": item.get("tax"),
#                 "item_Defaultprice": item.get("item_Defaultprice"),
#                 "description": item.get("description"),
#                 "hsnCode": item.get("hsnCode"),
#                 "status": item.get("status"),
#                 "create_item_date": item.get("create_item_date"),
#                 "updated_item_date": item.get("updated_item_date"),
#                 "netPrice": item.get("netPrice"),
#             },
#             "variance": {},
#         }

#         # Process flat structure variance (like first data example)
#         if "varianceName" in item:
#             variance_name = item.get("varianceName")
#             variance_info = {
#                 "varianceitemCode": item.get("varianceitemCode"),
#                 "varianceName": variance_name,
#                 "variance_Defaultprice": item.get("variance_Defaultprice"),
#                 "variance_Uom": item.get("variance_Uom"),
#                 "varianceStatus": "Active",
#                 "qrCode": None,
#                 "shelfLife": item.get("shelfLife"),
#                 "reorderLevel": item.get("reorderLevel"),
#                 "orderType": {},
#                 "branchwise": {},
#             }

#             # Dynamically handle orderType for flat structure
#             order_types = set([key.split('_')[0] for key in item.keys() if key.endswith('_Price') or key.endswith('_Enable')])
#             for o_type in order_types:
#                 if order_type is None or order_type == o_type:
#                     variance_info["orderType"][o_type] = {
#                         f"{o_type}_Price": item.get(f"{o_type}_Price"),
#                         f"{o_type}_Enable": item.get(f"{o_type}_Enable") == "y",
#                     }

#             # Dynamically handle branchwise for flat structure
#             branches = set([key.split('_')[1] for key in item.keys() if (key.startswith('Price_') or key.startswith('EnablePrice_') or key.startswith('branchwise_item_status_')) and key.split('_')[1] != 'item'])
#             for branch in branches:
#                 if branch_alias is None or branch_alias == branch:
#                     variance_info["branchwise"][branch] = {
#                         f"Price_{branch}": item.get(f"Price_{branch}"),
#                         f"EnablePrice_{branch}": item.get(f"EnablePrice_{branch}") == "y",
#                         f"itemStatus_{branch}": item.get(f"branchwise_item_status_{branch}") == "y",
#                         f"availableStock_{branch}": item.get(f"availableStock_{branch}", 0)
#                     }

#             transformed_item["variance"][variance_name] = variance_info

#         # Process nested structure variances (like second data example)
#         if "variances" in item:
#             for variance in item["variances"]:
#                 variance_name = variance.get("variance_name")
#                 variance_info = {
#                     "varianceitemCode": variance.get("varianceitemCode"),
#                     "varianceName": variance_name,
#                     "variance_Defaultprice": variance.get("variance_Defaultprice"),
#                     "variance_Uom": variance.get("variance_Uom"),
#                     "varianceStatus": "Active",
#                     "qrCode": None,
#                     "shelfLife": variance.get("shelfLife"),
#                     "reorderLevel": variance.get("reorderLevel"),
#                     "orderType": {},
#                     "branchwise": {},
#                 }

#                 # Filter orderType data based on order_type
#                 for o_type, details in variance.get("orderType", {}).items():
#                     if order_type is None or order_type == o_type:
#                         variance_info["orderType"][o_type] = details

#                 # Filter branchwise data based on branch_alias
#                 for branch, details in variance.get("branchwise", {}).items():
#                     if branch_alias is None or branch_alias == branch:
#                         variance_info["branchwise"][branch] = details

#                 transformed_item["variance"][variance_name] = variance_info

#         return item_name, transformed_item

#     transformed_data = {}
#     for item in data:
#         item_name, transformed_item = transform_item(item)
#         if item_name not in transformed_data:
#             transformed_data[item_name] = transformed_item
#         else:
#             transformed_data[item_name]["variance"].update(transformed_item["variance"])

#     # Calculate total pages
#     total_pages = (total_items + limit - 1) // limit if pagination else 1

#     return {
#         "page": page if pagination else 1,
#         "limit": limit if pagination else total_items,
#         "total_items": total_items,
#         "total_pages": total_pages,
#         "data": transformed_data
#     }



# upload_pdf

# @router.post("/upload-csv23/")
# async def upload_csv(file: UploadFile = File(...)):
#     content = await file.read()
#     df = pd.read_csv(io.BytesIO(content))
#     column_names = df.columns.tolist()
#     print(column_names)
#     return {"column_names": column_names}


# Endpoint to upload CSV


# pdf_collection = db["pdf"]  # Assuming 'db' is your MongoDB client's database

# @router.post("/upload-pdf/")
# async def upload_pdf(file: UploadFile = File(...)):
#     if file.content_type != 'application/pdf':
#         raise HTTPException(status_code=400, detail="Invalid file type. Only PDF files are accepted.")

#     # Ensure the directory exists
#     output_dir = Path("./uploaded_files")
#     output_dir.mkdir(parents=True, exist_ok=True)

#     file_location = output_dir / file.filename
#     try:
#         # Write the PDF to a file
#         with open(file_location, "wb") as f:
#             f.write(await file.read())

#         # Save file metadata to MongoDB
#         pdf_metadata = {
#             "filename": file.filename,
#             "content_type": file.content_type,
#             "file_path": str(file_location),
#             "uploaded_at": datetime.now()
#         }
#         result = await pdf_collection.insert_one(pdf_metadata)

#         return {
#             "status": "success",
#             "filename": file.filename,
#             "mongo_id": str(result.inserted_id)  # Return the MongoDB ID of the inserted document
#         }
#     except Exception as e:
#         return JSONResponse(status_code=500, content={"detail": str(e)})

# @router.get("/download-pdf/{pdf_id}")
# async def download_pdf(pdf_id: str):
#     try:
#         # Validate ObjectId
#         if not ObjectId.is_valid(pdf_id):
#             raise HTTPException(status_code=400, detail="Invalid MongoDB ID format.")

#         document = await pdf_collection.find_one({"_id": ObjectId(pdf_id)})
#         if not document:
#             raise HTTPException(status_code=404, detail="PDF not found.")

#         file_path = document['file_path']
#         if not Path(file_path).is_file():
#             raise HTTPException(status_code=404, detail="File does not exist.")

#         return FileResponse(path=file_path, filename=document['filename'], media_type='application/pdf')
#     except Exception as e:
#         return JSONResponse(status_code=500, content={"detail": str(e)})


# view-items Api
# def serialize_object_id(obj_id: ObjectId) -> str:
#     return str(obj_id)


# @router.get("/view-items/", response_model=Dict[str, Dict])
# async def get_items_by_branch_or_all(
#     branch_name: Optional[str] = None,
#     page: int = Query(1, ge=1),
#     limit: int = Query(20, ge=1, le=100),
# ):
#     skip = (page - 1) * limit
#     branchwise_items_query = {}
#     if branch_name:
#         branchwise_items_query = {
#             "$or": [
#                 {"branch": {"$elemMatch": {"branchName": branch_name}}},
#                 {"branch": {"$elemMatch": {"branchName": "All"}}},
#                 {"branchId": "All"},
#             ]
#         }

#     branchwise_items = await branchwise_items_collection.find(branchwise_items_query).skip(skip).limit(limit).to_list(None)
#     item_codes = [item.get("itemCode") for item in branchwise_items if "itemCode" in item]
#     item_id_map = {doc["itemCode"]: str(doc["_id"]) for doc in await items_collection23.find({"itemCode": {"$in": item_codes}}).to_list(None)}

#     results = {}
#     for item in branchwise_items:
#         item_id = str(item.pop("_id"))
#         item_name = item.get("itemName", "Unknown")
#         item_code = item.get("itemCode")
#         linked_item_id = item_id_map.get(item_code, None)

#         item_details = {
#             "itemName": item.get("itemName"),
#             "defaultprice": item.get("defaultprice"),
#             "uom": item.get("uom"),
#             "itemType": item.get("itemType"),
#             "create_item_Date": item.get("create_item_Date"),
#             "varianceItemcode": item.get("varianceItemcode"),
#             "subcategory": item.get("subcategory"),
#             "netPrice": item.get("netPrice"),
#             "reorderLevel": item.get("reorderLevel"),
#             "category": item.get("category"),
#             "itemGroup": item.get("itemGroup"),
#             "tax": item.get("tax"),
#             "price": item.get("price"),
#             "description": item.get("description"),
#             "hsnCode": item.get("hsnCode"),
#             "status": item.get("status"),
#         }

#         if item_name not in results:
#             results[item_name] = {
#                 "item": {
#                     "branchwiseItemId": item_id,
#                     "itemId": linked_item_id,
#                     **item_details,
#                 },
#                 "variance": {},
#             }

#         variance_name = item.get("varianceName")
#         if variance_name:
#             if variance_name not in results[item_name]["variance"]:
#                 results[item_name]["variance"][variance_name] = {
#                     "varianceName": variance_name,
#                      "uom": item.get("uom"),
#                     "defaultprice": item.get("defaultprice"),
#                 }

#     return results










# #  pip install pyzbar
# @router.get("/scan_qr")
# async def scan_qr():
#     # Initialize the camera
#     camera = cv2.VideoCapture(0)
#     start_time = time.time()
#     qr_code_data = None

#     try:
#         while time.time() - start_time < 5:  # Run for 10 seconds
#             success, frame = camera.read()  # Capture frame-by-frame
#             if not success:
#                 continue

#             # Decode QR codes in the frame
#             decoded_objects = decode(frame)
#             for obj in decoded_objects:
#                 qr_code_data = obj.data.decode('utf-8')  # Extract QR code data
#                 break

#             # If QR code is detected, break the loop
#             if qr_code_data:
#                 break
#     finally:
#         # Ensure the camera is released
#         camera.release()

#     if qr_code_data:
#         return {"qr_code_data": qr_code_data}
#     else:
#         return {"message": "No QR code detected in 10 seconds"}

# @router.on_event("shutdown")
# def shutdown_event():
#     # This is to ensure any open camera is released during shutdown
#     camera = cv2.VideoCapture(0)
#     camera.release()
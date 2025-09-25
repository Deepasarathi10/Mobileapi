import asyncio
import gc
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
from orderType.utils import get_orderType_collection
from .models import BranchwiseItem, BranchwiseItemPost, ItemUpdate,BranchwiseItemPatch,VarianceUpdate
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
from Branches.utils import get_branch_collection

router = APIRouter()
mongo_client = AsyncIOMotorClient("mongodb://admin:YenE580nOOUE6cDhQERP@194.233.78.90:27017/admin?appName=mongosh+2.1.1&authSource=admin&authMechanism=SCRAM-SHA-256&replicaSet=yenerp-cluster")
db = mongo_client["admin2"]
item_collection = db["fortest"]
branchwiseitem_collection = db["fortest"]

@router.post("/", response_model=str,status_code=status.HTTP_201_CREATED)
async def create_item(item: BranchwiseItemPost):
    result = await item_collection.insert_one(item.dict())
    return str(result.inserted_id)

branchwise_items_collection = db["fortest"]
variances_collection = db["variances"]
items_collection23 = db["items"]  # Items collection

branch_collection = get_branch_collection()


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
async def get_branchwise_promotional_items(
    branch_alias: str = Query(None, alias="branch_alias"),
    order_type: str = Query(None, alias="order_type"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100)
):
    try:
        # Fetch promotional offers
        promotional_offers_collection = get_collection(PROMOTIONAL_OFFERS_COLLECTION_NAME)
        promotional_offers = await promotional_offers_collection.find({}).to_list(length=None)

        # Fetch all branchwise items (include _id)
        cursor = branchwise_items_collection.find({})  # Remove {'_id': False} to include _id
        items = await cursor.to_list(length=None)
        
        # Synchronously fetch order types
        orderType_collection = get_orderType_collection()
        order_types = list(orderType_collection.find({}, {'_id': False}))

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    categories = set()
    merged_result = {}

    try:
        for item in items:
            item_name = item.get("itemName", "Unnamed")
            variance_name = item.get("varianceName", "Default")
            category = item.get("category", "Unknown")
            subcategory = item.get("subcategory", "Unknown")

            # Clean the item data
            cleaned_item = {
                k: (None if isinstance(v, float) and np.isnan(v) else v)
                for k, v in item.items()
            }

            # Initialize merge container
            if item_name not in merged_result:
                merged_result[item_name] = {"item": {}, "variance": {}}

            # Update category
            category = cleaned_item.get("category", "Uncategorized")
            categories.add(category)

            # Assign item attributes, including branchwiseItemId
            item_attributes = [
                "itemName", "category", "subCategory", "itemGroup",
                "ItemType", "item_Uom", "tax", "item_Defaultprice", "description", "hsnCode",
                "status", "create_item_date", "updated_item_date", "netPrice", "itemid"
            ]
            merged_result[item_name]["item"] = {
                k: cleaned_item[k] for k in item_attributes if k in cleaned_item
            }
            # Explicitly set branchwiseItemId
            merged_result[item_name]["item"]["branchwiseItemId"] = str(cleaned_item.get("_id"))

            # Process variance attributes
            variance_attributes = [
                "varianceid", "varianceitemCode", "varianceName", "variance_Defaultprice",
                "variance_Uom", "varianceStatus", "qrCode", "shelfLife", "reorderLevel"
            ]
            variance_info = {
                k: cleaned_item[k] for k in variance_attributes if k in cleaned_item
            }

            # Process branch-specific keys
            branchwise_info = {}
            branch_prefixes = [
                "Price_", "EnablePrice_", "systemStock_", "physicalStock_",
                "freeoffer_", "discountOffer_", "finalPrice_"
            ]
            for key, value in cleaned_item.items():
                if any(key.startswith(prefix) for prefix in branch_prefixes):
                    parts = key.split("_")
                    if len(parts) < 2:
                        continue
                    branch = parts[1]
                    if branch_alias and branch != branch_alias:
                        continue
                    branchwise_info.setdefault(branch, {})[key] = value

            # Process orderType keys
            for key, value in cleaned_item.items():
                if key.startswith("orderType_"):
                    parts = key.split("_")
                    if len(parts) < 3:
                        continue
                    branch = parts[1]
                    if branch_alias and branch != branch_alias:
                        continue
                    order_type_name = "_".join(parts[2:])
                    branch_data = branchwise_info.setdefault(branch, {})
                    order_type_dict = branch_data.setdefault("orderType", {})
                    order_type_dict[f"orderType_{branch}_{order_type_name}"] = value

            # Set default values for branch data
            for branch in branchwise_info.keys():
                branch_data = branchwise_info[branch]
                branch_data.setdefault(f"Price_{branch}", 0)
                branch_data.setdefault(f"freeoffer_{branch}", "false")
                branch_data.setdefault(f"discountOffer_{branch}", "false")
                branch_data.setdefault(f"finalPrice_{branch}", branch_data.get(f"Price_{branch}", 0))
                order_type_dict = branch_data.setdefault("orderType", {})
                for order in order_types:
                    ot_name = order.get("orderTypeName")
                    key_name = f"orderType_{branch}_{ot_name}"
                    order_type_dict.setdefault(key_name, "")

            # Process promotional offers
            for branch, branch_data in branchwise_info.items():
                branch_price = branch_data.get(f"Price_{branch}", 0)
                for offer in promotional_offers:
                    if branch_alias and branch not in offer.get("locations", []):
                        continue
                    if (
                        item_name in offer.get("itemName", []) or
                        variance_name in offer.get("varianceName", []) or
                        category in offer.get("category", []) or
                        subcategory in offer.get("subcategory", [])
                    ):
                        branch_data.update({
                            f"appTypes_{branch}": offer.get("appTypes", []),
                            f"offerName_{branch}": offer.get("offerName"),
                            f"locations_{branch}": offer.get("locations", []),
                            f"startDate_{branch}": offer.get("startDate"),
                            f"endDate_{branch}": offer.get("endDate"),
                            f"fromTime_{branch}": offer.get("fromTime"),
                            f"toTime_{branch}": offer.get("toTime"),
                            f"weekdays_{branch}": offer.get("weekdays", []),
                            f"selectionType_{branch}": offer.get("selectionType"),
                            f"itemName_{branch}": offer.get("itemName", []),
                            f"varianceName_{branch}": offer.get("varianceName", []),
                            f"category_{branch}": offer.get("category", []),
                            f"subcategory_{branch}": offer.get("subcategory", []),
                            f"configuration_{branch}": offer.get("configuration"),
                            f"discountValue_{branch}": offer.get("discountValue"),
                            f"orderValue_{branch}": offer.get("orderValue"),
                            f"orderDiscountValue_{branch}": offer.get("orderDiscountValue"),
                            f"customers_{branch}": offer.get("customers", []),
                            f"image_{branch}": offer.get("image"),
                            f"selectionType1_{branch}": offer.get("selectionType1"),
                            f"selectionType2_{branch}": offer.get("selectionType2"),
                            f"itemName1_{branch}": offer.get("itemName1", []),
                            f"itemName2_{branch}": offer.get("itemName2", []),
                            f"varianceName1_{branch}": offer.get("varianceName1", []),
                            f"varianceName2_{branch}": offer.get("varianceName2", []),
                            f"category1_{branch}": offer.get("category1", []),
                            f"category2_{branch}": offer.get("category2", []),
                            f"subcategory1_{branch}": offer.get("subcategory1", []),
                            f"subcategory2_{branch}": offer.get("subcategory2", []),
                            f"buy_{branch}": offer.get("buy", 0),
                            f"get_{branch}": offer.get("get", 0),
                            f"offerType_{branch}": offer.get("offerType"),
                            f"status_{branch}": offer.get("status"),
                            f"freeoffer_{branch}": offer.get("freeoffer", "false"),
                            f"discountOffer_{branch}": offer.get("discountOffer", "false")
                        })
                        if offer.get("discountOffer", "false") == "true":
                            try:
                                discount_value = float(offer.get("discountValue", 0) or 0)
                            except ValueError:
                                discount_value = 0
                            final_price = int(round(branch_price - (branch_price * discount_value / 100)))
                            branch_data[f"finalPrice_{branch}"] = str(final_price)

            # Merge variance data
            merged_result[item_name]["variance"].setdefault(variance_name, {}).update({
                **variance_info,
                "branchwise": branchwise_info
            })

        # Apply pagination
        merged_keys = sorted(merged_result.keys())
        total_items = len(merged_keys)
        start_index = (page - 1) * limit
        end_index = start_index + limit
        paginated_keys = merged_keys[start_index:end_index]
        paginated_result = { key: merged_result[key] for key in paginated_keys }

        total_pages = (total_items + limit - 1) // limit

        return {
            "page": page,
            "limit": limit,
            "total_items": total_items,
            "total_pages": total_pages,
            "data": paginated_result,
        }

    finally:
        del items, promotional_offers, cleaned_item, branchwise_info, variance_info
        gc.collect()

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
    The endpoint automatically assigns:
      - A new ObjectId for the item.
      - A new varianceitemCode if not provided (by finding the highest existing FG code
        and incrementing it, or defaulting to FG001 if none exist).
      - The default status "Active" if not provided.
      - A createdDate timestamp (current UTC datetime).
    """
    try:
        # Automatically generate a new ObjectId for the item.
        item_data["_id"] = ObjectId()
        
        # -------------------------------------------
        # Generate varianceitemCode if not provided
        # -------------------------------------------
        if not item_data.get("varianceitemCode"):
            # Query for varianceitemCodes from both top-level and nested variances.
            codes = await branchwise_items_collection.find(
                {}, {"varianceitemCode": 1, "variances.varianceitemCode": 1, "_id": 0}
            ).to_list(None)
            
            max_code = 0
            code_pattern = re.compile(r"FG(\d+)")
            
            # Loop over all returned documents
            for doc in codes:
                # Check for a top-level varianceitemCode
                if "varianceitemCode" in doc and doc["varianceitemCode"]:
                    match = code_pattern.match(doc["varianceitemCode"])
                    if match:
                        num = int(match.group(1))
                        if num > max_code:
                            max_code = num
                # If the document has nested variances, add their codes
                if "variances" in doc:
                    for variance in doc["variances"]:
                        if "varianceitemCode" in variance and variance["varianceitemCode"]:
                            match = code_pattern.match(variance["varianceitemCode"])
                            if match:
                                num = int(match.group(1))
                                if num > max_code:
                                    max_code = num
            
            # Calculate the next code number; if none found, max_code remains 0 and next_code becomes 1
            next_code_number = max_code + 1
            new_code = f"FG{next_code_number:03}"  # Formats number with leading zeros, e.g., FG001
            item_data["varianceitemCode"] = new_code
        
        # -------------------------------------------
        # Set default status if not provided
        # -------------------------------------------
        if not item_data.get("status"):
            item_data["status"] = "Active"
        
        # -------------------------------------------
        # Add a createdDate field with the current UTC datetime
        # -------------------------------------------
        item_data["createdDate"] = datetime.utcnow()
        
        # -------------------------------------------
        # Insert the item into the MongoDB collection
        # -------------------------------------------
        result = await branchwise_items_collection.insert_one(item_data)
        
        return {"message": "Item added successfully", "itemId": str(result.inserted_id)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
    
    
    
    
    
    
    



@router.get("/next-fgcode/")
async def get_next_varianceitemcode():
    try:
        # Fetch all documents and project only the nested varianceitemCode(s)
        codes = await branchwise_items_collection.find(
            {}, {"variances.varianceitemCode": 1, "_id": 0}
        ).to_list(None)
        
        # Initialize max_code to 0. If no valid code is found, the next code will be FG001.
        max_code = 0
        code_pattern = re.compile(r"FG(\d+)")
        
        # Loop over all returned documents
        for item in codes:
            # Get the list of variances; if not present, default to an empty list.
            variances = item.get("variances", [])
            for variance in variances:
                variance_code = variance.get("varianceitemCode", "")
                match = code_pattern.match(variance_code)
                if match:
                    # Convert the numeric part of the code to an integer
                    num = int(match.group(1))
                    # Update max_code if this number is greater
                    if num > max_code:
                        max_code = num
        
        # Calculate the next code number
        next_code_number = max_code + 1
        # Format the next code with leading zeros (e.g., FG001, FG002, ...)
        next_code = f"FG{next_code_number:03}"
        
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

    



PROMOTIONAL_OFFERS_COLLECTION_NAME = "promotionaloffer"



@router.patch("/update_stock")
async def update_stock(data: dict = Body(...)):
    branch_alias = data.get("branchAlias")
    variance_code = data.get("varianceCode")
    variance_name = data.get("varianceName")
    updated_stock = data.get("updatedStock")

    if not all([branch_alias, variance_code, variance_name, updated_stock]):
        raise HTTPException(status_code=400, detail="Missing required fields")

    # Update logic here (simplified example)
    result = await branchwise_items_collection.update_one(
        {
            f"variance.{variance_name}.varianceitemCode": variance_code
        },
        {
            "$set": {
                f"variance.{variance_name}.branchwise.{branch_alias}.localHiveStock_{branch_alias}": updated_stock
            }
        }
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Item not found or not updated")

    return {"status": "success", "message": "Stock updated"}


@router.get("/")
async def get_branchwise_promotional_items(
    branch_alias: str = Query(None, alias="branch_alias"),
    order_type: str = Query(None, alias="order_type")
):
    try:
        # Fetch promotional offers
        promotional_offers_collection = get_collection(PROMOTIONAL_OFFERS_COLLECTION_NAME)
        promotional_offers = await promotional_offers_collection.find({}).to_list(length=None)

        # Fetch branchwise items
        cursor = branchwise_items_collection.find({}, {'_id': False})
        items = await cursor.to_list(length=None)
        
        # Synchronously fetch order types (using PyMongo)
        orderType_collection = get_orderType_collection()
        order_types = list(orderType_collection.find({}, {'_id': False}))

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    categories = set()
    result = {}

    try:
        for item in items:
            item_name = item.get("itemName", "Unnamed")
            variance_name = item.get("varianceName", "Default")
            category = item.get("category", "Unknown")
            subcategory = item.get("subcategory", "Unknown")

            # Clean the item data
            cleaned_item = {
                k: (None if isinstance(v, float) and np.isnan(v) else v)
                for k, v in item.items()
            }

            if item_name not in result:
                result[item_name] = {"item": {}, "variance": {}}

            category = cleaned_item.get("category", "Uncategorized")
            categories.add(category)
            categories.discard("Uncategorized")
            # Assign item attributes        
            item_attributes = [
                "branchwiseItemId", "itemName", "category", "subCategory", "itemGroup",
                "ItemType", "item_Uom", "tax", "item_Defaultprice", "description", "hsnCode",
                "status", "create_item_date", "updated_item_date", "netPrice", "itemid"
            ]
            result[item_name]["item"] = {
                k: cleaned_item[k] for k in item_attributes if k in cleaned_item
            }

            # Process variance attributes
            variance_attributes = [
                "varianceid", "varianceitemCode", "varianceName", "variance_Defaultprice",
                "variance_Uom", "varianceStatus", "qrCode", "selfLife", "reorderLevel"
            ]
            variance_info = {
                k: cleaned_item[k] for k in variance_attributes if k in cleaned_item
            }

            # ---------------------------------------
            # Process branch-specific keys (prices, stocks, etc.)
            # ---------------------------------------
            branchwise_info = {}
            branch_prefixes = [
                "Price_", "EnablePrice_", "systemStock_", "physicalStock_",
                "freeoffer_", "discountOffer_", "finalPrice_"
            ]
            for key, value in cleaned_item.items():
                if any(key.startswith(prefix) for prefix in branch_prefixes):
                    parts = key.split("_")
                    if len(parts) < 2:
                        continue
                    branch = parts[1]  # e.g., "AR", "GH", etc.
                    if branch_alias and branch != branch_alias:
                        continue
                    # Save the key as is (so Price, freeoffer, etc. are retained)
                    branchwise_info.setdefault(branch, {})[key] = value

            # ---------------------------------------
            # Process orderType keys and nest them under "orderType"
            # ---------------------------------------
            for key, value in cleaned_item.items():
                if key.startswith("orderType_"):
                    parts = key.split("_")
                    if len(parts) < 3:
                        continue
                    branch = parts[1]
                    if branch_alias and branch != branch_alias:
                        continue
                    # Rejoin the remaining parts for the order type name
                    order_type_name = "_".join(parts[2:])
                    branch_data = branchwise_info.setdefault(branch, {})
                    # Use a nested dictionary for order types
                    order_type_dict = branch_data.setdefault("orderType", {})
                    order_type_dict[f"orderType_{branch}_{order_type_name}"] = value

            # ---------------------------------------
            # Optionally set defaults if keys are missing
            # ---------------------------------------
            for branch in branchwise_info.keys():
                branch_data = branchwise_info[branch]
                branch_data.setdefault(f"Price_{branch}", 0)
                branch_data.setdefault(f"freeoffer_{branch}", "false")
                branch_data.setdefault(f"discountOffer_{branch}", "false")
                branch_data.setdefault(f"finalPrice_{branch}", branch_data.get(f"Price_{branch}", 0))
                branch_data[f"localHiveStock_{branch}"] = 100
                # For each order type (from the orderType collection), set a default if not already provided
                order_type_dict = branch_data.setdefault("orderType", {})
                for order in order_types:
                    ot_name = order.get("orderTypeName")
                    key_name = f"orderType_{branch}_{ot_name}"
                    order_type_dict.setdefault(key_name, "")

            # ---------------------------------------
            # Process promotional offers per branch
            # ---------------------------------------
            for branch, branch_data in branchwise_info.items():
                branch_price = branch_data.get(f"Price_{branch}", 0)
                for offer in promotional_offers:
                    if branch_alias and branch not in offer.get("locations", []):
                        continue

                    # Match on item, variance, category, or subcategory
                    if (
                        item_name in offer.get("itemName", []) or
                        variance_name in offer.get("varianceName", []) or
                        category in offer.get("category", []) or
                        subcategory in offer.get("subcategory", [])
                    ):
                        branch_data.update({
                            f"appTypes_{branch}": offer.get("appTypes", []),
                            f"offerName_{branch}": offer.get("offerName"),
                            f"locations_{branch}": offer.get("locations", []),
                            f"startDate_{branch}": offer.get("startDate"),
                            f"endDate_{branch}": offer.get("endDate"),
                            f"fromTime_{branch}": offer.get("fromTime"),
                            f"toTime_{branch}": offer.get("toTime"),
                            f"weekdays_{branch}": offer.get("weekdays", []),
                            f"selectionType_{branch}": offer.get("selectionType"),
                            f"itemName_{branch}": offer.get("itemName", []),
                            f"varianceName_{branch}": offer.get("varianceName", []),
                            f"category_{branch}": offer.get("category", []),
                            f"subcategory_{branch}": offer.get("subcategory", []),
                            f"configuration_{branch}": offer.get("configuration"),
                            f"discountValue_{branch}": offer.get("discountValue"),
                            f"orderValue_{branch}": offer.get("orderValue"),
                            f"orderDiscountValue_{branch}": offer.get("orderDiscountValue"),
                            f"customers_{branch}": offer.get("customers", []),
                            f"image_{branch}": offer.get("image"),
                            f"selectionType1_{branch}": offer.get("selectionType1"),
                            f"selectionType2_{branch}": offer.get("selectionType2"),
                            f"itemName1_{branch}": offer.get("itemName1", []),
                            f"itemName2_{branch}": offer.get("itemName2", []),
                            f"varianceName1_{branch}": offer.get("varianceName1", []),
                            f"varianceName2_{branch}": offer.get("varianceName2", []),
                            f"category1_{branch}": offer.get("category1", []),
                            f"category2_{branch}": offer.get("category2", []),
                            f"subcategory1_{branch}": offer.get("subcategory1", []),
                            f"subcategory2_{branch}": offer.get("subcategory2", []),
                            f"buy_{branch}": offer.get("buy", 0),
                            f"get_{branch}": offer.get("get", 0),
                            f"offerType_{branch}": offer.get("offerType"),
                            f"status_{branch}": offer.get("status"),
                            f"freeoffer_{branch}": offer.get("freeoffer", "false"),
                            f"discountOffer_{branch}": offer.get("discountOffer", "false")
                        })

                        if offer.get("discountOffer", "false") == "true":
                            try:
                                discount_value = float(offer.get("discountValue", 0) or 0)
                            except ValueError:
                                discount_value = 0
                            final_price = int(round(branch_price - (branch_price * discount_value / 100)))
                            branch_data[f"finalPrice_{branch}"] = str(final_price)

            # ---------------------------------------
            # Update the result with variance and branchwise info
            # ---------------------------------------
            result[item_name]["variance"].setdefault(variance_name, {}).update({
                **variance_info,
                "branchwise": branchwise_info
            })

        if not result:
            raise HTTPException(status_code=404, detail="No items found for the given branch alias")

        return {
            "categories": list(categories),
            "data": result
        }

    finally:
        # Clean up
        del items, promotional_offers, cleaned_item, branchwise_info, variance_info
        gc.collect()  # Force garbage collection




@router.get("/get-variance-codes/")
async def get_variance_codes():
    """
    Returns a list of distinct varianceitemCode values from branchwise_items_collection.
    It checks for the code in both a top-level field 'varianceitemCode' and in nested variances.
    """
    try:
        # Project only the varianceitemCode at the top level and within nested 'variances'
        docs = await branchwise_items_collection.find(
            {}, {"varianceitemCode": 1, "variances.varianceitemCode": 1, "_id": 0}
        ).to_list(None)
        
        codes_set = set()
        for doc in docs:
            # Check for a top-level varianceitemCode
            if "varianceitemCode" in doc and doc["varianceitemCode"]:
                codes_set.add(doc["varianceitemCode"])
            # If the document has nested variances, add their varianceitemCode(s)
            if "variances" in doc:
                for variance in doc["variances"]:
                    if "varianceitemCode" in variance and variance["varianceitemCode"]:
                        codes_set.add(variance["varianceitemCode"])
        
        # Convert the set to a sorted list (optional)
        codes_list = sorted(list(codes_set))
        return {"varianceitemCodes": codes_list}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")



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


@router.patch("/update_systemstock")
async def update_system_stock(
    variance_names: List[str] = Body(..., description="List of variance names of the items to update"),
    branches: List[str] = Body(..., description="List of full branch names"),
    stock_updates: List[int] = Body(..., description="List of system stock counts to update")
):
    """Update system stock for multiple variances and branches."""
    try:
        
        if len(variance_names) != len(branches) or len(variance_names) != len(stock_updates):
            raise HTTPException(status_code=400, detail="The lengths of variance names, branches, and stock updates must match")
        
        update_responses = []
        
        for variance_name, branch_name, stock_update in zip(variance_names, branches, stock_updates):
            try:
                branch_doc = await branch_collection.find_one({"branchName": branch_name}, {"_id": 0, "aliasName": 1})
                
                if not branch_doc:
                    update_responses.append({
                        "varianceName": variance_name,
                        "branchName": branch_name,
                        "error": "Branch not found"
                    })
                    continue
                
                alias_name = branch_doc["aliasName"]
                
                update_result = await branchwiseitem_collection.update_one(
                    {"varianceName": variance_name},
                    {"$set": {f"systemStock_{alias_name}": stock_update}}
                )
                
                if update_result.modified_count == 0:
                    update_responses.append({
                        "varianceName": variance_name,
                        "branchName": branch_name,
                        "aliasName": alias_name,
                        "error": "Item not found or no update needed"
                    })
                    continue
                
                item = await branchwiseitem_collection.find_one({"varianceName": variance_name}, {"_id": 0})
                updated_value = item.get(f"systemStock_{alias_name}")
                
                update_responses.append({
                    "varianceName": variance_name,
                    "branchName": branch_name,
                    "aliasName": alias_name,
                    "updatedSystemStock": updated_value
                })
            
            except Exception as inner_err:
                print(f"🔥 Error updating {variance_name} for {branch_name}: {inner_err}")
                update_responses.append({
                    "varianceName": variance_name,
                    "branchName": branch_name,
                    "error": f"Update failed: {str(inner_err)}"
                })
        
        return {"status": "success", "updates": update_responses}
    
    except HTTPException as http_err:
        print(f"❌ HTTP error: {http_err.detail}")
        raise http_err
    except Exception as e:
        print(f"🔥 Unexpected server error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

    
 
 
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
 
@router.delete("/delete-variance/{variance_item_code}")
async def delete_variance(variance_item_code: str):
    """
    Endpoint to delete a document from branchwise_items_collection by varianceItemcode.
    """
    try:
        # Validate the variance_item_code
        if not variance_item_code:
            raise HTTPException(status_code=400, detail="Variance item code is required.")

        # Log the attempt
        print(f"Attempting to delete variance with varianceItemcode: {variance_item_code}")

        # First, try to delete a document where varianceItemcode is a top-level field
        # Check for both possible field names (case sensitivity)
        result = await branchwise_items_collection.delete_one(
            {"$or": [
                {"varianceItemcode": variance_item_code},
                {"varianceitemCode": variance_item_code}  # Alternative casing
            ]}
        )

        # Log the result of the top-level deletion attempt
        print(f"Top-level delete result: deleted_count={result.deleted_count}")

        # If no document was deleted, try deleting from a variances array (for backward compatibility)
        if result.deleted_count == 0:
            # Try multiple field name variations in the nested structure
            result = await branchwise_items_collection.update_one(
                {"$or": [
                    {"variances.varianceitemCode": variance_item_code},
                    {"variances.varianceItemcode": variance_item_code},  # Alternative casing
                    {"variances.variance_itemcode": variance_item_code}   # Snake case variation
                ]},
                {"$pull": {
                    "variances": {
                        "$or": [
                            {"varianceitemCode": variance_item_code},
                            {"varianceItemcode": variance_item_code},
                            {"variance_itemcode": variance_item_code}
                        ]
                    }
                }}
            )
            print(f"Nested variance delete result: modified_count={result.modified_count}")
            
            if result.modified_count == 0:
                # Check if the document exists at all with comprehensive search
                document = await branchwise_items_collection.find_one(
                    {"$or": [
                        {"varianceItemcode": variance_item_code},
                        {"varianceitemCode": variance_item_code},
                        {"variances.varianceitemCode": variance_item_code},
                        {"variances.varianceItemcode": variance_item_code},
                        {"variances.variance_itemcode": variance_item_code}
                    ]}
                )
                if document:
                    print(f"Document found but no deletion occurred: {document}")
                    # Log the actual structure to help debug
                    if 'variances' in document:
                        print(f"Variance structure: {document['variances']}")
                else:
                    print(f"No document found with varianceItemcode: {variance_item_code}")
                raise HTTPException(status_code=404, detail="Variance not found or no update made.")

        return {"message": "Variance deleted successfully", "varianceItemcode": variance_item_code}

    except HTTPException as http_exc:
        # Let HTTPExceptions (e.g., 400, 404) propagate unchanged
        raise http_exc
    except Exception as exc:
        # Log other unexpected errors
        print(f"Unexpected error deleting variance: {str(exc)}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(exc)}")


@router.delete("/delete-item23/{item_id}", status_code=status.HTTP_200_OK)
async def delete_item(item_id: str):
    try:
        # Validate the ObjectId
        if not ObjectId.is_valid(item_id):
            raise HTTPException(
                status_code=400,
                detail="Invalid branchwiseItemId format. Must be a valid MongoDB ObjectId."
            )

        # Attempt to delete the item
        result = await branchwise_items_collection.delete_one({"_id": ObjectId(item_id)})

        # Check if the item was deleted
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Item with branchwiseItemId {item_id} not found."
            )

        return {"message": "Item deleted successfully", "branchwiseItemId": item_id}
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while deleting the item: {str(exc)}"
        )



@router.patch("/update-variance/{variance_item_code}", status_code=200)
async def update_variance(variance_item_code: str, variance_update: VarianceUpdate):
    """
    Endpoint to update a variance by varianceItemcode in branchwise_items_collection.
    Supports updating both top-level and nested variance fields.
    """
    try:
        # Validate the variance_item_code
        if not variance_item_code:
            raise HTTPException(status_code=400, detail="Variance item code is required.")

        # Log the attempt
        print(f"Attempting to update variance with varianceItemcode: {variance_item_code}")

        # Filter out None values from updates
        update_data = {
            "$set": {
                key: val for key, val in variance_update.updates.items() if val is not None
            }
        }

        # First, try updating a document where varianceItemcode is a top-level field
        result = await branchwise_items_collection.update_one(
            {"$or": [
                {"varianceItemcode": variance_item_code},
                {"varianceitemCode": variance_item_code}
            ]},
            update_data
        )

        # Log the result of the top-level update attempt
        print(f"Top-level update result: modified_count={result.modified_count}")

        # If no document was updated, try updating a nested variance
        if result.modified_count == 0:
            result = await branchwise_items_collection.update_one(
                {"$or": [
                    {"variances.varianceitemCode": variance_item_code},
                    {"variances.varianceItemcode": variance_item_code},
                    {"variances.variance_itemcode": variance_item_code}
                ]},
                {
                    "$set": {
                        f"variances.$.{key}": val for key, val in variance_update.updates.items() if val is not None
                    }
                }
            )
            print(f"Nested variance update result: modified_count={result.modified_count}")

            if result.modified_count == 0:
                # Check if the variance exists
                document = await branchwise_items_collection.find_one(
                    {"$or": [
                        {"varianceItemcode": variance_item_code},
                        {"varianceitemCode": variance_item_code},
                        {"variances.varianceitemCode": variance_item_code},
                        {"variances.varianceItemcode": variance_item_code},
                        {"variances.variance_itemcode": variance_item_code}
                    ]}
                )
                if document:
                    print(f"Document found but no update occurred: {document}")
                    if 'variances' in document:
                        print(f"Variance structure: {document['variances']}")
                else:
                    print(f"No document found with varianceItemcode: {variance_item_code}")
                raise HTTPException(status_code=404, detail=f"Variance with code '{variance_item_code}' not found or no update made.")

        # Fetch the updated document to return
        updated_document = await branchwise_items_collection.find_one(
            {"$or": [
                {"varianceItemcode": variance_item_code},
                {"varianceitemCode": variance_item_code},
                {"variances.varianceitemCode": variance_item_code},
                {"variances.varianceItemcode": variance_item_code},
                {"variances.variance_itemcode": variance_item_code}
            ]}
        )

        if not updated_document:
            raise HTTPException(status_code=404, detail="Updated variance not found.")

        return {
            "message": "Variance updated successfully",
            "varianceItemcode": variance_item_code,
            "updatedFields": variance_update.updates
        }

    except HTTPException as http_exc:
        raise http_exc
    except Exception as exc:
        print(f"Unexpected error updating variance: {str(exc)}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(exc)}")


@router.patch("/update-item-by-id/{item_id}", status_code=200)
async def update_item_by_id(item_id: str, item_update: ItemUpdate):
    """
    Endpoint to update an item by its MongoDB _id in branchwise_items_collection.
    """
    try:
        # Validate the ObjectId
        if not ObjectId.is_valid(item_id):
            raise HTTPException(
                status_code=400,
                detail="Invalid item ID format. Must be a valid MongoDB ObjectId."
            )

        # Filter out None values from updates
        update_data = {
            "$set": {
                key: val for key, val in item_update.updates.items() if val is not None
            }
        }

        # Update the item
        result = await branchwise_items_collection.update_one(
            {"_id": ObjectId(item_id)},
            update_data
        )

        # Check if the item was updated
        if result.modified_count == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Item with ID {item_id} not found or no update made."
            )

        # Fetch the updated document
        updated_item = await branchwise_items_collection.find_one({"_id": ObjectId(item_id)})
        if not updated_item:
            raise HTTPException(status_code=404, detail="Updated item not found.")

        # Convert _id to branchwiseItemId for frontend compatibility
        updated_item["branchwiseItemId"] = str(updated_item.pop("_id"))
        return {
            "message": "Item updated successfully",
            "branchwiseItemId": updated_item["branchwiseItemId"],
            "updatedFields": item_update.updates,
            "updatedItem": updated_item
        }

    except HTTPException as http_exc:
        raise http_exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(exc)}")



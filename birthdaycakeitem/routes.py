import base64
import datetime
from fileinput import filename
import ftplib
import io
import json
import logging
import math
import os
import shutil
import tempfile
from tkinter import Image
import zipfile
from fastapi.responses import FileResponse, JSONResponse
import numpy as np
import pandas as pd
from fastapi import APIRouter, BackgroundTasks, Body, File, Form, HTTPException, Request, UploadFile
from bson import ObjectId
from typing import Any, Dict, List
import rarfile # Ensure you have installed rarfile and an extraction tool (e.g., unrar or unar)
import re
from pydantic import BaseModel
from datetime import datetime
from PIL import Image

from appitemimageserver.utils import get_cakeappimage_collection
# from cakeupload.routes import cleanup_dir
from .models import BirthdayCakeItem, BirthdayCakeItemPost, Variance  # ✅ Ensure Variance is imported

from .utils import get_BirthdayCakeItem_collection, convert_to_string_or_emptys
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection

# Get the MongoDB collections
item_collection = get_BirthdayCakeItem_collection()
image_collection = get_cakeappimage_collection()


FTP_HOST = "194.233.78.90"
FTP_USER = "yenerp.com_thys677l7kc"
FTP_PASSWORD = "PUTndhivxi6x94^%"
FTP_UPLOAD_DIR = "/httpdocs/share/upload/birthdaycakeapp/birthdaycakeimages"
BASE_URL = "https://yenerp.com/share/upload"


router = APIRouter()

async def get_next_fg_code_number():
    collection = await get_BirthdayCakeItem_collection()
    cursor = collection.find({"itemCode": {"$regex": "^FGB\\d+$"}}, {"itemCode": 1})
    items = await cursor.to_list(length=None)

    max_code = 0
    for item in items:
        match = re.match(r"FGB(\d+)", item.get("itemCode", ""))
        if match:
            max_code = max(max_code, int(match.group(1)))

    return max_code + 1


def compress_image(image_bytes: bytes, max_size: int = 800) -> bytes:
    image = Image.open(io.BytesIO(image_bytes))
    image = image.convert("RGB")
    if max(image.size) > max_size:
        image.thumbnail((max_size, max_size))
    output_io = io.BytesIO()
    image.save(output_io, format="WebP", quality=70)
    return output_io.getvalue()

async def upload_to_ftp(file_content: bytes, file_name: str) -> str:
    try:
        with ftplib.FTP() as ftp:
            ftp.set_pasv(True)
            ftp.connect(FTP_HOST, 21, timeout=10)
            ftp.login(FTP_USER, FTP_PASSWORD)
            ftp.cwd(FTP_UPLOAD_DIR)
            with io.BytesIO(file_content) as file_stream:
                ftp.storbinary(f"STOR {file_name}", file_stream)
        return f"{BASE_URL}/birthdaycakeapp/birthdaycakeimages/{file_name}"
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"FTP upload failed: {e}")


@router.post("/", response_model=str)
async def create_BirthdayCakeItem(
    image: UploadFile = File(...),
    category: str = Form(...),
    appItemName: str = Form(...),
    itemName: str = Form(...),
    variant: str = Form(...),
    flavour: str = Form(...),  # comma-separated string
    tax: float = Form(...),
    pricefor1kg: float = Form(...),
    hsnCode: int = Form(...),
    type: str = Form(...),
    description: str = Form(""),
    stockQuantity: int = Form(0),
    offer: float = Form(0.0),
    variances: str = Form(...),
    status: str = Form("1")
    
):
    try:
        # ✅ 1. Generate itemCode
        next_number = await get_next_fg_code_number()
        itemCode = f"FGB{next_number:03d}"

        # ✅ 2. Upload and save image in separate collection
        image_bytes = await image.read()
        compressed = compress_image(image_bytes)
        filename = f"{itemCode}.webp"
        ftp_url = await upload_to_ftp(compressed, filename)

        image_collection = await get_cakeappimage_collection()

        await image_collection.insert_one({
            "_id": ObjectId(),
            "itemCode": itemCode,
            "ftpPath": ftp_url,
            "createdDate": datetime.utcnow()
        })

        # ✅ 3. Price calculation
        price = round(pricefor1kg * 1, 2)
        final_price = round(price - (price * offer / 100), 2)
        if math.isnan(price) or math.isinf(price): price = 0.0
        if math.isnan(final_price) or math.isinf(final_price): final_price = 0.0

        # ✅ 4. Flavour as list
        flavour_list = [f.strip() for f in flavour.split(",") if f.strip()]

        # ✅ 5. Insert item (without image) into main collection
        item_data = {
            "_id": ObjectId(),
            "itemCode": itemCode,
            "category": category,
            "appItemName": appItemName,
            "itemName": itemName,
            "variant": variant,
            "flavour": flavour_list,
            "tax": tax,
            "pricefor1kg": pricefor1kg,
            "finalPrice": final_price,
            "hsnCode": hsnCode,
            "type": type,
            "description": description,
            "stockQuantity": stockQuantity,
            
            "variances": json.loads(variances),
            "status": status,
            "createdDate": datetime.utcnow()
        }

        item_collection = await get_BirthdayCakeItem_collection()
        result = await item_collection.insert_one(item_data)

        return str(result.inserted_id)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")




# @router.post("/", response_model=str)
# async def create_BirthdayCakeItem(item: BirthdayCakeItemPost):
#     # Calculate the price based on the selected variant
#     base_price_per_kg = item.pricefor1kg or 0  # Ensure it's not None
#     offer_percentage = item.offer or 0
#     weight = item.selected_variant_kg or 1  # Default to 1kg if not provided
    
#     price = base_price_per_kg * weight
#     final_price = price - (price * offer_percentage / 100)

#     # Ensure valid numbers (no NaN or inf)
#     if math.isnan(price) or math.isinf(price):
#         price = 0.0
#     if math.isnan(final_price) or math.isinf(final_price):
#         final_price = 0.0

#     price = round(price, 2)
#     final_price = round(final_price, 2)

#     # Construct the item with calculated variant
#     new_BirthdayCakeItem = {
#         "name": item.name,
#         "pricefor1kg": base_price_per_kg,
#         "offer": offer_percentage,
#         "variant": {
#             "kg": f"{weight}kg",
#             "price": price,
#             "finalPrice": final_price,
#             "qrcode": f"qrcode_{weight}kg"
#         }
#     }
    
#     # Store in MongoDB
#     result = get_BirthdayCakeItem_collection().insert_one(new_BirthdayCakeItem)
#     return str(result.inserted_id)  # ✅ Corrected return statement


def clean_floats(data):
    """
    Recursively replace NaN, Infinity values, and convert datetime to strings.
    """
    if isinstance(data, list):
        return [clean_floats(item) for item in data]
    elif isinstance(data, dict):
        return {key: clean_floats(value) for key, value in data.items()}
    elif isinstance(data, float):
        if math.isnan(data) or math.isinf(data):
            return 0.0
        return data
    elif isinstance(data, datetime):
        return data.isoformat()  
    return data


@router.get("/")
async def get_all_BirthdayCakeItems():
    try:
        collection = await get_BirthdayCakeItem_collection()
        cursor = collection.find()
        items = await cursor.to_list(length=None)

        # Convert MongoDB ObjectId to a string and assign it to birthdayCakeId
        for item in items:
            item["birthdayCakeId"] = str(item.pop("_id"))
        
        cleaned_items = clean_floats(items)
        return JSONResponse(content=cleaned_items)
    except Exception as e:
        logging.error(f"Error fetching BirthdayCakeItems: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving cake items")


    
@router.get("/{birthdayCakeId}", response_model=BirthdayCakeItem)
async def get_BirthdayCakeItem_by_id(birthdayCakeId: str):
    collection = await get_BirthdayCakeItem_collection()  # ✅ await the coroutine
    item = await collection.find_one({"itemCode": birthdayCakeId})  # ✅ Use itemCode if you're not using _id

    if item:
        item["_id"] = str(item["_id"])
        item["birthdayCakeId"] = item["_id"]
        return BirthdayCakeItem(**convert_to_string_or_emptys(item))
    else:
        raise HTTPException(status_code=404, detail="BirthdayCakeItem not found")

    
@router.put("/{birthdayCakeId}")
async def update_BirthdayCakeItem(birthdayCakeId: str, BirthdayCakeItem: BirthdayCakeItemPost):
    updated_fields = BirthdayCakeItem.dict(exclude_unset=True)

    # Ensure the variances are updated correctly
    if 'variances' in updated_fields:
        for variance in updated_fields['variances']:
            if variance.get('price') is not None and variance.get('offer') is not None:
                variance['finalPrice'] = round(
                    variance['price'] - (variance['price'] * variance['offer'] / 100), 2
                )

    # ✅ Await the collection and the update call
    collection = await get_BirthdayCakeItem_collection()
    result = await collection.update_one(
        {"_id": ObjectId(birthdayCakeId)},
        {"$set": updated_fields}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="BirthdayCakeItem not found")

    return {"message": "BirthdayCakeItem updated successfully"}


# @router.put("/{birthdayCakeId}")
# async def update_BirthdayCakeItem(birthdayCakeId: str, BirthdayCakeItem: BirthdayCakeItemPost):
#     updated_fields = BirthdayCakeItem.dict(exclude_unset=True)

#     # Ensure the variances are updated correctly
#     if 'variances' in updated_fields:
#         for variance in updated_fields['variances']:
#             if variance.get('price') is not None and variance.get('offer') is not None:
#                 variance['finalPrice'] = round(variance['price'] - (variance['price'] * variance['offer'] / 100), 2)
    
#     result = get_BirthdayCakeItem_collection().update_one(
#         {"_id": ObjectId(birthdayCakeId)},
#         {"$set": updated_fields}
#     )
#     if result.modified_count == 0:
#         raise HTTPException(status_code=404, detail="BirthdayCakeItem not found")
#     return {"message": "BirthdayCakeItem updated successfully"}

@router.delete("/{birthdayCakeId}")
async def delete_BirthdayCakeItem(birthdayCakeId: str):
    result = get_BirthdayCakeItem_collection().delete_one({"_id": ObjectId(birthdayCakeId)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="BirthdayCakeItem not found")
    return {"message": "BirthdayCakeItem deleted successfully"}

@router.patch("/{birthdayCakeId}/deactivate")
async def deactivate_BirthdayCakeItem(birthdayCakeId: str):
    try:
        # Convert the birthdayCakeId (a string) back to an ObjectId
        obj_id = ObjectId(birthdayCakeId)
    except Exception as e:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid birthdayCakeId format: {birthdayCakeId}"
        ) from e

    # Await the collection before calling update_one
    collection = await get_BirthdayCakeItem_collection()
    result = await collection.update_one(
        {"_id": obj_id},
        {"$set": {"status": "0"}}
    )

    if result.matched_count == 0:
        raise HTTPException(
            status_code=404, 
            detail=f"BirthdayCakeItem with ID {birthdayCakeId} not found"
        )
    return {"message": "BirthdayCakeItem deactivated successfully"}


@router.patch("/{birthdayCakeId}/activate")
async def activate_BirthdayCakeItem(birthdayCakeId: str):
    try:
        obj_id = ObjectId(birthdayCakeId)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid birthdayCakeId format: {birthdayCakeId}") from e
    
    result = get_BirthdayCakeItem_collection().update_one(
        {"_id": obj_id},
        {"$set": {"status": "1"}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail=f"BirthdayCakeItem with ID {birthdayCakeId} not found")
    return {"message": "BirthdayCakeItem activated successfully"}

@router.post("/import")
async def import_excel(file: UploadFile):
    try:
        # Read uploaded file
        contents = await file.read()
        filename = file.filename.lower()

        # Detect file type and read into DataFrame
        if filename.endswith('.csv'):
            try:
                df = pd.read_csv(io.BytesIO(contents), encoding='utf-8')
            except UnicodeDecodeError:
                df = pd.read_csv(io.BytesIO(contents), encoding='windows-1252')
        elif filename.endswith('.xls') or filename.endswith('.xlsx'):
            df = pd.read_excel(io.BytesIO(contents), engine='openpyxl')
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format. Please upload CSV or Excel file.")

        # ✅ Rename Columns
        column_mapping = {
            "name": "itemName",
            "kg": "Kg",
            "tax": "taxPercentage",
            "hsnCode": "hsCode",
            "stockQuantity": "availableStock",
            "finalPrice": "pricefor1kg",
            "description ": "description"  # Fix column name with trailing space
        }
        df.rename(columns=column_mapping, inplace=True)

        # ✅ Define Flavour Columns
        flavour_columns = ["chocolate", "strawberry", "butterScotch", "mango", "freshCream",
                           "blackCurrant", "redVelvet", "blackForest", "whiteForest", "blueBerry"]

        # ✅ Extract Multiple Flavours into an Array
        def extract_flavours(row):
            return [flavour.capitalize() for flavour in flavour_columns if str(row.get(flavour, "N")).strip().lower() == "y"]

        df["flavour"] = df.apply(extract_flavours, axis=1)
        df.drop(columns=[col for col in flavour_columns if col in df.columns], inplace=True)

        # ✅ Calculate Variances (Price per Weight)
        def calculate_variances(row):
            try:
                base_price = float(row["pricefor1kg"])
            except (TypeError, ValueError):
                base_price = 0

            offer = float(row.get("offer", 0))
            variant = str(row.get("variant", "0.5kg -10kg")).strip()

            match = re.findall(r"(\d*\.?\d+)", variant)
            if len(match) != 2:
                print(f"⚠ Invalid Variant Format: {variant}")
                return []

            start_weight, end_weight = map(float, match)
            weight_steps = []
            current_weight = start_weight
            while current_weight <= end_weight:
                weight_steps.append(round(current_weight, 1))
                current_weight += 0.5

            variances = []
            for weight in weight_steps:
                price = round(base_price * weight, 2)
                final_price = round(price - (price * offer / 100), 2)

                variances.append({
                    "kg": f"{weight}kg",
                    "price": price,
                    "offer": offer,
                    "finalPrice": final_price,
                    "qrcode": f"qrcode_{weight}kg"
                })

            return variances

        df["variances"] = df.apply(calculate_variances, axis=1)

        # ✅ Convert DataFrame to List of Dictionaries
        items = df.to_dict(orient="records")

        # ✅ Fetch FGCodes & Assign to Items
        collection = await get_BirthdayCakeItem_collection()
        fg_counter = await get_next_fg_code_number()

        for item in items:
            item["_id"] = ObjectId()
            item["createdDate"] = datetime.utcnow()
            item["itemCode"] = f"FGB{fg_counter:03d}"
            fg_counter += 1

        # ✅ Insert into MongoDB
        result = await collection.insert_many(items)

        return {"message": "File imported successfully", "inserted_count": len(result.inserted_ids)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
# @router.post("/import")
# async def import_excel(file: UploadFile):
#     try:
#         # Read uploaded file
#         contents = await file.read()
#         filename = file.filename.lower()

#         # Detect file type
#         if filename.endswith('.csv'):
#             df = pd.read_csv(io.BytesIO(contents))
#         elif filename.endswith('.xls') or filename.endswith('.xlsx'):
#             df = pd.read_excel(io.BytesIO(contents), engine='openpyxl')
#         else:
#             raise HTTPException(status_code=400, detail="Unsupported file format. Please upload CSV or Excel file.")

#         # ✅ Rename Columns
#         column_mapping = {
#             "name": "itemName",
#             "kg": "Kg",
#             "tax": "taxPercentage",
#             "hsnCode": "hsCode",
#             "stockQuantity": "availableStock",
#             "finalPrice": "pricefor1kg"
#         }
#         df.rename(columns=column_mapping, inplace=True)

#         # ✅ Define Flavour Columns
#         flavour_columns = ["chocolate", "strawberry", "butterScotch", "mango", "freshCream",
#                            "blackCurrant", "redVelvet", "blackForest", "whiteForest", "blueBerry"]

#         # ✅ Extract Multiple Flavours into an Array
#         def extract_flavours(row):
#             return [flavour.capitalize() for flavour in flavour_columns if str(row.get(flavour, "N")).strip().lower() == "y"]

#         df["flavour"] = df.apply(extract_flavours, axis=1)
#         df.drop(columns=[col for col in flavour_columns if col in df.columns], inplace=True)

#         # ✅ Calculate Variances (Price per Weight)
#         def calculate_variances(row):
#             try:
#                 base_price = float(row["pricefor1kg"])
#             except (TypeError, ValueError):
#                 base_price = 0

#             offer = float(row.get("offer", 0))
#             variant = str(row.get("variant", "0.5kg -10kg")).strip()

#             match = re.findall(r"(\d*\.?\d+)", variant)
#             if len(match) != 2:
#                 print(f"⚠ Invalid Variant Format: {variant}")
#                 return []

#             start_weight, end_weight = map(float, match)
#             weight_steps = []
#             current_weight = start_weight
#             while current_weight <= end_weight:
#                 weight_steps.append(round(current_weight, 1))
#                 current_weight += 0.5

#             variances = []
#             for weight in weight_steps:
#                 price = round(base_price * weight, 2)
#                 final_price = round(price - (price * offer / 100), 2)

#                 variances.append({
#                     "kg": f"{weight}kg",
#                     "price": price,
#                     "offer": offer,
#                     "finalPrice": final_price,
#                     "qrcode": f"qrcode_{weight}kg"
#                 })

#             return variances

#         df["variances"] = df.apply(calculate_variances, axis=1)

#         # ✅ Convert DataFrame to List of Dictionaries
#         items = df.to_dict(orient="records")

#         # ✅ Fetch FGCodes & Assign to Items
#         collection = await get_BirthdayCakeItem_collection()
        
#         max_code = await get_next_fg_code_number()
#         fg_counter = await get_next_fg_code_number()



#         for item in items:
#             item["_id"] = ObjectId()
#             item["createdDate"] = datetime.utcnow()
#             item["itemCode"] = f"FGB{fg_counter:03d}"
#             fg_counter += 1


#         # ✅ Insert into MongoDB
#         result = await collection.insert_many(items)

#         return {"message": "File imported successfully", "inserted_count": len(result.inserted_ids)}

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
# rarfile.UNRAR_TOOL = r"C:\Program Files\WinRAR\UnRAR.exe"

# def cleanup_dir(dir_path: str):
#     try:
#         shutil.rmtree(dir_path)
#     except Exception as e:
#         print(f"Error cleaning up temporary directory {dir_path}: {e}")

@router.post("/upload_archive")
async def upload_archive(archive_file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    """
    Upload a ZIP or RAR file containing a folder of image files.
    """
    filename = archive_file.filename
    if not (filename.endswith('.zip') or filename.endswith('.rar')):
        raise HTTPException(status_code=400, detail="Uploaded file must be a ZIP or RAR file.")

    # Create a temporary directory that persists until cleanup.
    temp_dir = tempfile.mkdtemp()

    # Save the uploaded archive in the temp directory.
    temp_archive_path = os.path.join(temp_dir, filename)
    with open(temp_archive_path, "wb") as f:
        f.write(await archive_file.read())

    # Extract the archive based on its extension.
    if filename.endswith('.zip'):
        with zipfile.ZipFile(temp_archive_path, "r") as archive:
            archive.extractall(temp_dir)
    else:  # For .rar files
        try:
            with rarfile.RarFile(temp_archive_path) as archive:
                archive.extractall(temp_dir)
        except rarfile.Error as e:
            shutil.rmtree(temp_dir)
            raise HTTPException(status_code=400, detail=f"Failed to extract RAR file: {str(e)}")

    # ✅ Await the collection
    collection = await get_BirthdayCakeItem_collection()

    processed_files = []  # List of tuples: (full_file_path, new_filename)

    # Walk through the temporary directory to process image files.
    for root, dirs, files in os.walk(temp_dir):
        for file in files:
            if file == filename:
                continue
            if not file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')):
                continue

            file_path = os.path.join(root, file)
            base_name = file.rsplit(".", 1)[0].strip()

            # ✅ Await the MongoDB document lookup
            document = await collection.find_one({
                "itemName": {"$regex": f"^{base_name}$", "$options": "i"}
            })

            if not document:
                continue

            file_extension = os.path.splitext(file)[1]
            new_filename = f"{document['itemCode']}{file_extension}"
            new_file_path = os.path.join(root, new_filename)

            os.rename(file_path, new_file_path)
            processed_files.append((new_file_path, new_filename))

    if not processed_files:
        shutil.rmtree(temp_dir)
        raise HTTPException(
            status_code=404,
            detail="No valid BirthdayCakeItem documents found for the uploaded images."
        )

    # Create a ZIP archive of the processed images
    output_zip_path = os.path.join(temp_dir, "processed_images.zip")
    with zipfile.ZipFile(output_zip_path, "w") as zip_out:
        for file_path, new_filename in processed_files:
            zip_out.write(file_path, arcname=new_filename)

    # Cleanup after response
    if background_tasks is None:
        background_tasks = BackgroundTasks()
    background_tasks.add_task( temp_dir)

    return FileResponse(
        path=output_zip_path,
        filename="processed_images.zip",
        media_type="application/zip",
        background=background_tasks
    )

# rarfile.UNRAR_TOOL = r"C:\Program Files\WinRAR\UnRAR.exe"

# def cleanup_dir(dir_path: str):
#     try:
#         shutil.rmtree(dir_path)
#     except Exception as e:
#         print(f"Error cleaning up temporary directory {dir_path}: {e}")
        
        
        


# STATIC_DIR = "static/processed_images"
# os.makedirs(STATIC_DIR, exist_ok=True)
# IMAGE_DIR = "static/processed_images"
# @router.post("/upload_archive")
# async def upload_archive(archive_file: UploadFile = File(...)):
#     """
#     Uploads an archive (ZIP or RAR), extracts images, renames them based on 
#     MongoDB records (by itemName), stores them in a static folder using itemCode, and prevents duplicates.
#     """
#     filename = archive_file.filename
#     if not (filename.endswith('.zip') or filename.endswith('.rar')):
#         raise HTTPException(status_code=400, detail="Uploaded file must be a ZIP or RAR file.")

#     temp_dir = tempfile.mkdtemp()

#     try:
#         temp_archive_path = os.path.join(temp_dir, filename)
#         with open(temp_archive_path, "wb") as f:
#             f.write(await archive_file.read())

#         # Extract archive contents
#         if filename.endswith('.zip'):
#             with zipfile.ZipFile(temp_archive_path, "r") as archive:
#                 archive.extractall(temp_dir)
#         else:
#             try:
#                 with rarfile.RarFile(temp_archive_path) as archive:
#                     archive.extractall(temp_dir)
#             except rarfile.Error as e:
#                 raise HTTPException(status_code=400, detail=f"Failed to extract RAR file: {str(e)}")

#         item_collection = await get_BirthdayCakeItem_collection()
#         image_collection = get_cakeappimage_collection()  # Sync collection

#         uploaded_images = []

#         # Walk through extracted files
#         for root, _, files in os.walk(temp_dir):
#             for file in files:
#                 if file == filename or not file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')):
#                     continue

#                 file_path = os.path.join(root, file)
#                 base_name = file.rsplit(".", 1)[0].strip()

#                 # Lookup by itemName (case-insensitive)
#                 document = await item_collection.find_one({
#                     "itemName": {"$regex": f"^{re.escape(base_name)}$", "$options": "i"}
#                 })

#                 if not document:
#                     logging.info(f"No item found for image: {base_name}")
#                     continue

#                 # Get itemCode
#                 item_code = document.get("itemCode")
#                 if not item_code:
#                     logging.warning(f"ItemCode missing for: {base_name}")
#                     continue

#                 # Rename using itemCode
#                 file_extension = os.path.splitext(file)[1]
#                 new_filename = f"{item_code}{file_extension}"
#                 new_file_path = os.path.join(STATIC_DIR, new_filename)

#                 shutil.move(file_path, new_file_path)

#                 # Construct URL
#                 file_url = f"https://yenerp.com/share/upload/birthdaycakeapp/birthdaycakeimages/{new_filename}"

#                 # Check for duplicates (SYNC)
#                 existing_image = image_collection.find_one({
#                     "item_id": document["_id"],
#                     "ftp_path": file_url
#                 })

#                 if existing_image:
#                     continue  # Already exists

#                 # Insert into MongoDB (SYNC)
#                 image_collection.insert_one({
#                     "item_id": document["_id"],
#                     "ftp_path": file_url
#                 })

#                 uploaded_images.append({
#                     "original": file,
#                     "itemCode": item_code,
#                     "new_filename": new_filename,
#                     "url": file_url
#                 })

#         if not uploaded_images:
#             raise HTTPException(status_code=404, detail="No new images found.")

#         return JSONResponse(content={"uploaded_images": uploaded_images})

#     finally:
#         shutil.rmtree(temp_dir, ignore_errors=True)

# @router.post("/upload_archive")
# async def upload_archive(archive_file: UploadFile = File(...)):
#     """
#     Uploads an archive (ZIP or RAR), extracts images, renames them based on 
#     MongoDB records, stores them in a static folder, and prevents duplicates.
#     """
#     filename = archive_file.filename
#     if not (filename.endswith('.zip') or filename.endswith('.rar')):
#         raise HTTPException(status_code=400, detail="Uploaded file must be a ZIP or RAR file.")

#     temp_dir = tempfile.mkdtemp()

#     try:
#         temp_archive_path = os.path.join(temp_dir, filename)
#         with open(temp_archive_path, "wb") as f:
#             f.write(await archive_file.read())

#         # Extract the archive
#         if filename.endswith('.zip'):
#             with zipfile.ZipFile(temp_archive_path, "r") as archive:
#                 archive.extractall(temp_dir)
#         else:
#             try:
#                 with rarfile.RarFile(temp_archive_path) as archive:
#                     archive.extractall(temp_dir)
#             except rarfile.Error as e:
#                 raise HTTPException(status_code=400, detail=f"Failed to extract RAR file: {str(e)}")

#         item_collection = await get_BirthdayCakeItem_collection()
#         image_collection =  get_cakeappimage_collection()

#         uploaded_images = []

#         # Walk through extracted files
#         for root, _, files in os.walk(temp_dir):
#             for file in files:
#                 if file == filename or not file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')):
#                     continue

#                 file_path = os.path.join(root, file)
#                 base_name = file.rsplit(".", 1)[0].strip()

#                 # Look up a matching document (case-insensitive)
#                 document = await item_collection.find_one({
#                     "itemName": {"$regex": f"^{base_name}$", "$options": "i"}
#                 })
#                 if not document:
#                    logging.info(f"No item found for image: {base_name}")
#                    continue

#                 # Rename and move file to static directory
#                 file_extension = os.path.splitext(file)[1]
#                 new_filename = f"{document['_id']}{file_extension}"
#                 new_file_path = os.path.join(STATIC_DIR, new_filename)
#                 shutil.move(file_path, new_file_path)

#                 # Generate public URL for the file
#                 file_url = f"https://yenerp.com/share/upload/birthdaycakeapp/birthdaycakeimages/{new_filename}"

#                 # Check if the image URL already exists in the database
#                 existing_image = image_collection.find_one({"item_id": document["_id"], "ftp_path": file_url})
#                 if existing_image:
#                     continue  # Skip duplicate entries

#                 # Save image record in MongoDB
#                 image_record = {
#                     "item_id": document["_id"],
#                     "ftp_path": file_url
#                 }
#                 image_collection.insert_one(image_record)

#                 uploaded_images.append({
#                     "original": file,
#                     "new_filename": new_filename,
#                     "url": file_url
#                 })

#         if not uploaded_images:
#             raise HTTPException(status_code=404, detail="No new images found.")

#         return JSONResponse(content={"uploaded_images": uploaded_images})

#     finally:
#         shutil.rmtree(temp_dir, ignore_errors=True)






# import io
# import json
# import logging
# import math
# import pandas as pd
# from fastapi import APIRouter, File, HTTPException, UploadFile
# from bson import ObjectId
# from typing import List
# from .models import BirthdayCakeItem, BirthdayCakeItemPost, Variant
# from .utils import get_BirthdayCakeItem_collection, get_BirthdayCakeItem_collection, convert_to_string_or_emptys, get_BirthdayCakeItem_collection
# import os

# router = APIRouter()
# class CustomJSONEncoder(json.JSONEncoder):
#     def default(self, obj):
#         if isinstance(obj, float):
#             if math.isnan(obj) or math.isinf(obj):
#                 return 0  # Replace NaN/Infinity with 0
#         return super().default(obj)

# @router.post("/", response_model=str)
# async def create_BirthdayCakeItem(BirthdayCakeItem: BirthdayCakeItemPost):
#     new_BirthdayCakeItem = BirthdayCakeItem.dict()  # Convert Pydantic model to dictionary
#     result = get_BirthdayCakeItem_collection().insert_one(new_BirthdayCakeItem)
#     return str(result.inserted_id)
# @router.get("/")
# async def get_all_BirthdayCakeItems():
#     BirthdayCakeItems = list(get_BirthdayCakeItem_collection().find())
#     for item in BirthdayCakeItems:
#         item["_id"] = str(item["_id"])
#     return BirthdayCakeItems

# @router.get("/cakeitems", response_model=List[dict])
# async def get_all_cakeitems():
#     try:
#         cakeitems = list(get_BirthdayCakeItem_collection().find())

#         for item in cakeitems:
#             item["_id"] = str(item["_id"])  # Convert ObjectId to string

#             # ✅ Ensure "flavour" is always an array of names
#             if "flavour" in item and isinstance(item["flavour"], list):
#                 item["flavour"] = [fl["flavourName"] for fl in item["flavour"] if fl.get("enableFlavour") == "Y"]
#             else:
#                 item["flavour"] = []

#             # ✅ Fix NaN and Infinity values
#             for key, value in item.items():
#                 if isinstance(value, float):
#                     if math.isnan(value) or math.isinf(value):
#                         item[key] = 0  # Replace with zero

#         return cakeitems

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error fetching cake items: {str(e)}")


# @router.get("/{birthdayCakeId}", response_model=BirthdayCakeItem)
# async def get_BirthdayCakeItem_by_id(birthdayCakeId: str):
#     BirthdayCakeItem = get_BirthdayCakeItem_collection().find_one({"_id": ObjectId(birthdayCakeId)})
#     if BirthdayCakeItem:
#         BirthdayCakeItem["_id"] = str(BirthdayCakeItem["_id"])
#         BirthdayCakeItem["birthdayCakeId"] = BirthdayCakeItem["_id"]
#         return BirthdayCakeItem(**convert_to_string_or_emptys(BirthdayCakeItem))
#     else:
#         raise HTTPException(status_code=404, detail="BirthdayCakeItem not found")

# @router.put("/{birthdayCakeId}")
# async def update_BirthdayCakeItem(birthdayCakeId: str, BirthdayCakeItem: BirthdayCakeItemPost):
#     updated_fields = BirthdayCakeItem.dict(exclude_unset=True)
#     result = get_BirthdayCakeItem_collection().update_one(
#         {"_id": ObjectId(birthdayCakeId)},
#         {"$set": convert_to_string_or_emptys(updated_fields)}
#     )
#     if result.modified_count == 0:
#         raise HTTPException(status_code=404, detail="BirthdayCakeItem not found")
#     return {"message": "BirthdayCakeItem updated successfully"}

# @router.delete("/{birthdayCakeId}")
# async def delete_BirthdayCakeItem(birthdayCakeId: str):
#     result = get_BirthdayCakeItem_collection().delete_one({"_id": ObjectId(birthdayCakeId)})
#     if result.deleted_count == 0:
#         raise HTTPException(status_code=404, detail="BirthdayCakeItem not found")
#     return {"message": "BirthdayCakeItem deleted successfully"}

# @router.patch("/{birthdayCakeId}/deactivate")
# async def deactivate_BirthdayCakeItem(birthdayCakeId: str):
#     try:
#         obj_id = ObjectId(birthdayCakeId)
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=f"Invalid birthdayCakeId format: {birthdayCakeId}") from e
    
#     result = get_BirthdayCakeItem_collection().update_one(
#         {"_id": obj_id},
#         {"$set": {"status": "inactive"}}
#     )
    
#     if result.modified_count == 0:
#         raise HTTPException(status_code=404, detail=f"BirthdayCakeItem with ID {birthdayCakeId} not found")
#     return {"message": "BirthdayCakeItem deactivated successfully"}

# @router.patch("/{birthdayCakeId}/activate")
# async def activate_BirthdayCakeItem(birthdayCakeId: str):
#     try:
#         obj_id = ObjectId(birthdayCakeId)
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=f"Invalid birthdayCakeId format: {birthdayCakeId}") from e
    
#     result = get_BirthdayCakeItem_collection().update_one(
#         {"_id": obj_id},
#         {"$set": {"status": "active"}}
#     )
    
#     if result.modified_count == 0:
#         raise HTTPException(status_code=404, detail=f"BirthdayCakeItem with ID {birthdayCakeId} not found")
#     return {"message": "BirthdayCakeItem activated successfully"}


# @router.post("/import")
# async def import_excel(file: UploadFile):
#     try:
#         # Read the uploaded file
#         contents = await file.read()
#         filename = file.filename.lower()

#         # Detect file type
#         if filename.endswith('.csv'):
#             df = pd.read_csv(io.BytesIO(contents))
#         elif filename.endswith('.xls') or filename.endswith('.xlsx'):
#             df = pd.read_excel(io.BytesIO(contents), engine='openpyxl')
#         else:
#             raise HTTPException(status_code=400, detail="Unsupported file format. Please upload CSV or Excel file.")

#         # Column name mapping
#         column_mapping = {
#             "name": "itemName",
#             "kg": "Kg",
#             "tax": "taxPercentage",
#             "hsnCode": "hsCode",
#             "stockQuantity": "availableStock"
#         }

#         df.rename(columns=column_mapping, inplace=True)

#         # Define possible flavour columns
#         flavour_columns = [
#             "chocolate", "strawberry", "butterScotch", "mango", "freshCream",
#             "blackCurrant", "redVelvet", "blackForest", "whiteForest", "blueBerry"
#         ]

#         # Convert flavours to objects
#         def extract_flavours(row):
#             return [
#                 {"flavourName": flavour.capitalize(), "enableFlavour": "Y"}
#                 for flavour in flavour_columns if row.get(flavour, "N") == "Y"
#             ]

#         df["flavour"] = df.apply(extract_flavours, axis=1)

#         # Drop original flavour columns
#         df.drop(columns=[col for col in flavour_columns if col in df.columns], inplace=True)

#         required_columns = {
#             "category", "subCategory", "itemName", "Kg", "variant", "taxPercentage",
#             "netPrice", "finalPrice", "uom", "hsCode", "status", "type", "availableStock", "flavour"
#         }

#         if not required_columns.issubset(set(df.columns)):
#             missing_columns = required_columns - set(df.columns)
#             raise HTTPException(status_code=400, detail=f"Missing required columns: {', '.join(missing_columns)}")

#         # ✅ Replace NaN and Infinity with 0 or None
#         df = df.applymap(lambda x: 0 if isinstance(x, float) and (math.isnan(x) or math.isinf(x)) else x)

#         # Convert DataFrame to list of dictionaries
#         items = df.to_dict(orient="records")

#         # Insert data into MongoDB collection
#         collection = get_BirthdayCakeItem_collection()
#         result = collection.insert_many(items)

#         return {
#             "message": "File imported and data inserted successfully",
#             "inserted_count": len(result.inserted_ids)
#         }

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


# @router.post("/import")
# async def import_excel(file: UploadFile):
#     try:
#         # Read the uploaded file
#         contents = await file.read()
#         filename = file.filename.lower()

#         # Detect file type
#         if filename.endswith('.csv'):
#             df = pd.read_csv(io.BytesIO(contents))
#         elif filename.endswith('.xls') or filename.endswith('.xlsx'):
#             df = pd.read_excel(io.BytesIO(contents), engine='openpyxl')
#         else:
#             raise HTTPException(status_code=400, detail="Unsupported file format. Please upload CSV or Excel file.")

#         # Column name mapping (CSV to expected API fields)
#         column_mapping = {
#             "name": "itemName",
#             "kg": "Kg",
#             "tax": "taxPercentage",
#             "hsnCode": "hsCode",
#             "stockQuantity": "availableStock"
#         }

#         # Rename the columns to match required ones
#         df.rename(columns=column_mapping, inplace=True)

#         # Define possible flavour columns
#         flavour_columns = [
#             "chocolate", "strawberry", "butterScotch", "mango", "freshCream",
#             "blackCurrant", "redVelvet", "blackForest", "whiteForest", "blueBerry"
#         ]

#         # Function to extract **multiple flavours** (list)
#         def extract_flavours(row):
#             return [flavour.capitalize() for flavour in flavour_columns if row.get(flavour, "N") == "Y"]

#         # Apply function to extract flavours
#         df["flavour"] = df.apply(extract_flavours, axis=1)

#         # Drop original flavour columns
#         df.drop(columns=[col for col in flavour_columns if col in df.columns], inplace=True)

#         # Validate required columns
#         required_columns = {
#             "category", "subCategory", "itemName", "Kg", "variant", "taxPercentage",
#             "netPrice", "finalPrice", "uom", "hsCode", "status", "type", "availableStock", "flavour"
#         }

#         if not required_columns.issubset(set(df.columns)):
#             missing_columns = required_columns - set(df.columns)
#             raise HTTPException(status_code=400, detail=f"Missing required columns: {', '.join(missing_columns)}")

#         # Replace empty fields with None
#         df = df.where(pd.notnull(df), None)

#         # Convert DataFrame to list of dictionaries
#         items = df.to_dict(orient="records")

#         # Insert data into MongoDB collection
#         collection = get_BirthdayCakeItem_collection()
#         result = collection.insert_many(items)

#         # Return success message
#         return {
#             "message": "File imported and data inserted successfully",
#             "inserted_count": len(result.inserted_ids)
#         }

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

































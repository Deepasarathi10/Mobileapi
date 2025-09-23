

import csv
import io
import logging
from datetime import datetime
from typing import List
from bson import ObjectId
from fastapi import APIRouter, Body, File,  HTTPException, Response, UploadFile,  status
from fastapi.responses import StreamingResponse
import pandas as pd
from pymongo.errors import PyMongoError
from OnlinePartner.models import onlinePartners, onlinePartnersPost, dynamicDataPost, dynamicData
from OnlinePartner.utils import get_db, get_online_partners_collection, create_partner_and_collection


from fastapi import Query
from math import ceil
from typing import Any, Dict, List, Optional

router = APIRouter()

# Get all Online Partners (LIFO order)
@router.get("/", response_model=List[onlinePartners])
async def get_all_online_partners():
    try:
        partners = list(get_online_partners_collection().find().sort("createdDate", -1))
        partner_store = []
        for partner_data in partners:
            partner_data["onlinePartnersId"] = str(partner_data["_id"])
            del partner_data["_id"]
            partner_store.append(onlinePartners(**partner_data))
        return partner_store
    except Exception as e:
        logging.error(f"Error fetching all partners: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")



# Create new Online Partner and collection
@router.post("/", response_model=str, status_code=status.HTTP_201_CREATED)
async def create_online_partner(partner_data: onlinePartnersPost):
    try:
        new_partner = partner_data.dict()
        new_partner["status"] = "active"
        inserted_id = create_partner_and_collection(new_partner)
        return inserted_id
    
    except Exception as e:
        logging.error(f"Error creating partner: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")



    




# Patch (update) partner
@router.patch("/{partner_id}", response_model=onlinePartners)
async def patch_online_partner(partner_id: str, partner_patch: onlinePartnersPost):
    try:
        existing_partner = get_online_partners_collection().find_one({"_id": ObjectId(partner_id)})
        if not existing_partner:
            raise HTTPException(status_code=404, detail="Partner not found")

        updated_fields = {
            key: value for key, value in partner_patch.dict(exclude_unset=True).items()
            if value is not None
        }

        updated_fields["updatedDate"] = datetime.utcnow()

        if updated_fields:
            result = get_online_partners_collection().update_one(
                {"_id": ObjectId(partner_id)}, {"$set": updated_fields}
            )
            if result.modified_count == 0:
                logging.warning(f"No partner updated for ID {partner_id}")

        updated_partner = get_online_partners_collection().find_one({"_id": ObjectId(partner_id)})
        updated_partner["onlinePartnersId"] = str(updated_partner["_id"])
        del updated_partner["_id"]
        return onlinePartners(**updated_partner)

    except Exception as e:
        logging.error(f"Error patching partner: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")




## GET ALL DATA  WITHOUT PAGINATION

@router.get("/{partner_name}/collection-data", summary="Get all items by partner name (no pagination)", response_model=Dict[str, Any])
async def get_dynamic_collection_data(
    partner_name: str,
    search: Optional[str] = Query(None, description="Search term for itemName"),
):
    try:
        # Normalize collection name
        collection_name = partner_name.replace(" ", "_").lower()
        db = get_online_partners_collection().database
        dynamic_collection = db[collection_name]

        # Build search query if provided
        query = {}
        if search:
            normalized = "".join(search.lower().split())
            query = {
                "$expr": {
                    "$regexMatch": {
                        "input": {
                            "$replaceAll": {
                                "input": {"$toLower": "$itemName"},
                                "find": " ",
                                "replacement": ""
                            }
                        },
                        "regex": normalized
                    }
                }
            }

        cursor = dynamic_collection.find(query)

        results = []
        for item in cursor:
            if "_id" in item:
                item["dynamicDataId"] = str(item["_id"])
                del item["_id"]
            results.append(dynamicData(**item))

        return {
            "total": len(results),
            "results": results
        }

    except Exception as e:
        logging.error(f"Error fetching data from dynamic collection for partner {partner_name}: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")






# ## POST THE NEW DATA INTO THE COLLECTION BY PARTNER NAME
    
@router.post("/{partner_name}/collection-data", summary="TO POST THE ITEM IN THE PARTICULAR PARTNER NAME", response_model=dynamicDataPost, status_code=status.HTTP_201_CREATED)
async def post_dynamic_collection_data(partner_name: str, template_data: dynamicDataPost):
    try:
        collection_name = partner_name.replace(" ", "_").lower()
        db = get_online_partners_collection().database
        dynamic_collection = db[collection_name]

        insert_data = template_data.dict(exclude_unset=True)
        result = dynamic_collection.insert_one(insert_data)
        
        insert_data["dynamicDataId"] = str(result.inserted_id)
        return dynamicDataPost(**insert_data)

    except Exception as e:
        logging.error(f"Error inserting data into dynamic collection for partner {partner_name}: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")




## GET THE COLLECTION DATA BY USING THE PARTNER NAME + ID

@router.get("/{partner_name}/collection-data/{data_id}", response_model=dynamicData)
async def get_dynamic_collection_data_by_id(partner_name: str, data_id: str):
    try:
        collection_name = partner_name.replace(" ", "_").lower()
        db = get_online_partners_collection().database
        dynamic_collection = db[collection_name]

        item = dynamic_collection.find_one({"_id": ObjectId(data_id)})

        if not item:
            raise HTTPException(status_code=404, detail="Data not found")

        item["dynamicDataId"] = str(item["_id"])
        del item["_id"]

        return dynamicData(**item)

    except Exception as e:
        logging.error(f"Error fetching data by ID from collection for partner {partner_name}: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

 
    

## UPDATE THE DATA IN THE COLLECTION BY USING PARTNER NAME + ID

@router.patch("/{partner_name}/collection-data/{data_id}", response_model=dynamicDataPost)
async def patch_dynamic_collection_data(
    partner_name: str,
    data_id: str,
    updated_data: dynamicDataPost
):
    try:
        collection_name = partner_name.replace(" ", "_").lower()
        db = get_online_partners_collection().database
        dynamic_collection = db[collection_name]

        update_fields = updated_data.dict(exclude_unset=True)

        result = dynamic_collection.update_one(
            {"_id": ObjectId(data_id)},
            {"$set": update_fields}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Data not found")

        # Fetch and return the updated document
        updated_doc = dynamic_collection.find_one({"_id": ObjectId(data_id)})

        if not updated_doc:
            raise HTTPException(status_code=404, detail="Updated data not found")

      #  updated_doc["dynamicDataId"] = str(updated_doc.pop("_id"))
        return dynamicData(**updated_doc)

    except Exception as e:
        logging.error(f"Error updating data in collection for partner {partner_name}: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    


   ###  DELETE THE DATA BY ID

@router.delete("/{partner_name}/collection-data/{data_id}", summary="Delete dynamic data by ID")
async def delete_dynamic_collection_data(
    partner_name: str,
    data_id: str,
):
    try:
        collection_name = partner_name.replace(" ", "_").lower()
        db = get_online_partners_collection().database
        dynamic_collection = db[collection_name]

        result = dynamic_collection.delete_one({"_id": ObjectId(data_id)})

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Data not found")

        return {"success": True, "message": f"Data with ID {data_id} deleted successfully."}

    except Exception as e:
        logging.error(f"Error deleting data in collection for partner {partner_name}: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")




  ### DELETE THE MULTIPLE DATA AT A TIME


@router.delete("/{partner_name}/{dynamicDataId}/bulk-delete", summary="Bulk delete dynamic data by IDs")
async def bulk_delete_dynamic_collection_data(
    partner_name: str,
    
template_ids: List[str] = Body(..., embed=True, description="List of data IDs to delete")
):
    try:
        collection_name = partner_name.replace(" ", "_").lower()
        db = get_online_partners_collection().database
        dynamic_collection = db[collection_name]

        # Convert string IDs to ObjectId
        object_ids = []
        for id in template_ids:
            try:
                object_ids.append(ObjectId(id))
            except Exception:
                raise HTTPException(status_code=400, detail=f"Invalid ObjectId: {id}")

        result = dynamic_collection.delete_many({"_id": {"$in": object_ids}})

        return {
            "success": True,
            "deleted_count": result.deleted_count,
            "deleted_ids": [str(oid) for oid in object_ids]
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        logging.error(f"Error bulk deleting data for partner {partner_name}: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")



# Function to delete a partner and its associated dynamic collection


@router.delete("/partners/{partner_id}")
async def delete_partner(partner_id: str):
    return delete_partner_and_collection(partner_id)
def delete_partner_and_collection(partner_id: str):
    db = get_db()
    collection = db['onlinePartnerMaster']

    try:
        # Retrieve partner by ID
        partner = collection.find_one({"_id": ObjectId(partner_id)})
        if not partner:
            raise HTTPException(status_code=404, detail="Partner not found")

        # Extract and sanitize collection name
        partner_name = partner.get("partnerName")
        if not partner_name:
            raise HTTPException(status_code=400, detail="partnerName is missing in the document")

        collection_name = partner_name.replace(" ", "_").lower()

        # Delete the partner document
        collection.delete_one({"_id": ObjectId(partner_id)})

        # Drop the associated collection if it exists
        if collection_name in db.list_collection_names():
            db.drop_collection(collection_name)
            logging.info(f"Dropped collection: {collection_name}")

        return {"detail": f"Partner '{partner_name}' and collection '{collection_name}' deleted."}

    except Exception as e:
        logging.error(f"Failed to delete partner or collection: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")



## IMPORT DATA
@router.post("/import")
async def import_partner_collection(partnerName: str, file: UploadFile = File(...)):
    try:
        # Normalize collection name
        collection_name = partnerName.replace(" ", "_").lower()
        db = get_db()
        collection = db[collection_name]

        # Read uploaded file
        content = await file.read()
        filename = file.filename

        # Parse into DataFrame
        if filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content))
        elif filename.endswith(".json"):
            df = pd.read_json(io.BytesIO(content))
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type. Upload CSV or JSON.")

        imported_ids = []
        duplicates = []

        for row in df.to_dict(orient="records"):
            row.pop("dynamicDataId", None)  # Remove any client-side ID

            item_name = row.get("itemName")
            if not item_name:
                continue  # Skip rows with no itemName

            normalized_name = item_name.strip().lower()

            # Check if a duplicate exists (case-insensitive)
            if collection.find_one({"itemName": {"$regex": f"^{normalized_name}$", "$options": "i"}}):
                duplicates.append(item_name)
            else:
                # Save itemName in uppercase
                row["itemName"] = item_name.strip().upper()
                result = collection.insert_one(row)
                imported_ids.append(str(result.inserted_id))

        return {
            "message": f"Import completed: {len(imported_ids)} new, {len(duplicates)} duplicates skipped.",
            "imported_ids": imported_ids,
            "duplicates": duplicates
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")




@router.get("/export", response_class=StreamingResponse)
async def export_partner_collection(partnerName: str):
    try:
        # Normalize collection name
        collection_name = partnerName.replace(" ", "_").lower()
        db = get_db()
        collection = db[collection_name]

        # Fetch only active templates with specific fields
        templates = list(collection.find(
            {"status": "active"},
            {
                "_id": 0,
                "itemName": 1,
                # "assignedPartners": 1,
                "Defaultprice": 1,
                "percentage": 1,
                "partnerPrice": 1
            }
        ))

        if not templates:
            raise HTTPException(status_code=404, detail=f"No active templates found for partner '{partnerName}'")

        # Create CSV
        csv_stream = io.StringIO()
        fieldnames = ["S.No", "Item Name", "Current Price", "Percentage", "Partner Price"]
        writer = csv.DictWriter(csv_stream, fieldnames=fieldnames)
        writer.writeheader()

        for index, template in enumerate(templates, 1):
            writer.writerow({
                "S.No": index,
                "Item Name": template.get("itemName", ""),
                "Current Price": template.get("Defaultprice", 0.0),
                "Percentage": template.get("percentage", 0),
                "Partner Price": template.get("partnerPrice", 0.0),
            })

        csv_stream.seek(0)
        return StreamingResponse(
            csv_stream,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={collection_name}_templates.csv"}
        )

    except Exception as e:
        logging.error(f"Error exporting templates: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error exporting templates: {str(e)}")












# Get partner by ID
@router.get("/{partner_id}", response_model=onlinePartners)
async def get_online_partner_by_id(partner_id: str):
    try:
        partner = get_online_partners_collection().find_one({"_id": ObjectId(partner_id)})
        if partner:
            partner["onlinePartnersId"] = str(partner["_id"])
            del partner["_id"]
            return onlinePartners(**partner)
        else:
            raise HTTPException(status_code=404, detail="Partner not found")
    except Exception as e:
        logging.error(f"Error fetching partner by ID: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")    





















































    








































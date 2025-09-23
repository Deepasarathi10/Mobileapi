

# import json
# import logging
# import re
# import string
# import uuid
# from fastapi import APIRouter, Body, HTTPException, Response, UploadFile, File, Query
# from typing import List, Optional, Dict, Any
# from bson import ObjectId
# from math import ceil
# import pandas as pd
# import io
# from pymongo import DESCENDING  # Useful for fetch APIs

# from OnlinePartner.utils import get_online_partners_collection
# from .models import onlinePartnerTemplate, onlinePartnerTemplatePost, PartnerPostPayload
# from .utils import get_onlinePartnerTemplate_collection

# router = APIRouter()
# collection = get_onlinePartnerTemplate_collection()

# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
# )

# def convert_to_string_or_none(value):
#     if isinstance(value, ObjectId):
#         return str(value)
#     elif value is None:
#         return None
#     elif isinstance(value, dict):
#         return {k: convert_to_string_or_none(v) for k, v in value.items()}
#     elif isinstance(value, list):
#         return [convert_to_string_or_none(v) for v in value]
#     return value

# def get_next_counter_value():
#     counter_collection = get_onlinePartnerTemplate_collection().database["counters"]
#     counter = counter_collection.find_one_and_update(
#         {"_id": "onlinePartnerTemplateId"},
#         {"$inc": {"sequence_value": 1}},
#         upsert=True,
#         return_document=True
#     )
#     return counter["sequence_value"]

# def reset_counter():
#     counter_collection = get_onlinePartnerTemplate_collection().database["counters"]
#     counter_collection.update_one(
#         {"_id": "onlinePartnerTemplateId"},
#         {"$set": {"sequence_value": 0}},
#         upsert=True
#     )

# def generate_random_id():
#     counter_value = get_next_counter_value()
#     return f"It{counter_value:03d}"






# async def sync_assigned_partners(db, item_name: str, template_collection, partner_name: str = None, status: str = None):
#     try:
#         # Find the template item
#         template_item = template_collection.find_one({"itemName": item_name})
#         if not template_item:
#             logging.info(f"No template item found for {item_name}, skipping sync")
#             return

#         assigned_partners = template_item.get("assignedPartners", []) or []
#         deactivate_assigned_partners = template_item.get("deactivateAssignedPartners", []) or []

#         if partner_name and status:
#             normalized_partner_name = partner_name.lower().replace(" ", "_")
#             # Update partner status
#             if status == "deactivated":
#                 if normalized_partner_name in assigned_partners:
#                     assigned_partners.remove(normalized_partner_name)
#                 if normalized_partner_name not in deactivate_assigned_partners:
#                     deactivate_assigned_partners.append(normalized_partner_name)
#             elif status == "active":
#                 if normalized_partner_name in deactivate_assigned_partners:
#                     deactivate_assigned_partners.remove(normalized_partner_name)
#                 if normalized_partner_name not in assigned_partners:
#                     assigned_partners.append(normalized_partner_name)
#         else:
#             # General sync for all partners
#             partner_collection = get_online_partners_collection()
#             partners = partner_collection.find({}, {"partnerName": 1})
#             for partner in partners:
#                 partner_name = partner["partnerName"].lower()
#                 normalized_partner_name = partner_name.replace(" ", "_")
#                 dynamic_collection = db[normalized_partner_name]
#                 item = dynamic_collection.find_one({
#                     "itemName": item_name,
#                     "status": "active"
#                 })
#                 if item:
#                     if normalized_partner_name not in assigned_partners:
#                         assigned_partners.append(normalized_partner_name)
#                     if normalized_partner_name in deactivate_assigned_partners:
#                         deactivate_assigned_partners.remove(normalized_partner_name)
#                 else:
#                     if normalized_partner_name in assigned_partners:
#                         assigned_partners.remove(normalized_partner_name)
#                     dynamic_item = dynamic_collection.find_one({"itemName": item_name, "status": "deactivated"})
#                     if dynamic_item and normalized_partner_name not in deactivate_assigned_partners:
#                         deactivate_assigned_partners.append(normalized_partner_name)

#         # Remove duplicates and update the template
#         assigned_partners = list(set(assigned_partners))
#         deactivate_assigned_partners = list(set(deactivate_assigned_partners))

#         # Update the template item
#         template_collection.update_one(
#             {"itemName": item_name},
#             {
#                 "$set": {
#                     "assignedPartners": assigned_partners,
#                     "deactivateAssignedPartners": deactivate_assigned_partners
#                 }
#             }
#         )
#         logging.info(f"Synced assigned partners for item {item_name}: {assigned_partners}, deactivated: {deactivate_assigned_partners}")
#     except Exception as e:
#         logging.error(f"Error syncing assigned partners for {item_name}: {str(e)}")
#         raise HTTPException(status_code=500, detail=f"Failed to sync assigned partners: {str(e)}")







    

# @router.post("/", response_model=str)
# async def create_onlinePartnerTemplate(onlinePartnerTemplate: onlinePartnerTemplatePost):
#     try:
#         # Reset counter if first document
#         if collection.count_documents({}) == 0:
#             reset_counter()

#         onlinePartnerTemplate_dict = onlinePartnerTemplate.dict()
#         item_name = onlinePartnerTemplate_dict.get("itemName")

#         if not item_name:
#             raise HTTPException(status_code=400, detail="Item name is required")

#         # Check for existing template
#         existing_template = collection.find_one({"itemName": item_name})
#         if existing_template:
#             raise HTTPException(
#                 status_code=400,
#                 detail=f"Item '{item_name}' already exists in the template collection"
#             )

#         # Set defaults
#         onlinePartnerTemplate_dict['status'] = "active"
#         onlinePartnerTemplate_dict['assignedPartners'] = onlinePartnerTemplate_dict.get('assignedPartners', [])
#         onlinePartnerTemplate_dict['deactivateAssignedPartners'] = onlinePartnerTemplate_dict.get('deactivateAssignedPartners', [])

#         # Check partner collections for assigned items
#         partner_collection = get_online_partners_collection()
#         partners = partner_collection.find({}, {"partnerName": 1})
#         db = collection.database
#         assigned_partners = []

#         for partner in partners:
#             partner_name = partner["partnerName"].lower()
#             normalized_partner_name = partner_name.replace(" ", "_")
#             dynamic_collection = db[normalized_partner_name]
#             item = dynamic_collection.find_one({"itemName": item_name})
#             if item:
#                 assigned_partners.append(normalized_partner_name)

#         onlinePartnerTemplate_dict['assignedPartners'] = list(set(assigned_partners))  # De-duplication

#         # Insert into template collection
#         result = collection.insert_one(onlinePartnerTemplate_dict)

#         # Sync for consistency
#         await sync_assigned_partners(db, item_name, collection)

#         logging.info(f"Created template for item '{item_name}' with assigned partners: {assigned_partners}")
#         return str(result.inserted_id)

#     except HTTPException as he:
#         raise he
#     except Exception as e:
#         logging.error(f"Error creating onlinePartnerTemplate for item '{item_name}': {str(e)}")
#         raise HTTPException(status_code=500, detail=f"Failed to create template: {str(e)}")








# @router.get("/", summary="Fetch All Online Partner Templates with Search (LIFO Order)")
# def get_all_onlinePartnerTemplates(
#     search: Optional[str] = Query(None, description="Search term for itemName"),
# ) -> Dict[str, Any]:
#     try:
#         query = {}
#         if search:
#             normalized = "".join(search.lower().split())
#             query = {
#                 "$expr": {
#                     "$regexMatch": {
#                         "input": {
#                             "$replaceAll": {
#                                 "input": {"$toLower": "$itemName"},
#                                 "find": " ",
#                                 "replacement": ""
#                             }
#                         },
#                         "regex": normalized
#                     }
#                 }
#             }

#         # Sort by _id in descending order (newest first = LIFO)
#         cursor = collection.find(query).sort("_id", -1)

#         templates = []
#         for partner in cursor:
#             for key, value in partner.items():
#                 partner[key] = convert_to_string_or_none(value)
#             partner["onlinePartnerTemplateId"] = str(partner.get("_id"))
#             templates.append(onlinePartnerTemplate(**partner))

#         return {
#             "total": len(templates),
#             "results": templates
#         }

#     except Exception as e:
#         print(f"Error fetching onlinePartnerTemplates: {e}")
#         raise HTTPException(status_code=500, detail="Internal Server Error")


# @router.get("/item-names", summary="Get all item names for autocomplete")
# def get_item_names(
#     search: Optional[str] = Query(None, description="Search term for itemName"),
#     limit: int = Query(10000000, ge=1, le=10000000)
# ) -> List[str]:
#     try:
#         query = {}
#         if search:
#             normalized = "".join(search.lower().split())
#             query = {
#                 "$expr": {
#                     "$regexMatch": {
#                         "input": {
#                             "$replaceAll": {
#                                 "input": { "$toLower": "$itemName" },
#                                 "find": " ",
#                                 "replacement": ""
#                             }
#                         },
#                         "regex": normalized
#                     }
#                 }
#             }
#         cursor = collection.find(query, {"itemName": 1, "_id": 0}).limit(limit)
#         item_names = [doc["itemName"] for doc in cursor if "itemName" in doc]
#         return item_names
#     except Exception as e:
#         print(f"Error fetching item names: {e}")
#         raise HTTPException(status_code=500, detail="Internal Server Error")

# @router.patch("/{onlinePartnerTemplateId}", response_model=onlinePartnerTemplate)
# async def partial_update_onlinePartnerTemplate(onlinePartnerTemplateId: str, onlinePartnerTemplate: onlinePartnerTemplatePost):
#     updated_onlinePartnerTemplate = {k: v for k, v in onlinePartnerTemplate.dict(exclude_unset=True).items() if v is not None}
#     result = collection.update_one({"_id": ObjectId(onlinePartnerTemplateId)}, {"$set": updated_onlinePartnerTemplate})
#     template_item = collection.find_one({"_id": ObjectId(onlinePartnerTemplateId)})
#     if result.matched_count == 0:
#         raise HTTPException(status_code=404, detail="onlinePartnerTemplate not found")
#     if template_item:
#         await sync_assigned_partners(collection.database, template_item.get("itemName"), collection)
#     return await get_onlinePartnerTemplate(onlinePartnerTemplateId)







# @router.delete("/{onlinePartnerTemplateId}", summary="Delete an online partner template")
# async def delete_onlinePartnerTemplate(onlinePartnerTemplateId: str):
#     try:
#         # Validate the ObjectId
#         if not ObjectId.is_valid(onlinePartnerTemplateId):
#             raise HTTPException(status_code=400, detail="Invalid ObjectId format")
        
#         # Find the template to get the item name for sync
#         template = collection.find_one({"_id": ObjectId(onlinePartnerTemplateId)})
#         if not template:
#             raise HTTPException(status_code=404, detail="Online partner template not found")
        
#         item_name = template.get("itemName")
        
#         # Delete the template
#         result = collection.delete_one({"_id": ObjectId(onlinePartnerTemplateId)})
        
#         if result.deleted_count == 0:
#             raise HTTPException(status_code=404, detail="Online partner template not found")
        
#         # Sync with all partner collections to move items to deactivated status
#         if item_name:
#             try:
            
                
              
                
#                 logging.info(f"Successfully deleted template {onlinePartnerTemplateId} and updated partner collections")
#             except Exception as sync_error:
#                 logging.error(f"Error during partner reference cleanup: {str(sync_error)}")
#                 # Continue with deletion even if cleanup fails, but log the error
        
#         return {"message": "Online partner template deleted successfully"}
    
#     except HTTPException as he:
#         raise he
#     except Exception as e:
#         logging.error(f"Error deleting online partner template {onlinePartnerTemplateId}: {str(e)}")
#         raise HTTPException(status_code=500, detail=f"Failed to delete template: {str(e)}")


    
    


#    ## DETETE THE BULK DATA ON THE TEMPLATE

# @router.delete("/{onlinePartnerTemplateId}/bulk-delete", summary="Bulk delete online partner templates by IDs")
# async def bulk_delete_online_partner_templates(
#     template_ids: List[str] = Body(..., embed=True, description="List of template IDs to delete")
# ):
#     try:
#         # Validate and convert all IDs to ObjectId
#         object_ids = []
#         invalid_ids = []
        
#         for template_id in template_ids:
#             if ObjectId.is_valid(template_id):
#                 object_ids.append(ObjectId(template_id))
#             else:
#                 invalid_ids.append(template_id)
        
#         if invalid_ids:
#             raise HTTPException(
#                 status_code=400,
#                 detail=f"Invalid ObjectId format for IDs: {', '.join(invalid_ids)}"
#             )

#         # Get all templates before deletion for sync purposes
#         templates = list(collection.find({"_id": {"$in": object_ids}}))
#         item_names = list({t.get("itemName") for t in templates if t.get("itemName")})

#         # Perform bulk deletion
#         result = collection.delete_many({"_id": {"$in": object_ids}})

#         if result.deleted_count == 0:
#             raise HTTPException(
#                 status_code=404,
#                 detail="No templates were found with the provided IDs"
#             )

#         # Sync with partner collections if needed
#         if item_names:
#             try:
#                 # Your existing sync logic here
#                 # Example: Update partner collections to deactivate these items
#                 logging.info(f"Syncing deletion with partner collections for items: {item_names}")
#             except Exception as sync_error:
#                 logging.error(f"Sync error during bulk delete: {str(sync_error)}")

#         return {
#             "success": True,
#             "message": f"Successfully deleted {result.deleted_count} templates",
#             "deleted_count": result.deleted_count,
#             "deleted_ids": [str(oid) for oid in object_ids],
#             "affected_items": item_names
#         }

#     except HTTPException as he:
#         raise he
#     except Exception as e:
#         logging.error(f"Error in bulk deleting online partner templates: {str(e)}")
#         raise HTTPException(
#             status_code=500,
#             detail=f"Failed to delete templates: {str(e)}"
#         )





# #### ASSIGN ITEM TO THE PARTNER 


# @router.post(
#     "/{partner_name}/collection-data",
#     summary="Assign data from template to dynamic collection",
#     response_model=Dict[str, List[str]]
# )
# async def post_template_to_dynamic_collection(
#     partner_name: str,
#     payload: PartnerPostPayload = Body(...)
# ):
#     try:
#         template_data = payload.template_data
#         logging.info(f"Received data for partner {partner_name}")
#         logging.info(f"Received payload: {[item.dict() for item in template_data]}")

#         partner_collection = get_online_partners_collection()
#         partner = partner_collection.find_one({
#             "partnerName": {"$regex": f"^{partner_name}$", "$options": "i"}
#         })
#         if not partner:
#             raise HTTPException(status_code=404, detail="Partner not found")

#         normalized_partner_name = partner_name.lower().replace(" ", "_")
#         if not normalized_partner_name:
#             raise HTTPException(status_code=400, detail="Invalid partner name")

#         db = get_onlinePartnerTemplate_collection().database
#         template_collection = get_onlinePartnerTemplate_collection()
#         dynamic_collection = db[normalized_partner_name]

#         inserted_ids = []
#         skipped_items = []

#         for item in template_data:
#             template_dict = item.dict(exclude_unset=False)
#             template_dict.pop('assignedPartners', None)
#             template_dict.pop('deactivateAssignedPartners', None)
#             template_dict['status'] = template_dict.get('status', 'active')

#             if not template_dict['itemName']:
#                 raise HTTPException(status_code=400, detail=f"Item name is required for item: {template_dict}")

#             item_name = template_dict['itemName']

#             existing_dynamic_item = dynamic_collection.find_one({
#                 "itemName": item_name
#             })
#             if existing_dynamic_item:
#                 logging.info(f"Item '{item_name}' already exists for partner '{partner_name}', skipping.")
#                 skipped_items.append(item_name)
#                 continue

#             dynamic_dict = template_dict.copy()
#             logging.info(f"Inserting into dynamic collection {normalized_partner_name}: {dynamic_dict}")
#             dynamic_result = dynamic_collection.insert_one(dynamic_dict)
#             inserted_ids.append(str(dynamic_result.inserted_id))

#             existing_template_item = template_collection.find_one({
#                 "itemName": item_name,
#                 "status": "active"
#             })

#             if existing_template_item:
#                 result = template_collection.update_one(
#                     {"_id": existing_template_item["_id"]},
#                     {
#                         "$set": {
#                             "Defaultprice": template_dict.get('Defaultprice'),
#                             "percentage": template_dict.get('percentage'),
#                             "partnerPrice": template_dict.get('partnerPrice'),
#                             "status": template_dict['status']
#                         }
#                     }
#                 )
#                 if result.modified_count > 0:
#                     logging.info(f"Updated item {item_name} in onlinePartnerTemplate")
#             else:
#                 template_dict['onlinePartnerTemplateId'] = template_dict.get('onlinePartnerTemplateId', None) or generate_random_id()
#                 template_dict['assignedPartners'] = [normalized_partner_name]
#                 template_dict['deactivateAssignedPartners'] = []
#                 logging.info(f"Inserting into onlinePartnerTemplate: {template_dict}")
#                 template_collection.insert_one(template_dict)

#             await sync_assigned_partners(db, item_name, template_collection, normalized_partner_name, template_dict['status'])

#         logging.info(f"Processed {len(inserted_ids)} items for {partner_name}. Skipped {len(skipped_items)} items: {skipped_items}")
#         return {
#             "inserted": inserted_ids,
#             "duplicates": skipped_items
#         }

#     except HTTPException as he:
#         raise he
#     except Exception as e:
#         logging.error(f"Error processing items for {partner_name}: {str(e)}")
#         raise HTTPException(status_code=500, detail=f"Failed to process items: {str(e)}")








# @router.delete("/{partner_name}/item/{item_name}", summary="Delete item from dynamic collection", response_model=str)
# async def delete_dynamic_item(
#     partner_name: str,
#     item_name: str
# ):
#     try:
#         # Get partner info
#         partner_collection = get_online_partners_collection()
#         partner = partner_collection.find_one({
#             "partnerName": {"$regex": f"^{partner_name}$", "$options": "i"}
#         })
#         if not partner:
#             raise HTTPException(status_code=404, detail="Partner not found")
        
#         # Normalize partner name
#         normalized_partner_name = partner_name.lower().replace(" ", "_")
#         if not normalized_partner_name:
#             raise HTTPException(status_code=400, detail="Invalid partner name")
        
#         # Get collections
#         db = get_onlinePartnerTemplate_collection().database
#         dynamic_collection = db[normalized_partner_name]
#         template_collection = get_onlinePartnerTemplate_collection()
        
#         # Check if item exists in partner's collection
#         existing_item = dynamic_collection.find_one({"itemName": item_name})
#         if not existing_item:
#             raise HTTPException(status_code=404, detail=f"Item '{item_name}' not found in {partner_name}'s collection")
        
#         # Delete the item from partner's collection
#         delete_result = dynamic_collection.delete_one({"itemName": item_name})
#         if delete_result.deleted_count == 0:
#             raise HTTPException(status_code=404, detail=f"Failed to delete item '{item_name}'")
        
#         # Remove partner from assignedPartners in template collection
#         template_collection.update_one(
#             {"itemName": item_name},
#             {"$pull": {"assignedPartners": normalized_partner_name}}
#         )
        
#         logging.info(f"Deleted item {item_name} from {normalized_partner_name}'s collection")
#         return "Item deleted successfully"
#     except HTTPException as he:
#         raise he
#     except Exception as e:
#         logging.error(f"Error deleting item {item_name} from {partner_name}: {str(e)}")
#         raise HTTPException(status_code=500, detail=f"Failed to delete item: {str(e)}")
    




# @router.post("/import")
# async def import_templates(file: UploadFile = File(...)):
#     content = await file.read()
#     filename = file.filename
#     try:
#         # Read file based on extension
#         if filename.endswith(".csv"):
#             df = pd.read_csv(io.BytesIO(content))
#         elif filename.endswith(".json"):
#             df = pd.read_json(io.BytesIO(content))
#         else:
#             raise HTTPException(status_code=400, detail="Unsupported file type. Please upload CSV or JSON.")
        
#         imported = []
#         duplicates = []
#         partner_updates = []
#         db = collection.database

#         for row in df.to_dict(orient="records"):
#             # Clean up data
#             row.pop("onlinePartnerTemplateId", None)
#             item_name = str(row.get("itemName", "")).strip().upper()
#             if not item_name:
#                 continue

#             # Check for existing template (case-insensitive)
#             if collection.find_one({"itemName": {"$regex": f"^{re.escape(item_name)}$", "$options": "i"}}):
#                 duplicates.append(item_name)
#                 continue

#             # Process assigned partners - handle various input formats
#             assigned_partners = []
#             partners_input = row.get("assignedPartners", [])
            
#             if isinstance(partners_input, str):
#                 # Handle string format like "[ SWIGGY, BUTTERPLAY ]"
#                 partners_input = partners_input.strip("[]").strip()
#                 if partners_input:
#                     assigned_partners = [p.strip().upper() for p in partners_input.split(",") if p.strip()]
#             elif isinstance(partners_input, list):
#                 assigned_partners = [str(p).strip().upper() for p in partners_input if p and str(p).strip()]
#             elif pd.notna(partners_input):  # Handle pandas NA/float values
#                 assigned_partners = [str(partners_input).strip().upper()]

#             # Convert other fields to proper types
#             default_price = float(row.get("Defaultprice", 0)) if pd.notna(row.get("Defaultprice")) else 0
#             percentage = float(row.get("percentage", 0)) if pd.notna(row.get("percentage")) else 0
#             partner_price = float(row.get("partnerPrice", 0)) if pd.notna(row.get("partnerPrice")) else 0

#             # Create the template document
#             template_data = {
#                 "itemName": item_name,
#                 "Defaultprice": default_price,
#                 "percentage": percentage,
#                 "partnerPrice": partner_price,
#                 "status": str(row.get("status", "active")).lower(),
#                 "assignedPartners": assigned_partners,
#                 "deactivateAssignedPartners": [],
#             }

#             # Insert template into templates collection
#             result = collection.insert_one(template_data)
#             template_id = str(result.inserted_id)
#             imported.append(template_id)

#             # Add this template to each assigned partner's dynamic collection
#             for partner_name in assigned_partners:
#                 try:
#                     # Normalize partner name for collection name
#                     normalized_partner_name = partner_name.lower().replace(" ", "_")
                    
#                     # Check if partner exists in partners collection (exact match)
#                     partner = get_online_partners_collection().find_one({
#                         "partnerName": {"$regex": f"^{re.escape(partner_name)}$", "$options": "i"}
#                     })
                    
#                     if not partner:
#                         logging.warning(f"Partner {partner_name} not found in partners collection")
#                         continue

#                     # Get or create dynamic collection
#                     dynamic_collection = db[normalized_partner_name]
                    
#                     # Prepare document for partner collection
#                     partner_doc = {
#                         "itemName": item_name,
#                         "Defaultprice": default_price,
#                         "percentage": percentage,
#                         "partnerPrice": partner_price,
#                         "status": "active",
#                     }

#                     # Insert or update in partner's dynamic collection
#                     dynamic_result = dynamic_collection.update_one(
#                         {"itemName": item_name},
#                         {"$set": partner_doc},
#                         upsert=True
#                     )

#                     # Update the partner's templates list
#                     partner_update_result = get_online_partners_collection().update_one(
#                         {"_id": partner["_id"]},
#                         {"$addToSet": {"templates": template_id}}
#                     )

#                     partner_updates.append({
#                         "partner": partner_name,
#                         "action": "created" if dynamic_result.upserted_id else "updated",
#                         "item": item_name
#                     })
                    
#                 except Exception as e:
#                     logging.error(f"Error updating partner {partner_name}: {str(e)}")
#                     continue

#         return {
#             "message": f"Import completed: {len(imported)} new templates, {len(duplicates)} duplicates skipped.",
#             "imported_ids": imported,
#             "duplicates": duplicates,
#             "partner_updates": partner_updates
#         }
        
#     except Exception as e:
#         logging.error(f"Import failed: {str(e)}", exc_info=True)
#         raise HTTPException(
#             status_code=500,
#             detail=f"Import failed: {str(e)}"
#         )



# @router.get("/export", response_class=Response)
# async def export_templates(format: str = "csv"):
#     try:
#         templates = list(collection.find({}, {"_id": 0}))
#         if not templates:
#             raise HTTPException(status_code=404, detail="No templates found")
#         df = pd.DataFrame(templates)
#         format = format.lower()
#         if format == "csv":
#             output = io.StringIO()
#             df.to_csv(output, index=False)
#             return Response(content=output.getvalue(), media_type="text/csv", headers={
#                 "Content-Disposition": "attachment; filename=online_partner_templates.csv"
#             })
#         elif format == "json":
#             return Response(content=df.to_json(orient="records"), media_type="application/json")
#         else:
#             raise HTTPException(status_code=400, detail="Unsupported format. Use 'csv' or 'json'.")
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


        

# @router.get("/{onlinePartnerTemplateId}", response_model=onlinePartnerTemplate)
# async def get_onlinePartnerTemplate(onlinePartnerTemplateId: str):
#     try:
#         if not ObjectId.is_valid(onlinePartnerTemplateId):
#             raise HTTPException(status_code=400, detail="Invalid ObjectId")
#         partner = collection.find_one({"_id": ObjectId(onlinePartnerTemplateId)})
#         if not partner:
#             raise HTTPException(status_code=404, detail="onlinePartnerTemplate not found")
#         for key, value in partner.items():
#             partner[key] = convert_to_string_or_none(value)
#         partner["onlinePartnerTemplateId"] = str(partner["_id"])
#         return onlinePartnerTemplate(**partner)
#     except Exception as e:
#         print(f"Error fetching onlinePartnerTemplate by ID: {e}")
#         raise HTTPException(status_code=500, detail="Internal Server Error")

































import csv
import json
import logging
import re
import string
import uuid
from fastapi import APIRouter, Body, HTTPException, Response, UploadFile, File, Query
from typing import List, Optional, Dict, Any
from bson import ObjectId
from math import ceil
from fastapi.responses import StreamingResponse
import pandas as pd
import io
from pymongo import DESCENDING

from OnlinePartner.utils import get_online_partners_collection
from .models import onlinePartnerTemplate, onlinePartnerTemplatePost, PartnerPostPayload, BulkDeleteRequest
from .utils import get_onlinePartnerTemplate_collection

router = APIRouter()
collection = get_onlinePartnerTemplate_collection()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)

def convert_to_string_or_none(value):
    if isinstance(value, ObjectId):
        return str(value)
    elif value is None:
        return None
    elif isinstance(value, dict):
        return {k: convert_to_string_or_none(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [convert_to_string_or_none(v) for v in value]
    return value

def get_next_counter_value():
    counter_collection = get_onlinePartnerTemplate_collection().database["counters"]
    counter = counter_collection.find_one_and_update(
        {"_id": "onlinePartnerTemplateId"},
        {"$inc": {"sequence_value": 1}},
        upsert=True,
        return_document=True
    )
    return counter["sequence_value"]

def reset_counter():
    counter_collection = get_onlinePartnerTemplate_collection().database["counters"]
    counter_collection.update_one(
        {"_id": "onlinePartnerTemplateId"},
        {"$set": {"sequence_value": 0}},
        upsert=True
    )

def generate_random_id():
    counter_value = get_next_counter_value()
    return f"It{counter_value:03d}"

async def sync_assigned_partners(db, item_name: str, template_collection, partner_name: str = None, status: str = None):
    try:
        template_item = template_collection.find_one({"itemName": item_name})
        if not template_item:
            logging.info(f"No template item found for {item_name}, skipping sync")
            return

        assigned_partners = template_item.get("assignedPartners", []) or []

        if partner_name and status:
            normalized_partner_name = partner_name.lower().replace(" ", "_")
            if status == "active":
                if normalized_partner_name not in assigned_partners:
                    assigned_partners.append(normalized_partner_name)
            elif status == "deactivated":
                if normalized_partner_name in assigned_partners:
                    assigned_partners.remove(normalized_partner_name)
        else:
            partner_collection = get_online_partners_collection()
            partners = partner_collection.find({}, {"partnerName": 1})
            for partner in partners:
                partner_name = partner["partnerName"].lower()
                normalized_partner_name = partner_name.replace(" ", "_")
                dynamic_collection = db[normalized_partner_name]
                item = dynamic_collection.find_one({"itemName": item_name, "status": "active"})
                if item:
                    if normalized_partner_name not in assigned_partners:
                        assigned_partners.append(normalized_partner_name)
                else:
                    if normalized_partner_name in assigned_partners:
                        assigned_partners.remove(normalized_partner_name)

        assigned_partners = list(set(assigned_partners))

        template_collection.update_one(
            {"itemName": item_name},
            {"$set": {"assignedPartners": assigned_partners}}
        )
        logging.info(f"Synced assigned partners for item {item_name}: {assigned_partners}")
    except Exception as e:
        logging.error(f"Error syncing assigned partners for {item_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to sync assigned partners: {str(e)}")

@router.post("/", response_model=str)
async def create_onlinePartnerTemplate(onlinePartnerTemplate: onlinePartnerTemplatePost):
    try:
        if collection.count_documents({}) == 0:
            reset_counter()

        onlinePartnerTemplate_dict = onlinePartnerTemplate.dict()
        item_name = onlinePartnerTemplate_dict.get("itemName")

        if not item_name:
            raise HTTPException(status_code=400, detail="Item name is required")

        existing_template = collection.find_one({"itemName": item_name})
        if existing_template:
            raise HTTPException(
                status_code=400,
                detail=f"Item '{item_name}' already exists in the template collection"
            )

        onlinePartnerTemplate_dict['status'] = "active"
        onlinePartnerTemplate_dict['assignedPartners'] = onlinePartnerTemplate_dict.get('assignedPartners', [])

        partner_collection = get_online_partners_collection()
        partners = partner_collection.find({}, {"partnerName": 1})
        db = collection.database
        assigned_partners = []

        for partner in partners:
            partner_name = partner["partnerName"].lower()
            normalized_partner_name = partner_name.replace(" ", "_")
            dynamic_collection = db[normalized_partner_name]
            item = dynamic_collection.find_one({"itemName": item_name})
            if item:
                assigned_partners.append(normalized_partner_name)

        onlinePartnerTemplate_dict['assignedPartners'] = list(set(assigned_partners))

        result = collection.insert_one(onlinePartnerTemplate_dict)
        await sync_assigned_partners(db, item_name, collection)

        logging.info(f"Created template for item '{item_name}' with assigned partners: {assigned_partners}")
        return str(result.inserted_id)

    except HTTPException as he:
        raise he
    except Exception as e:
        logging.error(f"Error creating onlinePartnerTemplate for item '{item_name}': {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create template: {str(e)}")

@router.get("/", summary="Fetch All Online Partner Templates with Search (LIFO Order)")
def get_all_onlinePartnerTemplates(
    search: Optional[str] = Query(None, description="Search term for itemName"),
) -> Dict[str, Any]:
    try:
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

        cursor = collection.find(query).sort("_id", -1)
        templates = []
        for partner in cursor:
            for key, value in partner.items():
                partner[key] = convert_to_string_or_none(value)
            partner["onlinePartnerTemplateId"] = str(partner.get("_id"))
            templates.append(onlinePartnerTemplate(**partner))

        return {
            "total": len(templates),
            "results": templates
        }

    except Exception as e:
        print(f"Error fetching onlinePartnerTemplates: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/item-names", summary="Get all item names for autocomplete")
def get_item_names(
    search: Optional[str] = Query(None, description="Search term for itemName"),
    limit: int = Query(10000000, ge=1, le=10000000)
) -> List[str]:
    try:
        query = {}
        if search:
            normalized = "".join(search.lower().split())
            query = {
                "$expr": {
                    "$regexMatch": {
                        "input": {
                            "$replaceAll": {
                                "input": { "$toLower": "$itemName" },
                                "find": " ",
                                "replacement": ""
                            }
                        },
                        "regex": normalized
                    }
                }
            }
        cursor = collection.find(query, {"itemName": 1, "_id": 0}).limit(limit)
        item_names = [doc["itemName"] for doc in cursor if "itemName" in doc]
        return item_names
    except Exception as e:
        print(f"Error fetching item names: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.patch("/{onlinePartnerTemplateId}", response_model=onlinePartnerTemplate)
async def partial_update_onlinePartnerTemplate(onlinePartnerTemplateId: str, onlinePartnerTemplate: onlinePartnerTemplatePost):
    updated_onlinePartnerTemplate = {k: v for k, v in onlinePartnerTemplate.dict(exclude_unset=True).items() if v is not None}
    result = collection.update_one({"_id": ObjectId(onlinePartnerTemplateId)}, {"$set": updated_onlinePartnerTemplate})
    template_item = collection.find_one({"_id": ObjectId(onlinePartnerTemplateId)})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="onlinePartnerTemplate not found")
    if template_item:
        await sync_assigned_partners(collection.database, template_item.get("itemName"), collection)
    return await get_onlinePartnerTemplate(onlinePartnerTemplateId)

@router.delete("/{onlinePartnerTemplateId}", summary="Delete an online partner template")
async def delete_onlinePartnerTemplate(onlinePartnerTemplateId: str):
    try:
        if not ObjectId.is_valid(onlinePartnerTemplateId):
            raise HTTPException(status_code=400, detail="Invalid ObjectId format")

        template = collection.find_one({"_id": ObjectId(onlinePartnerTemplateId)})
        if not template:
            raise HTTPException(status_code=404, detail="Online partner template not found")

        item_name = template.get("itemName")
        result = collection.delete_one({"_id": ObjectId(onlinePartnerTemplateId)})

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Online partner template not found")

        if item_name:
            try:
                await sync_assigned_partners(collection.database, item_name, collection)
                logging.info(f"Successfully deleted template {onlinePartnerTemplateId} and synced partner collections")
            except Exception as sync_error:
                logging.error(f"Error during partner reference cleanup: {str(sync_error)}")

        return {"message": "Online partner template deleted successfully"}

    except HTTPException as he:
        raise he
    except Exception as e:
        logging.error(f"Error deleting online partner template {onlinePartnerTemplateId}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete template: {str(e)}")

@router.delete("/{onlinePartnerTemplateId}/bulk-delete", summary="Bulk delete online partner templates by IDs")
async def bulk_delete_online_partner_templates(
    template_ids: List[str] = Body(..., embed=True, description="List of template IDs to delete")
):
    try:
        object_ids = []
        invalid_ids = []

        for template_id in template_ids:
            if ObjectId.is_valid(template_id):
                object_ids.append(ObjectId(template_id))
            else:
                invalid_ids.append(template_id)

        if invalid_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid ObjectId format for IDs: {', '.join(invalid_ids)}"
            )

        templates = list(collection.find({"_id": {"$in": object_ids}}))
        item_names = list({t.get("itemName") for t in templates if t.get("itemName")})

        result = collection.delete_many({"_id": {"$in": object_ids}})

        if result.deleted_count == 0:
            raise HTTPException(
                status_code=404,
                detail="No templates were found with the provided IDs"
            )

        if item_names:
            try:
                for item_name in item_names:
                    await sync_assigned_partners(collection.database, item_name, collection)
                logging.info(f"Synced deletion with partner collections for items: {item_names}")
            except Exception as sync_error:
                logging.error(f"Sync error during bulk delete: {str(sync_error)}")

        return {
            "success": True,
            "message": f"Successfully deleted {result.deleted_count} templates",
            "deleted_count": result.deleted_count,
            "deleted_ids": [str(oid) for oid in object_ids],
            "affected_items": item_names
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        logging.error(f"Error in bulk deleting online partner templates: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete templates: {str(e)}"
        )

@router.post("/{partner_name}/collection-data", summary="Assign data from template to dynamic collection", response_model=Dict[str, List[str]])
async def post_template_to_dynamic_collection(
    partner_name: str,
    payload: PartnerPostPayload = Body(...)
):
    try:
        template_data = payload.template_data
        logging.info(f"Received data for partner {partner_name}")
        logging.info(f"Received payload: {[item.dict() for item in template_data]}")

        partner_collection = get_online_partners_collection()
        partner = partner_collection.find_one({
            "partnerName": {"$regex": f"^{partner_name}$", "$options": "i"}
        })
        if not partner:
            raise HTTPException(status_code=404, detail="Partner not found")

        normalized_partner_name = partner_name.lower().replace(" ", "_")
        if not normalized_partner_name:
            raise HTTPException(status_code=400, detail="Invalid partner name")

        db = get_onlinePartnerTemplate_collection().database
        template_collection = get_onlinePartnerTemplate_collection()
        dynamic_collection = db[normalized_partner_name]

        inserted_ids = []
        skipped_items = []

        for item in template_data:
            template_dict = item.dict(exclude_unset=False)
            template_dict.pop('assignedPartners', None)
            template_dict['status'] = template_dict.get('status', 'active')

            if not template_dict['itemName']:
                raise HTTPException(status_code=400, detail=f"Item name is required for item: {template_dict}")

            item_name = template_dict['itemName']

            existing_dynamic_item = dynamic_collection.find_one({"itemName": item_name})
            if existing_dynamic_item:
                logging.info(f"Item '{item_name}' already exists for partner '{partner_name}', skipping.")
                skipped_items.append(item_name)
                continue

            dynamic_dict = template_dict.copy()
            logging.info(f"Inserting into dynamic collection {normalized_partner_name}: {dynamic_dict}")
            dynamic_result = dynamic_collection.insert_one(dynamic_dict)
            inserted_ids.append(str(dynamic_result.inserted_id))

            existing_template_item = template_collection.find_one({"itemName": item_name, "status": "active"})
            if existing_template_item:
                result = template_collection.update_one(
                    {"_id": existing_template_item["_id"]},
                    {
                        "$set": {
                            "Defaultprice": template_dict.get('Defaultprice'),
                            "percentage": template_dict.get('percentage'),
                            "partnerPrice": template_dict.get('partnerPrice'),
                            "status": template_dict['status']
                        }
                    }
                )
                if result.modified_count > 0:
                    logging.info(f"Updated item {item_name} in onlinePartnerTemplate")
            else:
                template_dict['onlinePartnerTemplateId'] = template_dict.get('onlinePartnerTemplateId', None) or generate_random_id()
                template_dict['assignedPartners'] = [normalized_partner_name]
                logging.info(f"Inserting into onlinePartnerTemplate: {template_dict}")
                template_collection.insert_one(template_dict)

            await sync_assigned_partners(db, item_name, template_collection, normalized_partner_name, template_dict['status'])

        logging.info(f"Processed {len(inserted_ids)} items for {partner_name}. Skipped {len(skipped_items)} items: {skipped_items}")
        return {
            "inserted": inserted_ids,
            "duplicates": skipped_items
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        logging.error(f"Error processing items for {partner_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process items: {str(e)}")



@router.delete("/{partner_name}/item/{item_name}", summary="Delete single item from dynamic collection", response_model=str)
async def delete_dynamic_item(
    partner_name: str,
    item_name: str
):
    try:
        partner_collection = get_online_partners_collection()
        partner = partner_collection.find_one({
            "partnerName": {"$regex": f"^{partner_name}$", "$options": "i"}
        })
        if not partner:
            raise HTTPException(status_code=404, detail="Partner not found")

        normalized_partner_name = partner_name.lower().replace(" ", "_")
        if not normalized_partner_name:
            raise HTTPException(status_code=400, detail="Invalid partner name")

        db = get_onlinePartnerTemplate_collection().database
        dynamic_collection = db[normalized_partner_name]
        template_collection = get_onlinePartnerTemplate_collection()

        existing_item = dynamic_collection.find_one({"itemName": item_name})
        if not existing_item:
            raise HTTPException(status_code=404, detail=f"Item '{item_name}' not found in {partner_name}'s collection")

        delete_result = dynamic_collection.delete_one({"itemName": item_name})
        if delete_result.deleted_count == 0:
            raise HTTPException(status_code=404, detail=f"Failed to delete item '{item_name}'")

        template_collection.update_one(
            {"itemName": item_name},
            {"$pull": {"assignedPartners": normalized_partner_name}}
        )

        await sync_assigned_partners(db, item_name, template_collection, normalized_partner_name, "deactivated")
        logging.info(f"Deleted item {item_name} from {normalized_partner_name}'s collection")
        return "Item deleted successfully"
    except HTTPException as he:
        raise he
    except Exception as e:
        logging.error(f"Error deleting item {item_name} from {partner_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete item: {str(e)}")
    



@router.delete("/{partner_name}/items", summary="Bulk delete items from dynamic collection", response_model=dict)
async def bulk_delete_items(
    partner_name: str,
    request: BulkDeleteRequest
):
    try:
        # Normalize partner name first
        normalized_partner_name = partner_name.lower().replace(" ", "_")
        if not normalized_partner_name:
            raise HTTPException(status_code=400, detail="Invalid partner name")

        partner_collection = get_online_partners_collection()
        partner = partner_collection.find_one({
            "partnerName": {"$regex": f"^{partner_name}$", "$options": "i"}
        })
        if not partner:
            raise HTTPException(status_code=404, detail="Partner not found")

        db = get_onlinePartnerTemplate_collection().database
        dynamic_collection = db[normalized_partner_name]
        template_collection = get_onlinePartnerTemplate_collection()

        deleted_count = 0
        non_existent_items = []
        affected_items = []  # Track items that were actually found and processed

        for item_id in request.item_names:
            # Convert string ID to ObjectId
            try:
                obj_id = ObjectId(item_id)
            except:
                non_existent_items.append(item_id)
                continue

            # Find the item in dynamic collection to get its itemName
            existing_item = dynamic_collection.find_one({"_id": obj_id})
            if not existing_item:
                non_existent_items.append(item_id)
                continue

            item_name = existing_item.get("itemName")
            if not item_name:
                non_existent_items.append(item_id)
                continue

            delete_result = dynamic_collection.delete_one({"_id": obj_id})
            if delete_result.deleted_count > 0:
                deleted_count += 1
                affected_items.append(item_name)  # Store item_name instead of item_id for sync
                # Update template to remove this partner from assignedPartners using itemName
                template_collection.update_one(
                    {"itemName": item_name},
                    {"$pull": {"assignedPartners": normalized_partner_name}}
                )

        # Only sync if we actually deleted items
        if affected_items:
            await sync_assigned_partners(db, affected_items, template_collection, normalized_partner_name, "deactivated")

        logging.info(f"Bulk deleted {deleted_count} items from {normalized_partner_name}'s collection")
        response = {
            "deleted_count": deleted_count,
            "non_existent_items": non_existent_items,
            "affected_items": affected_items  # Return item names for frontend updates
        }

        if deleted_count == 0 and non_existent_items:
            raise HTTPException(status_code=404, detail=f"No items found to delete: {', '.join(non_existent_items)}")

        return response
    except HTTPException as he:
        raise he
    except Exception as e:
        logging.error(f"Error bulk deleting items from {partner_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to bulk delete items: {str(e)}")


@router.post("/import")
async def import_templates(file: UploadFile = File(...)):
    content = await file.read()
    filename = file.filename
    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content))
        elif filename.endswith(".json"):
            df = pd.read_json(io.BytesIO(content))
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type. Please upload CSV or JSON.")

        imported = []
        duplicates = []
        partner_updates = []
        db = collection.database
        template_collection = get_onlinePartnerTemplate_collection()
        partner_collection = get_online_partners_collection()

        for row in df.to_dict(orient="records"):
            row.pop("onlinePartnerTemplateId", None)
            item_name = str(row.get("itemName", "")).strip().upper()
            if not item_name:
                logging.warning("Skipping row with missing itemName")
                continue

            # Check for duplicates in template collection
            if template_collection.find_one({"itemName": {"$regex": f"^{re.escape(item_name)}$", "$options": "i"}}):
                duplicates.append(item_name)
                logging.info(f"Item '{item_name}' already exists in template collection, skipping.")
                continue

            assigned_partners = []
            partners_input = row.get("assignedPartners", [])
            if isinstance(partners_input, str):
                partners_input = partners_input.strip("[]").strip()
                if partners_input:
                    assigned_partners = [p.strip().lower().replace(" ", "_") for p in partners_input.split(",") if p.strip()]
            elif isinstance(partners_input, list):
                assigned_partners = [str(p).strip().lower().replace(" ", "_") for p in partners_input if p and str(p).strip()]
            elif pd.notna(partners_input):
                assigned_partners = [str(partners_input).strip().lower().replace(" ", "_")]

            default_price = float(row.get("Defaultprice", 0)) if pd.notna(row.get("Defaultprice")) else 0
            percentage = float(row.get("percentage", 0)) if pd.notna(row.get("percentage")) else 0
            partner_price = float(row.get("partnerPrice", 0)) if pd.notna(row.get("partnerPrice")) else 0
            status = str(row.get("status", "active")).lower()

            template_data = {
                "itemName": item_name,
                "Defaultprice": default_price,
                "percentage": percentage,
                "partnerPrice": partner_price,
                "status": status,
                "assignedPartners": assigned_partners,
            }

            # Insert into template collection
            result = template_collection.insert_one(template_data)
            template_id = str(result.inserted_id)
            imported.append(template_id)
            logging.info(f"Inserted template {item_name} with ID {template_id}")

            # Process each assigned partner
            for partner_name in assigned_partners:
                try:
                    normalized_partner_name = partner_name.lower().replace(" ", "_")
                    partner = partner_collection.find_one({
                        "partnerName": {"$regex": f"^{re.escape(partner_name)}$", "$options": "i"}
                    })
                    if not partner:
                        logging.warning(f"Partner {partner_name} not found in partners collection")
                        continue

                    dynamic_collection = db[normalized_partner_name]

                    # Check for existing item in dynamic collection
                    existing_dynamic_item = dynamic_collection.find_one({"itemName": item_name})
                    if existing_dynamic_item:
                        logging.info(f"Item '{item_name}' already exists in {normalized_partner_name}'s collection, skipping.")
                        duplicates.append(f"{item_name} for {partner_name}")
                        continue

                    # Insert into dynamic collection
                    partner_doc = {
                        "itemName": item_name,
                        "Defaultprice": default_price,
                        "percentage": percentage,
                        "partnerPrice": partner_price,
                        "status": status,
                    }

                    dynamic_result = dynamic_collection.insert_one(partner_doc)
                    partner_updates.append({
                        "partner": normalized_partner_name,
                        "action": "created",
                        "item": item_name
                    })
                    logging.info(f"Inserted item {item_name} into {normalized_partner_name}'s collection")

                    # Update partner's templates field
                    partner_collection.update_one(
                        {"_id": partner["_id"]},
                        {"$addToSet": {"templates": template_id}}
                    )

                    # Synchronize assigned partners
                    await sync_assigned_partners(db, item_name, template_collection, normalized_partner_name, status)

                except Exception as e:
                    logging.error(f"Error processing partner {partner_name} for item {item_name}: {str(e)}")
                    continue

        return {
            "message": f"Import completed: {len(imported)} new templates, {len(duplicates)} duplicates skipped.",
            "imported_ids": imported,
            "duplicates": duplicates,
            "partner_updates": partner_updates
        }

    except Exception as e:
        logging.error(f"Import failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Import failed: {str(e)}"
        )




@router.get("/export", response_class=StreamingResponse)
async def export_templates():
    try:
        templates = list(collection.find(
            {"status": "active"},
            {"_id": 0, "itemName": 1, "assignedPartners": 1, "Defaultprice": 1, "percentage": 1, "partnerPrice": 1}
        ))
        if not templates:
            raise HTTPException(status_code=404, detail="No active templates found to export")

        csv_stream = io.StringIO()
        fieldnames = ["S.No", "Item Name", "Assigned Partners", "Current Price", "Percentage", "Partner Price"]
        writer = csv.DictWriter(csv_stream, fieldnames=fieldnames)
        writer.writeheader()

        for index, template in enumerate(templates, 1):
            writer.writerow({
                "S.No": index,
                "Item Name": template.get("itemName", ""),
                "Assigned Partners": ", ".join(template.get("assignedPartners", [])) if template.get("assignedPartners") else "",
                "Current Price": template.get("Defaultprice", 0.0),
                "Percentage": template.get("percentage", 0),
                "Partner Price": template.get("partnerPrice", 0.0),
            })

        csv_stream.seek(0)
        return StreamingResponse(
            csv_stream,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=online_partner_templates.csv"}
        )

    except Exception as e:
        logging.error(f"Error exporting templates: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error exporting templates: {str(e)}")
    




    

@router.get("/{onlinePartnerTemplateId}", response_model=onlinePartnerTemplate)
async def get_onlinePartnerTemplate(onlinePartnerTemplateId: str):
    try:
        if not ObjectId.is_valid(onlinePartnerTemplateId):
            raise HTTPException(status_code=400, detail="Invalid ObjectId")
        partner = collection.find_one({"_id": ObjectId(onlinePartnerTemplateId)})
        if not partner:
            raise HTTPException(status_code=404, detail="onlinePartnerTemplate not found")
        for key, value in partner.items():
            partner[key] = convert_to_string_or_none(value)
        partner["onlinePartnerTemplateId"] = str(partner["_id"])
        return onlinePartnerTemplate(**partner)
    except Exception as e:
        print(f"Error fetching onlinePartnerTemplate by ID: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
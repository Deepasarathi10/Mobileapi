

from asyncio.log import logger
import csv
from datetime import datetime
import io
import re
from bson import ObjectId
from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.encoders import jsonable_encoder
from typing import List, Optional
from fastapi.responses import StreamingResponse
from pymongo import InsertOne, UpdateOne
import pytz
from .models import Sections, SectionsPost
from .utils import get_sessions_collection

router = APIRouter()



@router.post("/", response_model=Sections, status_code=status.HTTP_201_CREATED)
async def create_section(section: SectionsPost):
    try:
        section_dict = jsonable_encoder(section)
        section_dict['status'] = 'active'  # Ensure new sections are active by default
        
        # Await the insert_one operation
        new_section = await get_sessions_collection().insert_one(section_dict)
        
        # Await the find_one operation
        created_section = await get_sessions_collection().find_one({"_id": new_section.inserted_id})
        
        if created_section:
            created_section["sectionsId"] = str(created_section["_id"])  # Add sectionsId if needed
            return Sections(**created_section)
        else:
            raise HTTPException(status_code=404, detail="Failed to retrieve created section")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")





@router.get("/", response_model=List[Sections])
async def get_all_sections(branch_name: Optional[str] = None, alias_name: Optional[str] = None):
    query = {}
    if branch_name:
        query['sectionsName'] = branch_name
    if alias_name:
        query['aliasName'] = alias_name

    # Await the to_list() to get actual results
    sections = await get_sessions_collection().find(query).to_list(length=None)
    return [Sections(sectionsId=str(section["_id"]), **section) for section in sections]





@router.get("/{section_id}", response_model=Sections)
async def get_section_by_id(section_id: str):
    try:
        # Await the find_one operation
        section = await get_sessions_collection().find_one({"_id": ObjectId(section_id)})
        if section:
            section["sectionsId"] = str(section["_id"])
            return Sections(**section)
        else:
            raise HTTPException(status_code=404, detail="Section not found")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid section ID format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")






@router.patch("/{section_id}", response_model=Sections)
async def update_section(section_id: str, section_update: SectionsPost):
    try:
        update_data = {k: v for k, v in section_update.dict(exclude_unset=True).items() if v is not None}
        result = await get_sessions_collection().update_one({"_id": ObjectId(section_id)}, {"$set": update_data})
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Section not found or no changes made")

        updated_section = await get_sessions_collection().find_one({"_id": ObjectId(section_id)})
        if updated_section:
            updated_section["sectionsId"] = str(updated_section["_id"])
            return Sections(**updated_section)
        raise HTTPException(status_code=404, detail="Section not found")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid section ID format")





@router.patch("/activate/{section_id}", response_model=Sections)
async def activate_section(section_id: str):
    try:
        result = await get_sessions_collection().update_one(
            {"_id": ObjectId(section_id)},
            {"$set": {"status": "active"}}
        )
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Section not found or already active")

        updated_section = await get_sessions_collection().find_one({"_id": ObjectId(section_id)})
        if updated_section:
            updated_section["sectionsId"] = str(updated_section["_id"])
            return Sections(**updated_section)
        raise HTTPException(status_code=404, detail="Section not found")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid section ID format")




@router.patch("/deactivate/{section_id}", response_model=Sections)
async def deactivate_section(section_id: str):
    try:
        result = await get_sessions_collection().update_one(
            {"_id": ObjectId(section_id)},
            {"$set": {"status": "deactivate"}}
        )
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Section not found or already deactivated")

        updated_section = await get_sessions_collection().find_one({"_id": ObjectId(section_id)})
        if updated_section:
            updated_section["sectionsId"] = str(updated_section["_id"])
            return Sections(**updated_section)
        raise HTTPException(status_code=404, detail="Section not found")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid section ID format")




@router.delete("/{section_id}")
async def delete_section(section_id: str):
    try:
        result = await get_sessions_collection().delete_one({"_id": ObjectId(section_id)})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Section not found")
        return {"message": "Section deleted successfully"}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid section ID format")
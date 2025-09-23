
from datetime import datetime
import logging
from typing import List, Optional
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Query

from MilkReceivings.models import MilkReceiving, MilkReceivingResponse
from MilkReceivings.utils import get_milk

router = APIRouter()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@router.post("/", response_model=MilkReceivingResponse)
async def create_milk_receiving(milk: MilkReceiving):
    milk_dict = milk.dict()
    result = get_milk().insert_one(milk_dict)
    milk_dict['id'] = str(result.inserted_id)
    logger.info(f"Created milk receiving entry with ID: {milk_dict['id']}")
    return milk_dict


@router.get("/", response_model=List[MilkReceivingResponse])
async def get_milk_receivings(
    branchName: Optional[str] = Query(None, description="Filter by a single branch name (deprecated if using branchNames)"),
    branchNames: Optional[List[str]] = Query(None, description="Filter by multiple branch names"),
    date: Optional[datetime] = Query(None, description="Filter by specific date (YYYY-MM-DD)"),
    fromDate: Optional[datetime] = Query(None, description="Start of date range (YYYY-MM-DD)"),
    toDate: Optional[datetime] = Query(None, description="End of date range (YYYY-MM-DD)")
):
    query = {}
    logger.info(f"Received query parameters: branchName={branchName}, branchNames={branchNames}, date={date}, fromDate={fromDate}, toDate={toDate}")

    # Branch name filtering
    if branchNames:
        query["branchName"] = {"$in": branchNames}
    elif branchName:
        query["branchName"] = branchName

    # Date range filtering
    if fromDate and toDate:
        start = datetime.combine(fromDate.date(), datetime.min.time())
        end = datetime.combine(toDate.date(), datetime.max.time())
        query["date"] = {"$gte": start, "$lte": end}
        logger.info(f"Date range filter: {start} to {end}")
    elif date:
        start_of_day = datetime.combine(date.date(), datetime.min.time())
        end_of_day = datetime.combine(date.date(), datetime.max.time())
        query["date"] = {"$gte": start_of_day, "$lte": end_of_day}
        logger.info(f"Single date filter: {start_of_day} to {end_of_day}")

    try:
        collection = get_milk()
        milks = list(collection.find(query))
        logger.info(f"Found {len(milks)} milk receiving entries for query: {query}")

        return [
            MilkReceivingResponse(**{**milk, "id": str(milk["_id"])})
            for milk in milks
        ]
    except Exception as e:
        logger.error(f"Error fetching milk receiving data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
@router.patch("/{milk_id}")
async def patch_milk(milk_id: str, milk_patch: MilkReceiving):
    try:
        existing_vendor = get_milk().find_one({"_id": ObjectId(milk_id)})
        if not existing_vendor:
            raise HTTPException(status_code=404, detail="Entry not found")

        updated_fields = {key: value for key, value in milk_patch.dict(exclude_unset=True).items() if value is not None}
        updated_fields['updatedDate'] = datetime.now()

        if updated_fields:
            updated_fields.pop('date', None)
            result = get_milk().update_one({"_id": ObjectId(milk_id)}, {"$set": updated_fields})
            if result.modified_count == 0:
                raise HTTPException(status_code=500, detail="Failed to update vendor")

        updated_vendor = get_milk().find_one({"_id": ObjectId(milk_id)})
        updated_vendor["_id"] = str(updated_vendor["_id"])
        logger.info(f"Updated milk receiving entry with ID: {milk_id}")
        return updated_vendor
    except Exception as e:
        logger.error(f"Error patching milk receiving entry: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
# app/dailylist/Ebreading/routes.py
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, status
from typing import List, Optional
from bson import ObjectId
import logging

from Ebreading.utils import ebreading_collection  # MongoDB collection
from Ebreading.models import BranchPost, BranchResponse

router = APIRouter()
logger = logging.getLogger("uvicorn.error")


@router.get("/", response_model=List[BranchResponse])
async def get_all_branches(
    branchName: Optional[str] = Query(None, description="Filter by a single branch name (deprecated if using branchNames)"),
    branchNames: Optional[List[str]] = Query(None, description="Filter by multiple branch names"),
    date: Optional[datetime] = Query(None, description="Filter by specific date (YYYY-MM-DD)"),
    fromDate: Optional[datetime] = Query(None, description="Start of date range (YYYY-MM-DD)", deprecated=True),
    toDate: Optional[datetime] = Query(None, description="End of date range (YYYY-MM-DD)", deprecated=True)
):
    query = {}
    logger.info(f"Received query params: branchName={branchName}, branchNames={branchNames}, date={date}, fromDate={fromDate}, toDate={toDate}")

    # Branch filtering
    if branchNames:
        query["branch_name"] = {"$in": branchNames}
    elif branchName:
        query["branch_name"] = branchName

    # Date filtering on meters.date field
    if fromDate and toDate:
        start = datetime.combine(fromDate.date(), datetime.min.time())
        end = datetime.combine(toDate.date(), datetime.max.time())
        query["meters.date"] = {"$gte": start, "$lte": end}
        logger.info(f"Date range filter: {start} to {end}")
    elif date:
        start_of_day = datetime.combine(date.date(), datetime.min.time())
        end_of_day = datetime.combine(date.date(), datetime.max.time())
        query["meters.date"] = {"$gte": start_of_day, "$lte": end_of_day}
        logger.info(f"Single date filter: {start_of_day} to {end_of_day}")

    try:
        collection = ebreading_collection()
        documents = list(collection.find(query))
        logger.info(f"Found {len(documents)} documents matching query: {query}")

        result = []
        for doc in documents:
            meters = doc.get("meters", [])

            # Extra filter meters in code (safety)
            if date or (fromDate and toDate):
                meters = [m for m in meters if m.get("date") and query["meters.date"]["$gte"] <= m["date"] <= query["meters.date"]["$lte"]]
                doc["meters"] = meters

            if meters:
                doc["id"] = str(doc["_id"])
                doc.pop("_id", None)
                # You can remove fields here if you want, e.g. doc.pop("viewStates", None)
                result.append(BranchResponse(**doc))

        return result

    except Exception as e:
        logger.error(f"Error fetching branch data: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.post("/", response_model=str, status_code=status.HTTP_201_CREATED)
async def create_reading(read_data: BranchPost):
    try:
        new_reading = read_data.dict()
        result = ebreading_collection().insert_one(new_reading)
        logger.info(f"Inserted new branch with id: {result.inserted_id}")
        return str(result.inserted_id)
    except Exception as e:
        logger.error(f"Error creating reading: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.patch("/{branch_id}", response_model=dict)
async def update_branch(branch_id: str, update_data: BranchPost):
    update_dict = update_data.dict(exclude_unset=True)  # Only update provided fields

    if not update_dict:
        raise HTTPException(status_code=422, detail="No fields provided for update")

    try:
        collection = ebreading_collection()
        result = collection.update_one(
            {"_id": ObjectId(branch_id)},
            {"$set": update_dict}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Branch not found")

        updated_doc = collection.find_one({"_id": ObjectId(branch_id)})
        if updated_doc:
            updated_doc["id"] = str(updated_doc["_id"])
            updated_doc.pop("_id", None)
            return updated_doc
        else:
            raise HTTPException(status_code=404, detail="Updated branch not found")

    except Exception as e:
        logger.error(f"Failed to update branch {branch_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update branch: {str(e)}")

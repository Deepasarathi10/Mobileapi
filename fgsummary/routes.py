from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, time
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorCollection
from fgsummary.utils import get_sfgtofgdata_collection

router = APIRouter()

@router.get("/fg-summary")
async def get_fg_summary(
    date: Optional[str] = Query(None),
    branch: Optional[str] = Query(None),
):
    collection: AsyncIOMotorCollection = get_sfgtofgdata_collection()

    query = {}
    if date:
        try:
            dt = datetime.strptime(date, "%Y-%m-%d")
            start = datetime.combine(dt.date(), time.min)
            end = datetime.combine(dt.date(), time.max)
            query["dateTime"] = {"$gte": start, "$lte": end}
        except ValueError:
            raise HTTPException(
                status_code=400, detail="Invalid date format. Use YYYY-MM-DD"
            )

    if branch:
        query["branch"] = branch

    # Use Motor's async cursor
    cursor = (
        collection.find(
            query,
            {
                "_id": 0,
                "itemName": 1,
                "availableStock": 1,
                "dateTime": 1,
                "branch": 1,
                "fgCategory": 1,
            },
        )
        .sort("dateTime", -1)  # newest first
    )

    items = await cursor.to_list(length=None)

    # Add S.No and formatted Date/Time
    for index, item in enumerate(items, start=1):
        item["S.No"] = index
        item["fgCategory"] = item.get("fgCategory", "")
        dt = item.get("dateTime")
        if isinstance(dt, datetime):
            item["Date"] = dt.strftime("%Y-%m-%d")
            item["Time"] = dt.strftime("%H:%M")
        else:
            item["Date"] = ""
            item["Time"] = ""

    return {"fgItems": items}

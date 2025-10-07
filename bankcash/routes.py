import logging
from datetime import datetime
import pytz
from fastapi import HTTPException, status, APIRouter, Query
from typing import List, Optional
from bson import ObjectId

from .models import BankDeposit, BankDepositPost
from .utils import get_bank_deposit_collection

# ----------------- Logging -----------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ----------------- Timezone -----------------
IST = pytz.timezone("Asia/Kolkata")
UTC = pytz.utc

# ----------------- Router -----------------
router = APIRouter()


# ----------------- Utils -----------------
def convert_utc_to_ist(utc_dt: datetime) -> datetime:
    """Convert UTC datetime to IST (Asia/Kolkata)."""
    if utc_dt.tzinfo is None:
        utc_dt = UTC.localize(utc_dt)
    return utc_dt.astimezone(IST)


def format_datetime(dt: datetime) -> str:
    """Format datetime object to ISO 8601 without microseconds."""
    return dt.replace(microsecond=0).isoformat()


def convert_objectid_to_str(doc: dict) -> dict:
    """Convert MongoDB ObjectId to string."""
    doc["cashId"] = str(doc["_id"])
    del doc["_id"]
    return doc


# ----------------- Routes -----------------
@router.get("/", response_model=List[dict])
async def get_all_bank_deposits(
    start_date: Optional[str] = Query(None, description="Start date in DD-MM-YYYY"),
    end_date: Optional[str] = Query(None, description="End date in DD-MM-YYYY")
):
    try:
        query_filter = {}
        if start_date or end_date:
            query_filter["date"] = {}

            if start_date:
                start_dt = datetime.strptime(start_date, "%d-%m-%Y")
                # Start of day in IST → UTC
                start_dt = IST.localize(
                    start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
                ).astimezone(UTC)
                query_filter["date"]["$gte"] = start_dt

            if end_date:
                end_dt = datetime.strptime(end_date, "%d-%m-%Y")
                # End of day in IST → UTC
                end_dt = IST.localize(
                    end_dt.replace(hour=23, minute=59, second=59, microsecond=999999)
                ).astimezone(UTC)
                query_filter["date"]["$lte"] = end_dt

        collection = get_bank_deposit_collection()
        cursor = collection.find(query_filter)
        deposits = await cursor.to_list(length=None)

        result = [
            {**convert_objectid_to_str(d), "date": format_datetime(convert_utc_to_ist(d["date"]))}
            for d in deposits
        ]
        return result
    except Exception as e:
        logger.error("Error fetching deposits: %s", e)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.post("/", response_model=str, status_code=status.HTTP_201_CREATED)
async def create_bank_deposit(deposit_data: BankDepositPost):
    try:
        deposit_dict = deposit_data.dict(exclude={"cashId"})
        deposit_dict["date"] = datetime.now(UTC)  # Always store in UTC
        collection = get_bank_deposit_collection()
        result = await collection.insert_one(deposit_dict)
        return str(result.inserted_id)
    except Exception as e:
        logger.error("Error creating deposit: %s", e)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.patch("/{deposit_id}", response_model=BankDeposit)
async def update_bank_deposit(deposit_id: str, deposit_update: BankDepositPost):
    try:
        collection = get_bank_deposit_collection()
        if not ObjectId.is_valid(deposit_id):
            raise HTTPException(status_code=400, detail="Invalid deposit ID")

        existing = await collection.find_one({"_id": ObjectId(deposit_id)})
        if not existing:
            raise HTTPException(status_code=404, detail="Deposit not found")

        updated_fields = deposit_update.dict(exclude_unset=True)
        if updated_fields:
            await collection.update_one({"_id": ObjectId(deposit_id)}, {"$set": updated_fields})

        updated_doc = await collection.find_one({"_id": ObjectId(deposit_id)})
        updated_doc["cashId"] = str(updated_doc["_id"])
        return BankDeposit(**updated_doc)
    except Exception as e:
        logger.error("Error updating deposit: %s", e)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.delete("/{deposit_id}", response_model=dict)
async def delete_bank_deposit(deposit_id: str):
    try:
        collection = get_bank_deposit_collection()
        if not ObjectId.is_valid(deposit_id):
            raise HTTPException(status_code=400, detail="Invalid deposit ID")

        result = await collection.delete_one({"_id": ObjectId(deposit_id)})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Deposit not found")
        return {"message": "Deposit deleted successfully"}
    except Exception as e:
        logger.error("Error deleting deposit: %s", e)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/check", response_model=dict)
async def check_today_deposit(type: str, branchName: str):
    try:
        # Today start & end in IST → convert to UTC for DB query
        today_start = IST.localize(
            datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        ).astimezone(UTC)

        today_end = IST.localize(
            datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
        ).astimezone(UTC)

        filter_query = {
            "type": type,
            "branchName": branchName,
            "date": {
                "$gte": today_start,
                "$lte": today_end
            }
        }
        collection = get_bank_deposit_collection()
        exists = await collection.find_one(filter_query)
        return {"exists": bool(exists)}
    except Exception as e:
        logger.error("Error checking today's deposit: %s", e)
        raise HTTPException(status_code=500, detail="Internal Server Error")

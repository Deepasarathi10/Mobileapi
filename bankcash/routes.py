
# from datetime import datetime
# from typing import Dict, Optional, List
# from fastapi import HTTPException, APIRouter, Query, status
# from pydantic import BaseModel, Field
# import pytz
# from bson import ObjectId
# import logging

# from bankcash.models import BankDeposit, BankDepositPost
# from bankcash.utils import get_bank_deposit_collection

# # Timezone setup
# IST = pytz.timezone("Asia/Kolkata")
# UTC = pytz.utc

# def convert_utc_to_ist(utc_dt: datetime) -> datetime:
#     """
#     Convert UTC datetime to IST (Asia/Kolkata) and keep the same datetime format.
#     Return the datetime object with IST timezone.
#     """
#     return utc_dt.astimezone(IST)


# # MongoDB utility function to convert ObjectId to string
# def convert_objectid_to_str(deposit):
#     """
#     Convert MongoDB ObjectId to string for serialization
#     """
#     deposit["cashId"] = str(deposit["_id"])
#     del deposit["_id"]
#     return deposit

# router = APIRouter()

# @router.get("/", response_model=List[dict])
# async def get_all_bank_deposits(
#     start_date: Optional[datetime] = Query(None, description="Start date in UTC"),
#     end_date: Optional[datetime] = Query(None, description="End date in UTC")
# ):
#     """
#     Fetch all bank deposits filtered by date range in UTC.
#     Return dates in IST (Asia/Kolkata) in correct format.
#     """
#     try:
#         query_filter = {}
#         if start_date or end_date:
#             query_filter["date"] = {}
#             if start_date:
#                 query_filter["date"]["$gte"] = start_date
#             if end_date:
#                 query_filter["date"]["$lte"] = end_date

#         deposits = list(get_bank_deposit_collection().find(query_filter))

#         # Convert UTC date to IST for each deposit and format the date
#         formatted_deposits = [
#             {
#                 **convert_objectid_to_str(deposit),
#                 "date": convert_utc_to_ist(deposit["date"]).isoformat(),  # Convert UTC to IST
#             }
#             for deposit in deposits
#         ]

#         return formatted_deposits
#     except Exception as e:
#         logging.error(f"Error fetching bank deposits: {e}")
#         raise HTTPException(status_code=500, detail="Internal Server Error")


# # Create a new bank deposit
# @router.post("/", response_model=str, status_code=status.HTTP_201_CREATED)
# async def create_bank_deposit(deposit_data: BankDepositPost):
#     try:
#         new_deposit = deposit_data.dict(exclude={"cashId"})
#         result = get_bank_deposit_collection().insert_one(new_deposit)
#         return str(result.inserted_id)
#     except Exception as e:
#         logging.error(f"Error creating bank deposit: {e}")
#         raise HTTPException(status_code=500, detail="Internal Server Error")


# # Update a specific bank deposit
# @router.patch("/{deposit_id}", response_model=BankDeposit)
# async def update_bank_deposit(deposit_id: str, deposit_update: BankDepositPost):
#     try:
#         existing_deposit = get_bank_deposit_collection().find_one({"_id": ObjectId(deposit_id)})
#         if not existing_deposit:
#             raise HTTPException(status_code=404, detail="Bank deposit not found")

#         updated_fields = deposit_update.dict(exclude_unset=True)
#         if updated_fields:
#             result = get_bank_deposit_collection().update_one(
#                 {"_id": ObjectId(deposit_id)}, {"$set": updated_fields}
#             )
#             if result.modified_count == 0:
#                 raise HTTPException(status_code=500, detail="Failed to update deposit")

#         updated_deposit = get_bank_deposit_collection().find_one({"_id": ObjectId(deposit_id)})
#         updated_deposit["cashId"] = str(updated_deposit["_id"])
#         return BankDeposit(**updated_deposit)
#     except Exception as e:
#         logging.error(f"Error updating bank deposit: {e}")
#         raise HTTPException(status_code=500, detail="Internal Server Error")


# # Delete a specific bank deposit
# @router.delete("/{deposit_id}", response_model=dict, status_code=status.HTTP_200_OK)
# async def delete_bank_deposit(deposit_id: str):
#     try:
#         result = get_bank_deposit_collection().delete_one({"_id": ObjectId(deposit_id)})
#         if result.deleted_count == 0:
#             raise HTTPException(status_code=404, detail="Bank deposit not found")
#         return {"message": "Bank deposit deleted successfully"}
#     except Exception as e:
#         logging.error(f"Error deleting bank deposit: {e}")
#         raise HTTPException(status_code=500, detail="Internal Server Error")


# # Check if today's deposit exists
# @router.get("/check", response_model=dict)
# async def check_today_deposit(type: str, branchName: str):
#     """
#     Check if a deposit with the current date, specified type, and branch name exists.
#     """
#     try:
#         # Get today's date
#         today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
#         today_end = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)

#         # Query for the type, branch name, and date range
#         query_filter = {
#             "type": type,
#             "branchName": branchName,  # Include branch name in the filter
#             "date": {"$gte": today_start, "$lte": today_end}
#         }

#         # Check if such a record exists in the database
#         deposit_exists = get_bank_deposit_collection().find_one(query_filter)

#         return {"exists": bool(deposit_exists)}
#     except Exception as e:
#         logging.error(f"Error checking today's deposit: {e}")
#         raise HTTPException(status_code=500, detail="Internal Server Error")



import logging
from datetime import datetime
import pytz
from fastapi import HTTPException,status
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Query
from bson import ObjectId

from bankcash.models import BankDeposit, BankDepositPost
from bankcash.utils import get_bank_deposit_collection

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Timezone setup
IST = pytz.timezone("Asia/Kolkata")
UTC = pytz.utc




# APIRouter for bank deposit routes
router = APIRouter()

def convert_utc_to_ist(utc_dt: datetime) -> datetime:
    """
    Convert UTC datetime to IST (Asia/Kolkata) and keep the same datetime format.
    Return the datetime object with IST timezone.
    """
    logger.info("Converting UTC time %s to IST", utc_dt)
    # Ensure conversion to timezone-aware datetime
    utc_dt = pytz.utc.localize(utc_dt)  # Ensure UTC datetime is timezone-aware
    ist_time = utc_dt.astimezone(IST)  # Convert to IST timezone
    logger.info("Converted time in IST: %s", ist_time)
    return ist_time

def format_datetime_with_timezone(dt: datetime) -> str:
    """
    Format datetime object to string with timezone information.
    Ensure the correct timezone format is returned.
    """
    logger.info("Formatting datetime: %s", dt)
    # Remove microseconds and return the formatted string in ISO 8601 format
    formatted_dt = dt.replace(microsecond=0).isoformat()  # Remove microseconds and format to ISO 8601
    logger.info("Formatted datetime: %s", formatted_dt)
    return formatted_dt


# MongoDB utility function to convert ObjectId to string
def convert_objectid_to_str(deposit):
    """
    Convert MongoDB ObjectId to string for serialization
    """
    deposit["cashId"] = str(deposit["_id"])
    del deposit["_id"]
    logger.info("Converted ObjectId to string: %s", deposit["cashId"])
    return deposit




@router.get("/", response_model=List[dict])
async def get_all_bank_deposits(
    start_date: Optional[datetime] = Query(None, description="Start date in UTC"),
    end_date: Optional[datetime] = Query(None, description="End date in UTC")
):
    """
    Fetch all bank deposits filtered by date range (ignores time) in UTC.
    Return dates in IST (Asia/Kolkata) in correct format.
    """
    try:
        logger.info("Fetching bank deposits with filters: start_date=%s, end_date=%s", start_date, end_date)
        
        # Ensure we only consider the date part by stripping time from start_date and end_date
        query_filter = {}
        if start_date or end_date:
            query_filter["date"] = {}
            
            # Stripping time from start_date and end_date by using .replace()
            if start_date:
                start_date_stripped = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
                query_filter["date"]["$gte"] = start_date_stripped
            if end_date:
                end_date_stripped = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
                query_filter["date"]["$lte"] = end_date_stripped

        # Fetching deposits from the database based on the query filter
        deposits = list(get_bank_deposit_collection().find(query_filter))
        logger.info("Fetched %d deposits from the database", len(deposits))

        # Convert UTC date to IST for each deposit and format the date
        formatted_deposits = [
            {
                **convert_objectid_to_str(deposit),
                "date": format_datetime_with_timezone(convert_utc_to_ist(deposit["date"]))  # Convert and format UTC to IST
            }
            for deposit in deposits
        ]
        logger.info("Formatted %d deposits", len(formatted_deposits))

        return formatted_deposits
    except Exception as e:
        logger.error("Error fetching bank deposits: %s", e)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.post("/", response_model=str, status_code=status.HTTP_201_CREATED)
async def create_bank_deposit(deposit_data: BankDepositPost):
    try:
        logger.info("Creating a new bank deposit: %s", deposit_data)
        # Use current time in IST
        deposit_data.date = datetime.now(IST)  # Ensure we set the correct current time in IST
        new_deposit = deposit_data.dict(exclude={"cashId"})
        result = get_bank_deposit_collection().insert_one(new_deposit)
        logger.info("Created new deposit with ID: %s", result.inserted_id)
        return str(result.inserted_id)
    except Exception as e:
        logger.error("Error creating bank deposit: %s", e)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.patch("/{deposit_id}", response_model=BankDeposit)
async def update_bank_deposit(deposit_id: str, deposit_update: BankDepositPost):
    try:
        logger.info("Updating bank deposit with ID: %s", deposit_id)
        existing_deposit = get_bank_deposit_collection().find_one({"_id": ObjectId(deposit_id)})
        if not existing_deposit:
            logger.error("Bank deposit with ID %s not found", deposit_id)
            raise HTTPException(status_code=404, detail="Bank deposit not found")

        updated_fields = deposit_update.dict(exclude_unset=True)
        if updated_fields:
            result = get_bank_deposit_collection().update_one(
                {"_id": ObjectId(deposit_id)}, {"$set": updated_fields}
            )
            if result.modified_count == 0:
                logger.error("Failed to update deposit with ID: %s", deposit_id)
                raise HTTPException(status_code=500, detail="Failed to update deposit")

        updated_deposit = get_bank_deposit_collection().find_one({"_id": ObjectId(deposit_id)})
        updated_deposit["cashId"] = str(updated_deposit["_id"])
        logger.info("Updated deposit: %s", updated_deposit)
        return BankDeposit(**updated_deposit)
    except Exception as e:
        logger.error("Error updating bank deposit: %s", e)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.delete("/{deposit_id}", response_model=dict, status_code=status.HTTP_200_OK)
async def delete_bank_deposit(deposit_id: str):
    try:
        logger.info("Deleting bank deposit with ID: %s", deposit_id)
        result = get_bank_deposit_collection().delete_one({"_id": ObjectId(deposit_id)})
        if result.deleted_count == 0:
            logger.error("Bank deposit with ID %s not found", deposit_id)
            raise HTTPException(status_code=404, detail="Bank deposit not found")
        logger.info("Successfully deleted deposit with ID: %s", deposit_id)
        return {"message": "Bank deposit deleted successfully"}
    except Exception as e:
        logger.error("Error deleting bank deposit: %s", e)
        raise HTTPException(status_code=500, detail="Internal Server Error")

# Check if today's deposit exists
@router.get("/check", response_model=dict)
async def check_today_deposit(type: str, branchName: str):
    """
    Check if a deposit with the current date, specified type, and branch name exists.
    """
    try:
        # Get today's date
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)

        # Query for the type, branch name, and date range
        query_filter = {
            "type": type,
            "branchName": branchName,  # Include branch name in the filter
            "date": {"$gte": today_start, "$lte": today_end}
        }

        # Check if such a record exists in the database
        deposit_exists = get_bank_deposit_collection().find_one(query_filter)

        return {"exists": bool(deposit_exists)}
    except Exception as e:
        logging.error(f"Error checking today's deposit: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

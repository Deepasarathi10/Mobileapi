from datetime import datetime
import logging
from typing import Dict, Optional
from fastapi import HTTPException, logger
from pydantic import BaseModel, Field
import pytz



# def get_iso_datetime(timezone: str = "Asia/Kolkata") -> datetime:
#     try:
#         # Set the specified timezone
#         specified_timezone = pytz.timezone(timezone)
#     except pytz.UnknownTimeZoneError:
#         raise HTTPException(status_code=400, detail="Invalid timezone")

#     # Get the current time in the specified timezone
#     current_time = datetime.now(specified_timezone)

#     return current_time  # Return datetime object

# class BankDeposit(BaseModel):
#     cashId:Optional[str] = None
#     type:Optional[str] = None
#     cash:Optional[float] = None
#     card:Optional[float] = None
#     upi:Optional[float] = None
#     other:Optional[float] = None
#     cashBreakdown: Optional[Dict[str, int]] = None 
#     swiggy: Optional[float] = None  # Added field for Swiggy
#     zomato: Optional[float] = None  # Added field for Zomato
#     keegi: Optional[float] = None  # Added field for Kikku
#     kukkoo: Optional[float] = None  # Added field for Kukko
#     bfly: Optional[float] = None 
#     totalAmount:Optional[float] = None
#     branchName:Optional[str] = None
#     date: Optional[datetime] = Field(default_factory=lambda: get_iso_datetime("Asia/Kolkata"))

# class BankDepositPost(BaseModel):
#     type:Optional[str] = None
#     cash:Optional[float] = None
#     card:Optional[float] = None
#     upi:Optional[float] = None
#     other:Optional[float] = None
#     cashBreakdown: Optional[Dict[str, int]] = None 
#     swiggy: Optional[float] = None  # Added field for Swiggy
#     zomato: Optional[float] = None  # Added field for Zomato
#     keegi: Optional[float] = None  # Added field for Kikku
#     kukkoo: Optional[float] = None  # Added field for Kukko
#     bfly: Optional[float] = None 
#     totalAmount:Optional[float] = None
#     branchName:Optional[str] = None
#     date:Optional[datetime]= Field(default_factory=lambda: get_iso_datetime("Asia/Kolkata"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_iso_datetime(timezone: str = "Asia/Kolkata") -> datetime:
    try:
        # Set the specified timezone
        specified_timezone = pytz.timezone(timezone)
    except pytz.UnknownTimeZoneError:
        logger.error("Invalid timezone: %s", timezone)
        raise HTTPException(status_code=400, detail="Invalid timezone")

    # Get the current time in the specified timezone
    current_time = datetime.now(specified_timezone)
    logger.info("Current time in timezone %s: %s", timezone, current_time)

    return current_time  # Return datetime object

class BankDeposit(BaseModel):
    cashId: Optional[str] = None
    type: Optional[str] = None
    cash: Optional[float] = None
    card: Optional[float] = None
    upi: Optional[float] = None
    other: Optional[float] = None
    cashBreakdown: Optional[Dict[str, int]] = None
    swiggy: Optional[float] = None  # Added field for Swiggy
    zomato: Optional[float] = None  # Added field for Zomato
    keegi: Optional[float] = None  # Added field for Kikku
    kukkoo: Optional[float] = None  # Added field for Kukko
    bfly: Optional[float] = None
    totalAmount: Optional[float] = None
    branchName: Optional[str] = None
    date: Optional[datetime] = Field(default_factory=lambda: get_iso_datetime("Asia/Kolkata"))


class BankDepositPost(BaseModel):
    type: Optional[str] = None
    cash: Optional[float] = None
    card: Optional[float] = None
    upi: Optional[float] = None
    other: Optional[float] = None
    cashBreakdown: Optional[Dict[str, int]] = None
    swiggy: Optional[float] = None  # Added field for Swiggy
    zomato: Optional[float] = None  # Added field for Zomato
    keegi: Optional[float] = None  # Added field for Kikku
    kukkoo: Optional[float] = None  # Added field for Kukko
    bfly: Optional[float] = None
    totalAmount: Optional[float] = None
    branchName: Optional[str] = None
    date: Optional[datetime] = Field(default_factory=lambda: get_iso_datetime("Asia/Kolkata"))
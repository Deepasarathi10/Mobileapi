from datetime import datetime
from fastapi import HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Union

import pytz

def get_iso_datetime(timezone: str = "Asia/Kolkata") -> str:
    try:
        # Set the specified timezone
        specified_timezone = pytz.timezone(timezone)
    except pytz.UnknownTimeZoneError:
        raise HTTPException(status_code=400, detail="Invalid timezone")

    # Get the current time in the specified timezone
    current_time = datetime.now(specified_timezone)

    # Format the date and time in ISO 8601 format
    iso_datetime = current_time.isoformat()
    return iso_datetime


class PurchaseSubcategory(BaseModel):

    dispatchId: Optional[str] = None  # Define _id field explicitly
    varianceName: Optional[List[str]] = None
    uom: Optional[List[str]] = None
    itemName: Optional[List[str]] = None
    price: Optional[List[int]] = None
    itemCode: Optional[List[str]] = None
    weight: Optional[List[float]] = None
    qty: Optional[List[int]] = None
    amount: Optional[List[float]] = None
    totalAmount: Optional[float] = None
    warehouseName: Optional[str] = None
    hsnCode: Optional[str] = None
    sameDay: Optional[bool] = None  # ✅ boolean field
    date: Optional[datetime] = None  # ISO 8601 formatted datetime
    sentDate: Optional[str] = None  # ISO 8601 formatted datetime
    reason: Optional[str] = None
    branchName: Optional[str] = None
    createdBy: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None
    towarehouseCode: Optional[str] = None
    location: Optional[str] = None
    category: Optional[List[str]] = None
    subCategory: Optional[List[str]] = None
    section: Optional[str] = ""  # Added field with default empty string
    dispatchNumber: Optional[int] = None
    from_: str = Field(default="RM", alias="from")  # Static value "RM"



class PurchaseSubcategoryPost(BaseModel):

    varianceName: Optional[List[str]] = None
    uom: Optional[List[str]] = None
    itemName: Optional[List[str]] = None
    price: Optional[List[int]] = None
    itemCode: Optional[List[str]] = None
    weight: Optional[List[float]] = None
    qty: Optional[List[int]] = None
    amount: Optional[List[float]] = None
    totalAmount: Optional[float] = None
    warehouseName: Optional[str] = None
    hsnCode: Optional[str] = None
    date: Optional[str] =None
    reason: Optional[str] = None
    branchName: Optional[str] = None
    createdBy: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None
    sameDay: Optional[bool] = None  # ✅ boolean field
    towarehouseCode: Optional[str] = None
    sentDate: Optional[str] = None  # ISO 8601 formatted datetime
    location: Optional[str] = None
    category: Optional[List[str]] = None
    subCategory: Optional[List[str]] = None
    section: Optional[str] = ""  # Added field with default empty string
    dispatchNumber: Optional[int] = None
    from_: str = Field(default="RM", alias="from")  # Static value "RM"

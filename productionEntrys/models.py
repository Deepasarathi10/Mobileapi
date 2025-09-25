from datetime import datetime
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Any, Optional, List
import pytz

app = FastAPI()

# Helper function to get the formatted ISO datetime
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

# Models
class ProductionEntry(BaseModel):
    productionEntryId: Optional[str] = None  # Define _id field explicitly
    varianceName: Optional[List[str]] = None
    uom: Optional[List[str]] = None
    itemName: Optional[List[str]] = None
    price: Optional[List[int]] = None
    itemCode: Optional[List[str]] = None
    weight: Optional[List[float]] = None
    qty: Optional[List[int]] = None
    amount: Optional[List[float]] = None
    cancelVarianceName: Optional[List[str]] = None
    cancelUom: Optional[List[str]] = None
    cancelItemName: Optional[List[str]] = None
    cancelPrice: Optional[List[int]] = None
    cancelItemCode: Optional[List[str]] = None
    cancelWeight: Optional[List[float]] = None
    cancelQty: Optional[List[int]] = None
    cancelAmount: Optional[List[float]] = None
    totalAmount: Optional[Any] = None
    warehouseName: Optional[str] = None
    date: Optional[datetime] = None  # ISO 8601 formatted datetime
    reason: Optional[str] = None
    status: Optional[str] = None
    productionEntryNumber: Optional[int] = None
    createdBy:Optional[str]=None

class ProductionEntryPost(BaseModel):
    varianceName: Optional[List[str]] = None
    uom: Optional[List[str]] = None
    itemName: Optional[List[str]] = None
    price: Optional[List[int]] = None
    itemCode: Optional[List[str]] = None
    weight: Optional[List[float]] = None
    qty: Optional[List[int]] = None
    amount: Optional[List[float]] = None
    cancelVarianceName: Optional[List[str]] = None
    cancelUom: Optional[List[str]] = None
    cancelItemName: Optional[List[str]] = None
    cancelPrice: Optional[List[int]] = None
    cancelItemCode: Optional[List[str]] = None
    cancelWeight: Optional[List[float]] = None
    cancelQty: Optional[List[int]] = None
    cancelAmount: Optional[List[float]] = None
    totalAmount: Optional[str] = None
    warehouseName: Optional[str] = None
    date: Optional[str] = Field(default_factory=lambda: get_iso_datetime())
    reason: Optional[str] = None
    status: Optional[str] = None
    productionEntryNumber: Optional[int] = None
    createdBy:Optional[str]=None
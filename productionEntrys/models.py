from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from bson import ObjectId
from datetime import datetime
from dateutil import parser as date_parser
from pymongo import DESCENDING
from pydantic import BaseModel, Field
import pytz

router = APIRouter()

# Helper function to get the formatted ISO datetime
def get_iso_datetime(timezone: str = "Asia/Kolkata") -> str:
    try:
        specified_timezone = pytz.timezone(timezone)
    except pytz.UnknownTimeZoneError:
        raise HTTPException(status_code=400, detail="Invalid timezone")
    current_time = datetime.now(specified_timezone)
    return current_time.isoformat()

# Models
class ProductionEntry(BaseModel):
    productionEntryId: Optional[str] = None
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
    
    editVarianceName: Optional[List[str]] = None
    editUom: Optional[List[str]] = None
    editItemName: Optional[List[str]] = None
    editPrice: Optional[List[int]] = None
    editItemCode: Optional[List[str]] = None
    editWeight: Optional[List[float]] = None
    editQty: Optional[List[int]] = None
    editAmount: Optional[List[float]] = None
    editreason: Optional[str] = None
    
    totalAmount: Optional[str] = None  # Changed to str to match ProductionEntryPost
    warehouseName: Optional[str] = None
    date: Optional[datetime] = None
    reason: Optional[str] = None
    status: Optional[str] = None
    productionEntryNumber: Optional[str] = None  # Changed to str for "PE000X" format
    createdBy: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True  # Allow datetime objects

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
    editVarianceName: Optional[List[str]] = None
    editUom: Optional[List[str]] = None
    editItemName: Optional[List[str]] = None
    editPrice: Optional[List[int]] = None
    editItemCode: Optional[List[str]] = None
    editWeight: Optional[List[float]] = None
    editQty: Optional[List[int]] = None
    editAmount: Optional[List[float]] = None
    editreason: Optional[str] = None
    totalAmount: Optional[str] = None
    warehouseName: Optional[str] = None
    date: Optional[str] = Field(default_factory=lambda: get_iso_datetime())
    reason: Optional[str] = None
    status: Optional[str] = None
    productionEntryNumber: Optional[str] = None  # Changed to str, but ignored in POST
    createdBy: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True
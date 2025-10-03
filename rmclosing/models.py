from datetime import datetime
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Any, Optional, List
import pytz
from datetime import datetime, timedelta, timezone
from dateutil.parser import isoparse

app = FastAPI()




def get_iso_datetime(timezone: str = "Asia/Kolkata") -> str:
    try:
        tz = pytz.timezone(timezone)
    except pytz.UnknownTimeZoneError:
        raise HTTPException(status_code=400, detail="Invalid timezone")

    # ✅ Always get current UTC time
    now_utc = datetime.now(pytz.utc)

    # ✅ Convert to the server’s desired timezone (Asia/Kolkata by default)
    now_local = now_utc.astimezone(tz)

    # ✅ Return ISO string with offset
    return now_local.isoformat()

# Models
class RmClosing(BaseModel):
    requestId: Optional[str] = None  # Define _id field explicitly
    varianceName: Optional[List[str]] = None
    uom: Optional[List[str]] = None
    itemName: Optional[List[str]] = None
    price: Optional[List[int]] = None
   # itemCode: Optional[List[str]] = None
    #weight: Optional[List[float]] = None
    closingqty: Optional[List[int]] = None
    #amount: Optional[List[float]] = None
   # totalAmount: Optional[float] = None
    warehouseName: Optional[str] = None
    date: Optional[datetime] = None  # ISO 8601 formatted datetime
    
    #reason: Optional[str] = None
   # vehicleNumber:Optional [str] =None
   # driverName:Optional[str]=None
    # branchName:Optional[str] =None
    # createdBy:Optional[str]=None
    # type:Optional[str]=None
    status:Optional[str]=None
    requestNumber: Optional[str] = None  # Define _id field explicitly
    
class RmClosingPost(BaseModel):
    varianceName: Optional[List[str]] = None
    uom: Optional[List[str]] = None
    itemName: Optional[List[str]] = None
    price: Optional[List[int]] = None
    itemCode: Optional[List[str]] = None
   # weight: Optional[List[float]] = None
    closingqty: Optional[List[int]] = None
    #amount: Optional[List[float]] = None
   # totalAmount: Optional[float] = None
    warehouseName: Optional[str] = None
    date: Optional[datetime] = Field(default_factory=lambda: get_iso_datetime())
   # reason: Optional[str] = None
    #vehicleNumber:Optional [str] =None
   # driverName:Optional[str]=None
    branchName:Optional[str] =None
    #createdBy:Optional[str]=None
   # type:Optional[str]=None
    status:Optional[str]=None
    requestNumber: Optional[str] = None  # Define _id field explicitly

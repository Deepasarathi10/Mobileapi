from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
import pytz

app = FastAPI()

# Helper function to get the formatted ISO datetime
def get_iso_datetime(timezone: str = "Asia/Kolkata") -> datetime:
    try:
        # Set the specified timezone
        tz = pytz.timezone(timezone)
    except pytz.UnknownTimeZoneError:
        raise HTTPException(status_code=400, detail="Invalid timezone")

    return datetime.now(tz)



class ApprovalDetails(BaseModel):
    approvalStatus: Optional[str] = None
    approvalType: Optional[str] = None
    summary: Optional[str] = "No"
    approvalDate: Optional[datetime] = None
    approvedBy: Optional[str] = None
    

# Models
class Dispatch(BaseModel):
    dispatchId: Optional[str] = None
    varianceName: Optional[List[str]] = None
    uom: Optional[List[str]] = None
    itemName: Optional[List[str]] = None
    price: Optional[List[int]] = None
    dispatchNo: Optional[str] = None
    itemCode: Optional[List[str]] = None
    weight: Optional[List[float]] = None
    qty: Optional[List[int]] = None
    amount: Optional[List[float]] = None
    totalAmount: Optional[float] = None
    warehouseName: Optional[str] = None
    date: Optional[datetime] = None
    reason: Optional[str] = None
    vehicleNumber: Optional[str] = None
    driverName: Optional[str] = None
    driverNumber: Optional[str] = None
    branchName: Optional[str] = None
    createdBy: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None
    saleOrderNo: Optional[str] = None
    approvalDetails: Optional[List[ApprovalDetails]] = None
    receivedQty: Optional[List[int]] = None


class DispatchPost(BaseModel):
    varianceName: Optional[List[str]] = None
    uom: Optional[List[str]] = None
    dispatchNo: Optional[str] = None
    itemName: Optional[List[str]] = None
    price: Optional[List[int]] = None
    itemCode: Optional[List[str]] = None
    weight: Optional[List[float]] = None
    qty: Optional[List[int]] = None
    amount: Optional[List[float]] = None
    totalAmount: Optional[float] = None
    warehouseName: Optional[str] = None
    date: Optional[datetime] = Field(default_factory=lambda: get_iso_datetime())
    reason: Optional[str] = None
    vehicleNumber: Optional[str] = None
    driverName: Optional[str] = None
    driverNumber: Optional[str] = None
    branchName: Optional[str] = None
    createdBy: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None
    saleOrderNo: Optional[str] = None
    receivedQty: Optional[List[int]] = None
    approvalDetails: Optional[List[ApprovalDetails]] = None

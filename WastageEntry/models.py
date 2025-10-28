from datetime import datetime
from pydantic import BaseModel, Field
from typing import List, Optional

class WastageEntry(BaseModel):
    wastageId: Optional[str] = None
    wastageEntryNumber: Optional[str] = None
    varianceName: Optional[List[str]] = None
    uom: Optional[List[str]] = None
    itemName: Optional[List[str]] = None
    price: Optional[List[int]] = None
    itemCode: Optional[List[str]] = None
    sendweight: Optional[List[float]] = None
    sendqty: Optional[List[int]] = None
    sendamount: Optional[List[float]] = None
    sendtotalAmount: Optional[float] = None
    receivedweight: Optional[List[float]] = None
    receivedqty: Optional[List[int]] = None
    receivedamount: Optional[List[float]] = None
    receivedtotalAmount: Optional[float] = None
    warehouseName: Optional[str] = None
    driverName: Optional[str] = None
    branchName: Optional[str] = None
    vehicleNo: Optional[str] = None
    date: Optional[datetime] = Field(default_factory=datetime.now)
    reason: Optional[str] = None
    status: Optional[str] = Field(default="Pending")  # Added status field with default 'Pending'
    sendBy:Optional[str] = None
    receivedBy:Optional[str] = None
class WastageEntryPost(BaseModel):
    varianceName: Optional[List[str]] = None
    uom: Optional[List[str]] = None
    itemName: Optional[List[str]] = None
    price: Optional[List[int]] = None
    itemCode: Optional[List[str]] = None
    sendweight: Optional[List[float]] = None
    sendqty: Optional[List[int]] = None
    sendamount: Optional[List[float]] = None
    sendtotalAmount: Optional[float] = None
    receivedweight: Optional[List[float]] = None
    receivedqty: Optional[List[int]] = None
    receivedamount: Optional[List[float]] = None
    receivedtotalAmount: Optional[float] = None
    warehouseName: Optional[str] = None
    driverName: Optional[str] = None
    vehicleNo: Optional[str] = None
    branchName: Optional[str] = None
    date: Optional[datetime] = Field(default_factory=datetime.now)
    reason: Optional[str] = None
    status: Optional[str] = None  # Added status field, optional for creation/updates
    sendBy:Optional[str] = None
    receivedBy:Optional[str] = None
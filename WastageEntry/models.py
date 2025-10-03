from datetime import datetime
from pydantic import BaseModel, Field
from typing import List, Optional

class WastageEntry(BaseModel):
    wastageId: Optional[str] = None  # Define _id field explicitly
    wastageEntryNumber: Optional[str] = None  # NEW
    varianceName:Optional[list[str]]=None
    # category:Optional[list[str]]=None
    uom: Optional[list[str]] = None
    itemName: Optional[list[str]] = None
    price: Optional[list[int]] = None
    itemCode:Optional[list[str]]=None
    weight:Optional[list[float]]=None
    qty: Optional[list[int]] = None
    amount: Optional[List[float]] = None
    totalAmount: Optional[float] = None
    warehouseName: Optional[str] = None
    driverName:Optional[str] = None
    branchName:Optional[str] = None

    vehicleNo: Optional[str] = None
    date: Optional[datetime]= Field(default_factory=datetime.now)
    reason: Optional[str] = None
    
    
class WastageEntryPost(BaseModel):

    varianceName:Optional[list[str]]=None
  
    uom: Optional[list[str]] = None
    itemName: Optional[list[str]] = None
    price: Optional[list[int]] = None
    itemCode:Optional[list[str]]=None
    weight:Optional[list[float]]=None
    qty: Optional[list[int]] = None
    amount: Optional[List[float]] = None
    totalAmount: Optional[float] = None
    warehouseName: Optional[str] = None
    driverName:Optional[str] = None
    vehicleNo: Optional[str] = None
    branchName:Optional[str] = None
    date: Optional[datetime]= Field(default_factory=datetime.now)
    reason: Optional[str] = None
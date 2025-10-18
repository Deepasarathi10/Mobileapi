from datetime import datetime
from pydantic import BaseModel, Field
from typing import List, Optional

class WarehouseReturn(BaseModel):
    warehouseReturnId: Optional[str] = None  # Define _id field explicitly
    warehouseReturnNumber: Optional[str] = None  # NEW
    varianceName:Optional[list[str]]=None
    # category:Optional[list[str]]=None
    uom: Optional[list[str]] = None
    itemName: Optional[list[str]] = None
    price: Optional[list[int]] = None
    itemCode:Optional[list[str]]=None
    sendweight: Optional[List[float]] = None
    sendqty: Optional[List[int]] = None
    sendamount: Optional[List[float]] = None
    sendtotalamount: Optional[float] = None
    receivedweight: Optional[List[float]] = None
    receivedqty: Optional[List[int]] = None
    receivedamount: Optional[List[float]] = None
    receivedtotalamount: Optional[float] = None
    warehouseName: Optional[str] = None
    driverName:Optional[str] = None
    vehicleNo: Optional[str] = None
    branchName:Optional[str] = None
    date: Optional[datetime]= Field(default_factory=datetime.now)
    reason: Optional[str] = None
    status: Optional[str] = Field(default="Pending")  # Added status field with default 'Pending'

    
class WarehouseReturnPost(BaseModel):

    warehouseReturnNumber: Optional[str] = None  # NEW
    varianceName:Optional[list[str]]=None
    # category:Optional[list[str]]=None
    uom: Optional[list[str]] = None
    itemName: Optional[list[str]] = None
    price: Optional[list[int]] = None
    itemCode:Optional[list[str]]=None
    sendweight: Optional[List[float]] = None
    sendqty: Optional[List[int]] = None
    sendamount: Optional[List[float]] = None
    sendtotalamount: Optional[float] = None
    receivedweight: Optional[List[float]] = None
    receivedqty: Optional[List[int]] = None
    receivedamount: Optional[List[float]] = None
    receivedtotalamount: Optional[float] = None
    warehouseName: Optional[str] = None
    driverName:Optional[str] = None
    vehicleNo: Optional[str] = None
    branchName:Optional[str] = None
    date: Optional[datetime]= Field(default_factory=datetime.now)
    reason: Optional[str] = None
    status: Optional[str] = Field(default="Pending")  # Added status field with default 'Pending'
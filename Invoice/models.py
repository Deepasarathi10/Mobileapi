from pydantic import BaseModel, Field
from typing import Any, List, Optional,Union
from datetime import datetime

from orders.models import ConfigItem

class Invoice(BaseModel):
    invoiceId: Optional[str] = None
    varianceitemCode: Optional[list[str]] = None   
    itemName: Optional[List[str]] = None
    varianceName: Optional[List[str]] = None
    price: Optional[List[float]] = None
    sellingPrice: Optional[List[float]] = None
    sellingAmount: Optional[List[float]] = None
    weight: Optional[List[float]] = None
    qty: Optional[List[int]] = None
    amount: Optional[List[float]] = None
    tax: Optional[List[float]] = None
    uom: Optional[List[str]] = None
    totalAmount: Optional[float] = None
    netAmount: Optional[float] = None
    crossAmount: Optional[float] = None
    status: Optional[str] = None
    salesType: Optional[str] = None
    customerPhoneNumber: Optional[str] = "No Number"
    salesPersonId: Optional[str] = None
    salesPersonName: Optional[str] = None
    branchId: Optional[str] = None
    branchName: Optional[str] = None
    aliasName: Optional[str] = None
    paymentType: Optional[List[str]] = None
    cash: Optional[int] = None
    card: Optional[int] = None
    upi: Optional[int] = None
    others: Optional[str] = None
    invoiceDateTime: Optional[str] = None
    shiftNumber: Optional[int] = None
    shiftId: Optional[str] = None
    invoiceNo: Optional[Any] = None
    deviceNumber: Optional[int] = None
    customCharge: Optional[int] = None
    discountAmount: Optional[float] = None
    discountPercentage: Optional[int] = None    
    deviceCode:Optional[str]=None
    kotaddOns:Optional[List[ConfigItem]] = None
    createdById:Optional[str]=None
    createdByName:Optional[str]=None
    syncDateTime:Optional[datetime]=None

    
    
class InvoiceCreate(BaseModel):
    itemName: Optional[List[str]] = None
    varianceitemCode: Optional[list[str]] = None   
    varianceName: Optional[List[str]] = None
    price: Optional[List[float]] = None
    sellingPrice: Optional[List[float]] = None
    sellingAmount: Optional[List[float]] = None
    weight: Optional[List[float]] = None
    qty: Optional[List[int]] = None
    amount: Optional[List[float]] = None
    tax: Optional[List[float]] = None
    uom: Optional[List[str]] = None
    totalAmount: Optional[float] = None
    netAmount: Optional[float] = None
    crossAmount: Optional[float] = None
    advanceAmount: Optional[float] = None
    status: Optional[str] = None
    salesType: Optional[str] = None
    customerPhoneNumber: Optional[str] = "No Number"
    salesPersonId: Optional[str] = None
    salesPersonName: Optional[str] = None
    branchId: Optional[str] = None
    branchName: Optional[str] = None
    aliasName: Optional[str] = None
    paymentType: Optional[List[str]] = None
    cash: Optional[int] = None
    card: Optional[int] = None
    upi: Optional[int] = None
    others: Optional[str] = None
    invoiceDateTime: Optional[str] = None
    shiftNumber: Optional[int] = None
    shiftId: Optional[str] = None
    invoiceNo: Optional[Any] = None
    deviceNumber: Optional[int] = None
    customCharge: Optional[int] = None
    discountAmount: Optional[float] = None
    discountPercentage: Optional[int] = None   
    deviceCode:Optional[str]=None
    kotaddOns:Optional[List[ConfigItem]] = None
    createdById:Optional[str]=None
    createdByName:Optional[str]=None
    syncDateTime:Optional[datetime]=None
    
class InvoiceUpdate(BaseModel):
    itemName: Optional[List[str]] = None
    varianceitemCode: Optional[list[str]] = None   
    varianceName: Optional[List[str]] = None
    price: Optional[List[float]] = None
    sellingPrice: Optional[List[float]] = None
    sellingAmount: Optional[List[float]] = None
    weight: Optional[List[float]] = None
    qty: Optional[List[int]] = None
    amount: Optional[List[float]] = None
    tax: Optional[List[float]] = None
    uom: Optional[List[str]] = None
    itemTotalAmount: Optional[float] = None
    netAmount: Optional[float] = None
    crossAmount: Optional[float] = None
    advanceAmount: Optional[float] = None
    status: Optional[str] = None
    salesPersonId: Optional[str] = None
    salesPersonName: Optional[str] = None
    customerPhoneNumber: Optional[str] = "No Number"
    salesPerson: Optional[str] = None
    branchId: Optional[str] = None
    branchName: Optional[str] = None
    aliasName: Optional[str] = None
    paymentType: Optional[List[str]] = None
    cash: Optional[int] = None
    card: Optional[int] = None
    upi: Optional[int] = None
    others: Optional[str] = None
    invoiceDateTime: Optional[str] = None
    shiftNumber: Optional[int] = None
    shiftId: Optional[str] = None
    invoiceNo: Optional[Any] = None
    deviceNumber: Optional[int] = None
    customCharge: Optional[int] = None
    discountAmount: Optional[float] = None
    discountPercentage: Optional[int] = None    
    deviceCode:Optional[str]=None
    kotaddOns:Optional[List[ConfigItem]] = None
    createdById:Optional[str]=None
    createdByName:Optional[str]=None
    syncDateTime:Optional[datetime]=None
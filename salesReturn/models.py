from pydantic import BaseModel, Field
from typing import Any, List, Optional,Union

class SalesReturn(BaseModel):
    id: Optional[str] = Field(None, alias="salesReturnId")
    itemCode: Optional [List] =None
    itemName: Optional [List] =None
    price: Optional [List] =None
    qty: Optional [List] =None
    amount: Optional [List] =None
    tax: Optional [List] =None
    uom: Optional [List] =None
    totalAmount: Optional[str] = None
    totalAmount2: Optional[str] = None
    totalAmount3: Optional[str] = None
    status: Optional[str] = None
    branch: Optional[str] = None
    discountPercentage: Optional[str] = None
    discountAmount: Optional[str] = None
    employeeName: Optional[str] = None
    phoneNumber: Optional[str] = None
    customCharge: Optional[str] = None
    netPrice: Optional[str] = None
    invoiceNo: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    paymentType: Optional[str] = None
    salesType: Optional[str] = None
    tableType: Optional[str] = None
    invoiceDate: Optional[str] = None
    shiftNumber: Optional[str] = None
    shiftId: Optional[str] = None


class SalesReturnPost(BaseModel):

    itemCode: Optional [List] =None
    itemName: Optional [List] =None
    price: Optional [List] =None
    qty: Optional [List] =None
    amount: Optional [List] =None
    tax: Optional [List] =None
    uom: Optional [List] =None
    totalAmount:  Optional[Union[str, int]] = None
    totalAmount2: Optional[Union[str, int]] = None
    totalAmount3: Optional[Union[str, int]] = None
    status: Optional[str] = None
    branch: Optional[str] = None
    discountPercentage: Optional[Union[str, int]] = None
    discountAmount: Optional[Union[str, int]] = None
    employeeName: Optional[str] = None
    phoneNumber: Optional[Union[str, int]] = None
    customCharge: Optional[Union[str, int]] = None
    netPrice: Optional[Union[str, int]] = None
    invoiceNo: Optional[Union[str, int]] = None
    date: Optional[str] = None
    time: Optional[str] = None
    paymentType: Optional[str] = None
    salesType: Optional[str] = None
    tableType: Optional[str] = None
    invoiceDate: Optional[str] = None
    shiftNumber: Optional[Union[str, int]] = None
    shiftId: Optional[Union[str, int]] = None
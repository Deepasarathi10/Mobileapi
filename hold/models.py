from pydantic import BaseModel, Field
from typing import Any, List, Optional,Union

class Hold(BaseModel):
    holdId: Optional[str] = Field(None, alias="holdId")
    itemId: Optional[Any] = None
    itemCode: Optional[Any] = None
    itemName: Optional[Any] = None
    weight: Optional[Any] = None
    price: Optional[Any] = None
    category: Optional[str] = None
    qty: Optional[Any] = None
    amount: Optional[Any] = None
    tax: Optional[Any] = None
    uom: Optional[Any] = None
    totalAmount: Optional[str] = None
    totalAmount2: Optional[str] = None
    totalAmount3: Optional[str] = None
    status: Optional[str] = None
    branchId: Optional[str] = None
    branch: Optional[str] = None
    discountPercentage: Optional[str] = None
    discountAmount: Optional[str] = None
    employeeName: Optional[str] = None
    phoneNumber: Optional[str] = None
    phoneNumber2: Optional[str] = None
    customCharge: Optional[str] = None
    netPrice: Optional[str] = None
    invoiceNo: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    paymentType: Optional[str] = None
    salesType: Optional[str] = None
    salesReturn: Optional[str] = None
    salesReturnNumber: Optional[str] = None
    type: Optional[str] = None
    salesOrderNumber:Optional[str] = None
    customerName:Optional[str] = None
    deliveryDate:Optional[str] = None
    deliveryTime:Optional[str] = None
    event:Optional[str] = None
    advance:Optional[str] = None
    orderPreference:Optional[str] = None
    deliveryPreference:Optional[str] = None
    orderDate:Optional[str] = None
    orderTime:Optional[str] = None
    remark:Optional[str] = None
    orderInvoiceNo:Optional[str] = None
    invoiceDate:Optional[str] = None
    cash:Optional[str] = None
    upi:Optional[str] = None
    card:Optional[str] = None
    deliveryPartner:Optional[str] = None
    otherPayment:Optional[str] = None
    deliveryPartnerName:Optional[str] = None
    shiftNumber:Optional[str] = None
    shiftId:Optional[str] = None
    deliveryLocation:Optional[str] = None
    preinvoiceId: Optional[str] = None 
    
    
    
    
    
    
    
    
class HoldPost(BaseModel):
    itemId: Optional[List[Optional[str]]] = None
    itemName: Optional[List[Optional[str]]] = None
    itemCode: Optional[List[Optional[str]]] = None
    weight: Optional[List[Optional[str]]] = None
    price: Optional[List[Optional[str]]] = None
    category: Optional[List[Optional[str]]] = None
    qty: Optional[List[Optional[str]]] = None
    amount: Optional[List[Optional[str]]] = None
    tax: Optional[List[Optional[str]]] = None
    uom:Optional[List[Optional[str]]] = None
    totalAmount: Optional[Union[str,int]] = None
    totalAmount2: Optional[Union[str,int]] = None
    totalAmount3: Optional[Union[str,int]] = None
    status: Optional[str] = None
    branchId: Optional[Union[str,int]] = None
    branch: Optional[str] = None
    discountPercentage: Optional[Union[str,int]] = None
    discountAmount: Optional[Union[str,int]] = None
    employeeName: Optional[str] = None
    phoneNumber: Optional[Union[str,int]] = None
    customCharge: Optional[Union[str,int]] = None
    netPrice: Optional[Union[str,int]] = None
    invoiceNo: Optional[Union[str,int]] = None
    date: Optional[str] = None
    time: Optional[str] = None
    paymentType: Optional[str] = None
    salesType: Optional[str] = None
    salesReturn: Optional[str] = None
    salesReturnNumber: Optional[Union[str,int]] = None
    type: Optional[str] = None
    salesOrderNumber:Optional[str] = None
    customerName:Optional[str] = None
    deliveryDate:Optional[str] = None
    deliveryTime:Optional[str] = None
    event:Optional[str] = None
    advance:Optional[str] = None
    orderPreference:Optional[str] = None
    deliveryPreference:Optional[str] = None
    orderDate:Optional[str] = None
    orderTime:Optional[str] = None
    remark:Optional[str] = None
    orderInvoiceNo:Optional[str] = None
    invoiceDate:Optional[str] = None
    cash:Optional[str] = None
    upi:Optional[str] = None
    card:Optional[str] = None
    deliveryPartner:Optional[str] = None
    otherPayment:Optional[str] = None
    deliveryPartnerName:Optional[str] = None
    shiftNumber:Optional[str] = None
    shiftId:Optional[str] = None
    deliveryLocation:Optional[str] = None
    phoneNumber2: Optional[str] = None
    preinvoiceId: Optional[str] = None 
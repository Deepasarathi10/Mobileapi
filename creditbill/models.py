from datetime import datetime
from fastapi import HTTPException
from pydantic import BaseModel, Field
from typing import  Any, List, Optional,Union

class CreditBill(BaseModel):
    creditBillId: Optional[str] = None
    itemName: Optional[List[str]] = None
    qty: Optional[List[int]] = None
    price: Optional[List[int]] = None
    itemCode: Optional[List[str]] = None   
    weight: Optional[List[float]] = None
    amount: Optional[List[float]] = None
    tax: Optional[List[int]] = None
    uom: Optional[List[str]] = None
    totalAmount: Optional[float] = None
    totalAmount2: Optional[float] = None
    netPrice: Optional[float] = None
    orderInvoiceNo: Optional[str] = None
    branchId: Optional[str] = None
    branchName: Optional[str] = None
    invoiceDate: Optional[str] = None
    cash: Optional[float] = None
    card: Optional[float] = None
    upi: Optional[float] = None
    deliveryPartners: Optional[str] = None
    otherPayments: Optional[float] = None
    deliveryPartnerName: Optional[str] = None
    shiftId: Optional[str] = None
    shiftName: Optional[str] = None
    user: Optional[str] = None   
    deliveryDate: Optional[datetime] = None
    deliveryTime: Optional[str] = None
    
    customerNumber: Optional[str] = None
    customerName: Optional[str] = None
    deliveryType: Optional[str] = None
    address: Optional[str] = None
    landmark: Optional[str] = None
    discount: Optional[int] = None
    discountAmount: Optional[float] = None
    remark: Optional[str] = None
    customCharge: Optional[float] = None
    advanceAmount: Optional[float] = None
    paymentType: Optional[str] = None
    finalPrice: Optional[float] = None
    balanceAmount: Optional[float] = None
    creditBillNo: Optional[str] = None
    orderDate: Optional[str] = None
    orderTime: Optional[str] = None
    employeeName: Optional[str] = None
    status: Optional[str] =Field(default="CrediBill Order")
    cancelOrderRemark: Optional[str] = None
    
def convert_to_date(date_str: str) -> datetime:
    try:
        return datetime.strptime(date_str, "%d-%m-%Y")
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid date format. Please use dd-MM-yyyy."
        )  
class CreditBillPost(BaseModel):
    itemName: Optional[list[str]] = None
    qty: Optional[list[int]] = None
    price: Optional[list[int]] = None
    itemCode: Optional[list[str]] = None   
    weight: Optional[list[float]] = None
    amount: Optional[list[float]] = None
    tax: Optional[list[int]] = None
    uom: Optional[list[str]] = None
    totalAmount: Optional[float] = None
    totalAmount2: Optional[float] = None
    netPrice: Optional[float] = None
    orderInvoiceNo: Optional[str] = None
    branchId: Optional[str] = None
    branchName: Optional[str] = None
    invoiceDate: Optional[str] = None
    cash: Optional[float] = None
    card: Optional[float] = None
    upi: Optional[float] = None
    deliveryPartners: Optional[str] = None
    otherPayments: Optional[float] = None
    deliveryPartnerName: Optional[str] = None
    shiftId: Optional[str] = None
    shiftName: Optional[str] = None
    user: Optional[str] = None   
    deliveryDate: Optional[str] = None 
    deliveryTime: Optional[str] = None 
    customerNumber:Optional[str] = None
    customerName: Optional[str] = None
    deliveryType: Optional[str] = None
    address: Optional[str] = None
    landmark: Optional[str] = None
    discount: Optional[int] = None
    discountAmount:Optional[float] = None
    remark: Optional[str] = None
    customCharge: Optional[float] = None
    advanceAmount: Optional[float] = None
    paymentType: Optional[str] = None
    finalPrice: Optional[float] = None
    balanceAmount:Optional[float] = None
    creditBillNo: Optional[str] = None
    orderDate: Optional[str] = None
    orderTime: Optional[str] = None
    employeeName:Optional[str] = None
    status: Optional[str] =Field(default="CrediBill Order")
    cancelOrderRemark: Optional[str] = None

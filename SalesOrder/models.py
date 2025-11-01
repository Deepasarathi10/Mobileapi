from fastapi import HTTPException
from pydantic import BaseModel, Field, validator
from typing import Dict, Optional, List
from datetime import date, datetime, time


class ApprovalDetails(BaseModel):
    approvalStatus: Optional[str] = None
    approvalType: Optional[str] = None
    summary: Optional[str] = "No"
    approvalDate: Optional[datetime] = None
    approvedBy: Optional[str] = None
    previousDiscount:Optional[List[float]] = None
    previousDiscountAmount:Optional[List[float]] = None


class AdvancePaymentType(BaseModel):
    modeOfPayment: Optional[List[str]] = None
    
class ModeWiseAmount(BaseModel):
    modeOfAmount: Optional[List[float]] = None
    
class SalesOrder(BaseModel):
    salesOrderId: Optional[str] = None
    itemName: Optional[List[str]] = None
    varianceName: Optional[List[str]] = None
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
    aliasName: Optional[str] = None
    invoiceDate: Optional[datetime] = None
    receivedDate: Optional[datetime] = None
    cash: Optional[float] = None
    card: Optional[float] = None
    upi: Optional[float] = None
    deliveryPartners: Optional[str] = None
    otherPayments: Optional[float] = None
    deliveryPartnerName: Optional[str] = None
    shiftId: Optional[List[str]] = None
    shiftName: Optional[List[str]] = None
    user: Optional[List[str]] = None
    deliveryDate: Optional[datetime] = None
    deliveryTime: Optional[str] = None
    event: Optional[str] = None
    customerNumber: Optional[str] = None
    customerName: Optional[str] = None
    deliveryType: Optional[str] = None
    address: Optional[str] = None
    landmark: Optional[str] = None
    discount: Optional[int] = None
    discountAmount: Optional[float] = None
    remark: Optional[str] = None
    customCharge: Optional[float] = None
    advanceAmount:Optional[List[float]] = None
    advanceDateTime:Optional[List[datetime]] = None
    advancePaymentTerm:Optional[List[int]] = None

    advancePaymentType: Optional[List[List[str]]] = None
    modeWiseAmount: Optional[List[List[float]]] = None

    paymentType: Optional[List[str]] = None
    finalPrice: Optional[float] = None
    balanceAmount: Optional[float] = None
    saleOrderNo: Optional[str] = None
    orderDate: Optional[datetime] = Field(default_factory=datetime.now)
    orderTime: Optional[str] = None
    employeeName: Optional[str] = None
    status: Optional[str] = None
    cancelOrderRemark: Optional[str] = None
    cancelOrderDate:Optional[datetime]=None
    returnAmount: Optional[str] = None
    # approvedBy:Optional[str] = None
    canceledPersonName:Optional[str] = None
    canceledPaymentType:Optional[str]=None
    companyName:Optional[str]=None
    companyAddress:Optional[str]=None
    companyGST:Optional[str]=None
    orderType:Optional[str] =None
    createdById:Optional[str] =None
    isBoxItem:Optional[List[str]] = None
    boxQty:Optional[int] = None    
    # approvalStatus:Optional[str] =None
    # approvalType:Optional[str] =None
    # summary:Optional[str] ="No"
    # approvalDate:Optional[datetime]=None
    eventDate:Optional[str] =None
    deliveryBranchName:Optional[str]=None
    approvalDetails: Optional[List[ApprovalDetails]] = None
    itemWiseDiscountAmount:Optional[List[float]] = None
    itemWiseDiscount:Optional[List[float]] = None    


    
def convert_to_date(date_str: str) -> datetime:
    try:
        return datetime.strptime(date_str, "%d-%m-%Y")
    except ValueError: 
        raise HTTPException(
            status_code=400,
            detail="Invalid date format. Please use dd-MM-yyyy."
        )  
class SalesOrderPost(BaseModel):
    itemName: Optional[list[str]] = None
    varianceName: Optional[List[str]] = None
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
    aliasName: Optional[str] = None
    createdById:Optional[str] =None
    invoiceDate: Optional[datetime] = None
    receivedDate: Optional[datetime] = None
    cash: Optional[float] = None
    card: Optional[float] = None
    upi: Optional[float] = None
    deliveryPartners: Optional[str] = None
    otherPayments: Optional[float] = None
    deliveryPartnerName: Optional[str] = None
    shiftId: Optional[List[str]] = None
    shiftName: Optional[List[str]] = None
    user: Optional[List[str]] = None  
    # deliveryDate: Optional[str] = None
    deliveryDate: Optional[str] = None 
    deliveryTime: Optional[str] = None 
    event: Optional[str] = None
    customerNumber:Optional[str] = None
    customerName: Optional[str] = None
    deliveryType: Optional[str] = None
    address: Optional[str] = None
    landmark: Optional[str] = None
    discount: Optional[int] = None
    discountAmount:Optional[float] = None
    remark: Optional[str] = None
    customCharge: Optional[float] = None
    advanceAmount:Optional[List[float]] = None
    advanceDateTime:Optional[List[datetime]] = None
    advancePaymentTerm:Optional[List[int]] = None
    advancePaymentType: Optional[List[List[str]]] = None
    modeWiseAmount: Optional[List[List[float]]] = None
    paymentType: Optional[List[str]] = None
    finalPrice: Optional[float] = None
    balanceAmount:Optional[float] = None
    saleOrderNo: Optional[str] = None
    orderDate: Optional[datetime] = Field(default_factory=datetime.now)
    orderTime: Optional[str] = None
    employeeName:Optional[str] = None
    status: Optional[str] = None
    cancelOrderRemark: Optional[str] = None
    cancelOrderDate:Optional[datetime]=None
    returnAmount: Optional[str] = None
    # approvedBy:Optional[str] = None
    canceledPersonName:Optional[str] = None
    canceledPaymentType:Optional[str] =None
    companyName:Optional[str]=None
    companyAddress:Optional[str]=None
    companyGST:Optional[str]=None
    orderType:Optional[str] =None
    isBoxItem:Optional[List[str]] = None
    boxQty:Optional[int] = None    
    # approvalStatus:Optional[str] =None
    # approvalType:Optional[str] =None
    # summary:Optional[str] ="No"
    # approvalDate:Optional[datetime]=None
    eventDate:Optional[str] =None
    deliveryBranchName:Optional[str]=None
    approvalDetails: Optional[List[ApprovalDetails]] = None
    orderType:Optional[str] =None    
    itemWiseDiscountAmount:Optional[List[float]] = None
    itemWiseDiscount:Optional[List[float]] = None    
class Invoice(BaseModel):
    invoiceId: Optional[str] = None
    itemName: Optional[List[str]] = None
    varianceName: Optional[List[str]] = None
    price: Optional[List[float]] = None
    weight: Optional[List[float]] = None
    qty: Optional[List[int]] = None
    amount: Optional[List[float]] = None
    tax: Optional[List[float]] = None
    uom: Optional[List[str]] = None
    totalAmount: Optional[float] = None
    totalAmount2: Optional[float] = None
    totalAmount3: Optional[float] = None
    status: Optional[str] = None
    salesType: Optional[str] = None
    customerPhoneNumber: Optional[str] = "No Number"
    employeeName: Optional[str] = None
    branchId: Optional[str] = None
    branchName: Optional[str] = None
    aliasName: Optional[str] = None

    ppaymentType: Optional[List[str]] = None
    cash: Optional[int] = None
    card: Optional[int] = None
    upi: Optional[int] = None
    others: Optional[str] = None
    invoiceDate: Optional[str] = None
    # invoiceTime: Optional[str] = None
    shiftNumber: Optional[int] = None
    shiftId: Optional[int] = None 
    invoiceNo: Optional[str] = None
    deviceNumber: Optional[int] = None
    customCharge: Optional[int] = None
    discountAmount: Optional[float] = None
    discountPercentage: Optional[int] = None
    user: Optional[List[str]] = None
    deviceCode: Optional[str] = None
    approvalDate:Optional[datetime]=None
    isBoxItem:Optional[List[str]] = None
   
class SalesOrderResponse(BaseModel):
    saleOrderNo: str
    customerName: Optional[str] = None
    orderDate: Optional[datetime] = None
    deliveryDate: Optional[datetime] = None
    productionTime: Optional[datetime] = None
    dispatchTime: Optional[datetime] = None
    branchName: Optional[str] = None
    aliasName: Optional[str] = None
    createdById:Optional[str] =None
    receivedTime: Optional[datetime] = None
    invoiceTime: Optional[datetime] = None
    varianceName: Optional[List[str]] = None
    price: Optional[List[float]] = None
    weight: Optional[List[float]] = None
    qty: Optional[List[int]] = None
    amount: Optional[List[float]] = None
    tax: Optional[List[float]] = None
    uom: Optional[List[str]] = None
    totalAmount: Optional[float] = None
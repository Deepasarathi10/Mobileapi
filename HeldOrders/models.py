# from pydantic import BaseModel, Field
# from typing import Optional

# class SalesOrder(BaseModel):
#     salesOrderId: Optional[str] = None  # Define _id field explicitly
#     itemName: Optional[list[str]] = None
#     qty: Optional[list[int]] = None
#     price: Optional[list[int]] = None
#     itemCode: Optional[list[str]] = None   
#     weight: Optional[list[float]] = None
#     amount: Optional[list[float]] = None
#     tax: Optional[list[int]] = None
#     uom: Optional[list[str]] = None
#     orderInvoiceNo: Optional[str] = None
#     branchId: Optional[str] = None
#     branchName: Optional[str] = None
#     deliveryDate: Optional[str] = None
#     deliveryTime: Optional[str] = None
#     event: Optional[str] = None
#     customerNumber:Optional[str] = None
#     customerName: Optional[str] = None
#     deliveryType: Optional[str] = None
#     address: Optional[str] = None
#     landmark: Optional[str] = None
#     orderDate: Optional[str] = None
#     orderTime: Optional[str] = None
#     employeeName:Optional[str] = None
#     status: Optional[str] = None
#     cancelOrderRemark: Optional[str] = None


    
    
# class SalesOrderPost(BaseModel):
#     itemName: Optional[list[str]] = None
#     qty: Optional[list[int]] = None
#     price: Optional[list[int]] = None
#     itemCode: Optional[list[str]] = None   
#     weight: Optional[list[float]] = None
#     amount: Optional[list[float]] = None
#     tax: Optional[list[int]] = None
#     uom: Optional[list[str]] = None
#     orderInvoiceNo: Optional[str] = None
#     branchId: Optional[str] = None
#     branchName: Optional[str] = None
#     deliveryDate: Optional[str] = None
#     deliveryTime: Optional[str] = None
#     event: Optional[str] = None
#     customerNo:Optional[str] = None
#     customerName: Optional[str] = None
#     deliveryType: Optional[str] = None
#     address: Optional[str] = None
#     landmark: Optional[str] = None
#     saleOrderNo: Optional[str] = None
#     orderDate: Optional[str] = None
#     orderTime: Optional[str] = None
#     employeeName:Optional[str] = None
#     status: Optional[str] = None
#     cancelOrderRemark: Optional[str] = None


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

class ChequeDetails(BaseModel):
    chequeNumber: Optional[str] = None
    chequeHolderName: Optional[str] = None
    chequeAmount: Optional[float] = None
    bankName: Optional[str] = None
    chequeDate: Optional[datetime] = None



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
    invoiceDate: Optional[datetime] = None
    receivedDate: Optional[datetime] = None
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
    event: Optional[str] = None
    customerNumber: Optional[str] = None
    customerName: Optional[str] = None
    deliveryType: Optional[str] = None
    address: Optional[str] = None
    landmark: Optional[str] = None
    discount: Optional[int] = None
    discountAmount: Optional[float] = None
    itemWiseDiscountAmount:Optional[List[float]] = None
    itemWiseDiscount:Optional[List[float]] = None
    remark: Optional[str] = None
    customCharge: Optional[float] = None
    advanceAmount:Optional[List[float]] = None
    advanceDateTime:Optional[List[datetime]] = None
    advancePaymentType:Optional[List[str]] = None
    paymentType: Optional[str] = None
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
    # approvalStatus:Optional[str] =None
    # approvalType:Optional[str] =None
    # summary:Optional[str] ="No"
    # approvalDate:Optional[datetime]=None
    eventDate:Optional[str] =None
    deliveryBranchName:Optional[str]=None
    approvalDetails: Optional[List[ApprovalDetails]] = None
    chequeDetails: Optional[List[ChequeDetails]] = None
    isBoxItem:Optional[List[str]] = None
    totalBoxQty:Optional[List[float]] = None     

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
    itemWiseDiscount:Optional[List[float]] = None
    itemWiseDiscountAmount:Optional[List[float]] = None
    netPrice: Optional[float] = None
    orderInvoiceNo: Optional[str] = None
    branchId: Optional[str] = None
    branchName: Optional[str] = None
    invoiceDate: Optional[datetime] = None
    receivedDate: Optional[datetime] = None
    cash: Optional[float] = None
    card: Optional[float] = None
    upi: Optional[float] = None
    deliveryPartners: Optional[str] = None
    otherPayments: Optional[float] = None
    deliveryPartnerName: Optional[str] = None
    shiftId: Optional[str] = None
    shiftName: Optional[str] = None
    user: Optional[str] = None   
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
    advancePaymentType:Optional[List[str]] = None
    paymentType: Optional[str] = None
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
    # approvalStatus:Optional[str] =None
    # approvalType:Optional[str] =None
    # summary:Optional[str] ="No"
    # approvalDate:Optional[datetime]=None
    eventDate:Optional[str] =None
    deliveryBranchName:Optional[str]=None
    approvalDetails: Optional[List[ApprovalDetails]] = None
    isBoxItem:Optional[List[str]] = None
    totalBoxQty:Optional[List[float]] = None 



class HoldOrderPatch(BaseModel):
    # Core Identifiers
    salesOrderId: Optional[str] = None
    holdOrderId: Optional[str] = None
    saleOrderNo: Optional[str] = None
    aliasName: Optional[str] = None
    shiftId: Optional[str] = None
    branchId: Optional[str] = None
    branchName: Optional[str] = None
    employeeName: Optional[str] = None

    # Customer & Delivery
    customerName: Optional[str] = None
    customerNumber: Optional[str] = None
    address: Optional[str] = None
    landmark: Optional[str] = None
    deliveryDate: Optional[str] = None
    deliveryTime: Optional[str] = None
    deliveryType: Optional[str] = None
    orderDate: Optional[str] = None
    orderTime: Optional[str] = None
    event: Optional[str] = None
    eventDate: Optional[str] = None

    # Items
    itemName: Optional[List[str]] = None
    varianceName: Optional[List[str]] = None
    itemCode: Optional[List[str]] = None
    qty: Optional[List[int]] = None
    uom: Optional[List[str]] = None
    tax: Optional[List[float]] = None
    price: Optional[List[float]] = None
    weight: Optional[List[float]] = None
    amount: Optional[List[float]] = None
    isBoxItem: Optional[List[str]] = None
    boxQty: Optional[List[int]] = None
    itemWiseDiscount: Optional[List[float]] = None
    itemWiseDiscountAmount: Optional[List[float]] = None

    # Financial
    totalAmount: Optional[float] = None
    totalAmount2: Optional[float] = None
    finalPrice: Optional[float] = None
    balanceAmount: Optional[float] = None
    discount: Optional[float] = None
    discountAmount: Optional[float] = None
    customCharge: Optional[float] = None
    cash: Optional[float] = None
    card: Optional[float] = None
    upi: Optional[float] = None

    # Company Info
    companyName: Optional[str] = None
    companyAddress: Optional[str] = None
    companyGST: Optional[str] = None
    orderType: Optional[str] = None

    # Extra Info
    remark: Optional[str] = None
    status: Optional[str] = None


    # Media
    imagePath1: Optional[str] = None
    imagePath2: Optional[str] = None
    audioPath: Optional[str] = None
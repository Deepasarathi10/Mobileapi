from pydantic import BaseModel, Field
from typing import List, Optional

class ConfigItem(BaseModel):
    varianceName:str
    weight: Optional[float] = None
    configQty: Optional[List[int]] = None
    addOn: Optional[List[List[str]]] = None
    addOnPrice: Optional[List[List[int]]] = None
    variance: Optional[List[str]] = None
    type: Optional[List[str]] = None
    remark: Optional[List[str]] = None
class Diningorder(BaseModel):
    orderId: Optional[str] = None
    itemNames: Optional[List[str]]=None
    varianceNames: Optional[List[str]] = None
    prices: Optional[List[float]] = None
    weights: Optional[List[float]] = None
    quantities: Optional[List[float]] = None
    amounts: Optional[List[float]] = None
    taxes: Optional[List[float]] = None
    uoms: Optional[List[str]] = None
    totalAmount: Optional[float] = None
    status: Optional[str] = None
    orderType: Optional[str] = None
    tokenNo: Optional[int] = None
    branchName: Optional[str] = None
    table: Optional[str] = None
    seat: Optional[str] = None
    areaName: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    customerPhoneNumber: Optional[str] = None
    preinvoiceTime: Optional[str] = None
    waiter: Optional[str] = None
    deviceId: Optional[str] = None
    pax: Optional[str] = None
    hiveOrderId: Optional[str] = None
    seathiveOrderId: Optional[str] = None
    cancelledQty: Optional[List[float]] = None  # No null values allowed
    orderRemark: Optional[str] = None
    itemRemark: Optional[List[str]] = None
    partiallyCancelled: Optional[str] = None
    config: Optional[List[ConfigItem]] = None

class DiningorderCreate(BaseModel):
    itemNames: Optional[List[str]] = None  # No null values allowed in the list
    varianceNames: Optional[List[str]] = None
    prices: Optional[List[float]] = None
    weights: Optional[List[float]] = None
    quantities: Optional[List[float]] = None
    amounts: Optional[List[float]] = None
    taxes: Optional[List[float]] = None
    uoms: Optional[List[str]] = None
    totalAmount: Optional[float] = None
    status: Optional[str] = None
    orderType: Optional[str] = None
    tokenNo: Optional[int] = None
    branchName: Optional[str] = None
    table: Optional[str] = None
    seat: Optional[str] = None
    areaName: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    customerPhoneNumber: Optional[str] = None
    preinvoiceTime: Optional[str] = None
    waiter: Optional[str] = None
    deviceId: Optional[str] = None
    pax: Optional[str] = None
    hiveOrderId: Optional[str] = None
    seathiveOrderId: Optional[str] = None
    cancelledQty: Optional[List[float]] = None  # No null values allowed
    orderRemark: Optional[str] = None
    itemRemark: Optional[List[str]] = None
    partiallyCancelled: Optional[str] = None
    config: Optional[List[ConfigItem]] = None


class DiningorderUpdate(BaseModel):
    itemNames: Optional[List[str]] = None  # No null values allowed in the list
    varianceNames: Optional[List[str]] = None
    prices: Optional[List[float]] = None
    weights: Optional[List[float]] = None
    quantities: Optional[List[float]] = None
    amounts: Optional[List[float]] = None
    taxes: Optional[List[float]] = None
    uoms: Optional[List[str]] = None
    totalAmount: Optional[float] = None
    status: Optional[str] = None
    orderType: Optional[str] = None
    tokenNo: Optional[int] = None
    branchName: Optional[str] = None
    table: Optional[str] = None
    seat: Optional[str] = None
    areaName: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    customerPhoneNumber: Optional[str] = None
    preinvoiceTime: Optional[str] = None
    waiter: Optional[str] = None
    deviceId: Optional[str] = None
    pax: Optional[str] = None
    hiveOrderId: Optional[str] = None
    seathiveOrderId: Optional[str] = None
    cancelledQty: Optional[List[float]] = None  # No null values allowed
    orderRemark: Optional[str] = None
    itemRemark: Optional[List[str]] = None
    partiallyCancelled: Optional[str] = None
    config: Optional[List[ConfigItem]] = None


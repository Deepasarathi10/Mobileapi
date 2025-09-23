from pydantic import BaseModel, Field
from typing import Any, Optional, Union

class DayEnd(BaseModel):
    dayEndId: Optional[str] = None
    dayOpeningDate: Optional[str] = None
    dayOpeningTime: Optional[str] = None
    dayClosingDate: Optional[str] = None
    dayClosingTime: Optional[str] = None
    systemCashSales: Optional[Any] = None
    manualCashSales:Optional[Any]=None
    cashDifferenceAmount: Optional[Any] = None
    cashDifferenceType: Optional[Any] = None
    systemCardSales: Optional[Any] = None
    manualCardSales:Optional[Any]=None
    cardDifferenceAmount: Optional[Any] = None
    cardDifferenceType: Optional[Any] = None
    systemUpiSales: Optional[Any] = None
    manualUpiSales:Optional[Any]=None
    upiDifferenceAmount: Optional[Any] = None
    upiDifferenceType: Optional[Any] = None
    totalSystemSales: Optional[str] = None
    totalManualSales: Optional[Any] = None
    totalDifferenceAmount: Optional[str] = None
    totalDifferenceType: Optional[str] = None
    systemDeliveryPartnerSales: Optional[Any] = None
    manualDeliverypartnerSales:Optional[Any]=None
    systemOtherSales: Optional[str] = None
    manualOtherSales:Optional[Any]=None
    salesReturn: Optional[str] = None
    status: Optional[str] = None
    branchId: Optional[str] = None
    branchName: Optional[str] = None
    deviceId: Optional[str] = None
    deviceNumber: Optional[str] = None
    
    
class DayEndPost(BaseModel):
    dayEndId: Optional[str] = None
    dayOpeningDate: Optional[str] = None
    dayOpeningTime: Optional[str] = None
    dayClosingDate: Optional[str] = None
    dayClosingTime: Optional[str] = None
    systemCashSales: Optional[Any] = None
    manualCashSales:Optional[Any]=None
    cashDifferenceAmount: Optional[Any] = None
    cashDifferenceType: Optional[Any] = None
    systemCardSales: Optional[Any] = None
    manualCardSales:Optional[Any]=None
    cardDifferenceAmount: Optional[Any] = None
    cardDifferenceType: Optional[Any] = None
    systemUpiSales: Optional[Any] = None
    manualUpiSales:Optional[Any]=None
    upiDifferenceAmount: Optional[Any] = None
    upiDifferenceType: Optional[Any] = None
    totalSystemSales: Optional[str] = None
    totalManualSales: Optional[Any] = None
    totalDifferenceAmount: Optional[str] = None
    totalDifferenceType: Optional[str] = None
    systemDeliveryPartnerSales: Optional[Any] = None
    manualDeliverypartnerSales:Optional[Any]=None
    systemOtherSales: Optional[str] = None
    manualOtherSales:Optional[Any]=None
    salesReturn: Optional[str] = None
    status: Optional[str] = None
    branchId: Optional[str] = None
    branchName: Optional[str] = None
    deviceId: Optional[str] = None
    deviceNumber: Optional[str] = None
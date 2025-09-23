from pydantic import BaseModel, Field
from typing import Any, Optional, Union
from datetime import datetime
from datetime import datetime
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Any, Optional, List
import pytz

# Helper function to get the formatted ISO datetime
async def get_iso_datetime(timezone: str = "Asia/Kolkata") -> str:
    try:
        # Set the specified timezone
        specified_timezone = pytz.timezone(timezone)
    except pytz.UnknownTimeZoneError:
        raise HTTPException(status_code=400, detail="Invalid timezone")

    # Get the current time in the specified timezone
    current_time = datetime.now(specified_timezone)

    # Format the date and time in ISO 8601 format
    iso_datetime = current_time.isoformat()
    return iso_datetime

class Shift(BaseModel):
    shiftId: Optional[str] = Field(None, alias="shiftId")
    shiftNumber: Optional[Union[str, int]] = None
    OpeningDateTime: Optional[datetime] = None   # datetime type
    ClosingDateTime: Optional[datetime] = None   # datetime type
    systemOpeningBalance: Optional[str] = None
    manualOpeningBalance: Optional[str] = None
    systemClosingBalance: Optional[str] = None
    manualClosingBalance: Optional[str] = None
    openingDifferenceAmount: Optional[str] = None
    openingDifferenceType: Optional[str] = None
    closingDifferenceAmount: Optional[str] = None
    closingDifferenceType: Optional[str] = None
    systemCashSales: Optional[str] = None
    manualCashsales: Optional[Any] = None
    cashSaleDifferenceAmount: Optional[str] = None
    cashSaleDifferenceType: Optional[str] = None
    systemCardSales: Optional[str] = None
    manualCardsales: Optional[Any] = None
    cardSaleDifferenceAmount: Optional[str] = None
    cardSaleDifferenceType: Optional[str] = None
    systemUpiSales: Optional[str] = None
    manualUpisales: Optional[Any] = None
    upiSaleDifferenceAmount: Optional[str] = None
    upiSaleDifferenceType: Optional[str] = None
    deliveryPartnerSales: Optional[str] = None
    otherSystemSales: Optional[str] = None
    otherManualsales: Optional[Any] = None
    otherSaleDifferenceAmount: Optional[str] = None
    otherSaleDifferenceType: Optional[str] = None
    totalSystemSales: Optional[str] = None
    totalManualSales: Optional[Any] = None
    totalDifferenceAmount: Optional[str] = None
    totalDifferenceType: Optional[str] = None
    salesReturn: Optional[str] = None
    dayEndStatus: Optional[str] = None
    status: Optional[str] = None
    branchId: Optional[str] = None
    branchName: Optional[str] = None
    empId: Optional[str] = None
    empName: Optional[str] = None
    deviceId: Optional[str] = None
    deviceNumber: Optional[str] = None  
    

class ShiftPost(BaseModel):
    shiftNumber: Optional[Union[str, int]] = None
    OpeningDateTime: Optional[datetime] = None   # datetime type
    ClosingDateTime: Optional[datetime] = None   # datetime type
    systemOpeningBalance: Optional[str] = None
    manualOpeningBalance: Optional[str] = None
    systemClosingBalance: Optional[str] = None
    manualClosingBalance: Optional[str] = None
    openingDifferenceAmount: Optional[str] = None
    openingDifferenceType: Optional[str] = None
    closingDifferenceAmount: Optional[str] = None
    closingDifferenceType: Optional[str] = None
    systemCashSales: Optional[str] = None
    manualCashsales: Optional[Any] = None
    cashSaleDifferenceAmount: Optional[str] = None
    cashSaleDifferenceType: Optional[str] = None
    systemCardSales: Optional[str] = None
    manualCardsales: Optional[Any] = None
    cardSaleDifferenceAmount: Optional[str] = None
    cardSaleDifferenceType: Optional[str] = None
    systemUpiSales: Optional[str] = None
    manualUpisales: Optional[Any] = None
    upiSaleDifferenceAmount: Optional[str] = None
    upiSaleDifferenceType: Optional[str] = None
    deliveryPartnerSales: Optional[str] = None
    otherSystemSales: Optional[str] = None
    otherManualsales: Optional[Any] = None
    otherSaleDifferenceAmount: Optional[str] = None
    otherSaleDifferenceType: Optional[str] = None
    totalSystemSales: Optional[str] = None
    totalManualSales: Optional[Any] = None
    totalDifferenceAmount: Optional[str] = None
    totalDifferenceType: Optional[str] = None
    salesReturn: Optional[str] = None
    dayEndStatus: Optional[str] = None
    status: Optional[str] = None
    branchId: Optional[str] = None
    branchName: Optional[str] = None
    empId: Optional[str] = None
    empName: Optional[str] = None
    deviceId: Optional[str] = None
    deviceNumber: Optional[str] = None


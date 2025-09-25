from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class FgSalesData(BaseModel):
    fgGroup: str
    fgConverted: Optional[int] = Field(0, ge=0)
    fgSales: Optional[int] = Field(0, ge=0)
    fgStock: Optional[int] = Field(0, ge=0)
    dateTime: datetime


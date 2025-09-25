from datetime import datetime
from pydantic import BaseModel, Field


class FGSummaryPostRequest(BaseModel):
    itemName: str
    availableStock: int = Field(..., gt=0)
    dateTime: datetime
    branch: str
    fgCategory: str = ""
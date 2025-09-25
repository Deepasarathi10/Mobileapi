from typing import List
from pydantic import BaseModel, Field
from datetime import datetime

class ConversionDetails(BaseModel):                          
    itemName: str
    branchName: List[str]
    currentStock: List[int]
    dateTime: datetime  # Format: "31-07-2025 12:55 PM"

class FGItems(BaseModel):  
    itemName: str
    branchName: str
    availableStock: int
    fgCategory: str = ""  # optional, default empty
    

class ConversionItem(BaseModel):
    itemName: str
    availableStock: int = Field(gt=0, le=100)

class ConversionRequest(BaseModel):
    items: List[ConversionItem]
    currentStock: int
    branchName: str
    dateTime: datetime  # Expected ISO format like "2025-08-02T10:35:00"


class CustomConversionResponse(BaseModel):
    conversionDetails: ConversionDetails
    fgItems: FGItems




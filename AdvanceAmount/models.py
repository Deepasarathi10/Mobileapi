
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, List

class AdvanceAmount(BaseModel):
    amountId: Optional[str] = None
    createdDate: Optional[datetime] = None
    updatedDate: Optional[datetime] = None
    name: Optional[str] = None
    percentage: Optional[str] = None
    remarks: Optional[str] = None
    status: Optional[str] = None
    branches: Optional[List[str]] = None 
     # New field to store selected branches

class AdvanceAmountPost(BaseModel):
    name: Optional[str] = None
    percentage: Optional[str] = None
    createdDate: Optional[datetime] = None
    remarks: Optional[str] = None
    status: Optional[str] = None
    branches: Optional[List[str]] = None  # Added to handle branches in requests


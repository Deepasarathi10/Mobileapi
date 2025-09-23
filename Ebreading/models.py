# app/dailylist/Ebreading/models.py
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class Meter(BaseModel):
    meter: float
    opening_reading: float
    closing_reading: float
    consumption: float
    rate_per_unit: float
    amount: float
    date: Optional[datetime] = Field(default_factory=datetime.now) 
    status: str = Field(default="active")

class BranchPost(BaseModel):
    branch_name: str
    meters: List[Meter]  # List of Meter objects
    

class BranchResponse(BaseModel):
    id: str  # MongoDB generated ID
    branch_name: str
    reMark: str = Field(default="wait")
    viewStates:str = Field(default="wait") 
    meters: List[Meter]  # List of Meter objects with generated IDs
    
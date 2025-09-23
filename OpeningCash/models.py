from datetime import datetime
from pydantic import BaseModel, Field
from typing import  Optional , List

class OpeningCash(BaseModel):
    systemOpenCashId: Optional[str] = None
    systemOpenCash: Optional[float] = None
    branches: Optional[str] = None 
    createdDate: Optional[datetime] = None
    updatedDate: Optional[datetime] = None 
    status: Optional[str] = None
   

class OpeningCashPost(BaseModel):
    systemOpenCash: Optional[float] = None
    branches: Optional[str] = None 
    createdDate: Optional[datetime] = None
    status: Optional[str] = None
   


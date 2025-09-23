from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional , List

class PettyCash(BaseModel):
    pettyCashId: Optional[str] = None
    pettyCash: Optional[float] = None
    branches: Optional[str] = None 
    createdDate: Optional[datetime] = None
    updatedDate: Optional[datetime] = None 
    status: Optional[str] = None
   

class PettyCashPost(BaseModel):
    pettyCash: Optional[float] = None
    branches: Optional[str] = None 
    createdDate: Optional[datetime] = None
    status: Optional[str] = None
   


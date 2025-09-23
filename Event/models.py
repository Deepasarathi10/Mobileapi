from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional

class Event(BaseModel):
    eventId: Optional[str] = None
    eventname: Optional[str] = None  
    # user: Optional[str] = None
    createdDate: Optional[datetime] = None
    updatedDate: Optional[datetime] = None
    remarks: Optional[str] = None
    status: Optional[str] = None
   

class EventPost(BaseModel):
    eventname: Optional[str] = None  
    # user: Optional[str] = None
    remarks: Optional[str] = None
    status: Optional[str] = None
   


from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class EPPrice(BaseModel):
    epprice: float
    date: Optional[datetime] = Field(default_factory=datetime.now) 
    status:str =Field(default="active") 


class EppriceGet(EPPrice):
    id: str  # Ensure this includes the ID for database responses

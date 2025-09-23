from pydantic import BaseModel,Field
from typing import Optional
from datetime import datetime

class Item(BaseModel):
    # date: Optional[datetime] = Field(default_factory=datetime.now)
    location:str
    meter:list[float]
    status:str =Field(default="active") 
    date: Optional[datetime] = Field(default_factory=datetime.now) 

class ItemGet(Item):
    id:str
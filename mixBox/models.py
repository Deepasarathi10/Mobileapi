from pydantic import BaseModel, Field
from typing import List, Optional, Any
from datetime import datetime

class Item(BaseModel):
    item_name: Optional[str] = None
    uom: Optional[str] = None
    grams: Optional[float] = None

class MixBox(BaseModel):
    id: Optional[str] = None
    mixboxName: Optional[str] = None
    totalGrams: Optional[float] = None
    items: Optional[List[Item]] = None
    status: Optional[Any] = "active"
    randomId: Optional[str] = None
    createdDate: Optional[datetime] = None
    lastUpdatedDate: Optional[datetime] = None

class MixBoxPost(BaseModel):
    mixboxName: Optional[str] = None
    totalGrams: Optional[float] = None
    items: Optional[List[Item]] = None
    status: Optional[Any] = "active"
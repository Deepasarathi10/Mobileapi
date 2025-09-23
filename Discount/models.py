from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class Discount(BaseModel):
    discountId: Optional[str] = None  # Define _id field explicitly
    discountName: Optional[str] = None
    discountPercentage: Optional[str] = None
    status: Optional[str] = None
    randomId: Optional[str] = None
    createdDate: Optional[datetime] = None
    lastUpdatedDate: Optional[datetime] = None

class DiscountPost(BaseModel):
    discountName: Optional[str] = None
    discountPercentage: Optional[str] = None
    status: Optional[str] = None
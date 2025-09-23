from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional

class DeliveryType(BaseModel):
    deliveryTypeId: Optional[str] = None
    deliveryType: Optional[str] = None 
    # user: Optional[str] = None
    createdDate: Optional[datetime] = None
    updatedDate: Optional[datetime] = None
    remarks: Optional[str] = None
    status: Optional[str] = None
   

class DeliveryTypePost(BaseModel):
    deliveryType: Optional[str] = None  
    # user: Optional[str] = None
    remarks: Optional[str] = None
    status: Optional[str] = None
   


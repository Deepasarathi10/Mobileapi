
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional

class Payment(BaseModel):     ## caps P letter
    paymentTypeId: Optional[str] = None
    paymentType: Optional[str] = None
    description: Optional[str] = None
    createdDate: Optional[datetime] = None
    updatedDate: Optional[datetime] = None
    status: Optional[str] = None
    editStatus: Optional[bool] = None
   

class PaymentPost(BaseModel):     ## caps P letter
    paymentType: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    editStatus: Optional[bool] = None
   
   
   
from pydantic import BaseModel, Field
from typing import Optional

class Customer(BaseModel):
    customerId: Optional[str] = None
    customerName:Optional[str]=None
    customerPhoneNumber:Optional[str]=None
    status:Optional[str]=None
    
class CustomerPost(BaseModel):
    customerName:Optional[str]=None
    customerPhoneNumber:Optional[str]=None
    status: Optional[str] = Field(default="customer")  # Default status set to "1"
     
class CustomerPatch(BaseModel):
    customerName:Optional[str]=None
    customerPhoneNumber:Optional[str]=None
    status:Optional[str]=None
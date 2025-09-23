from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class MilkReceiving(BaseModel):
    date: Optional[datetime]= Field(default_factory=datetime.now)
    vendorName: str
    itemName: str
    packetSize: Optional[float] = None
    quantity: float
    totalLiters: float
    updatedDate:Optional[datetime] = None
    updatedQuantity: Optional[float] = None
    rate: Optional[float] = None  # Make this field optional
    amount: Optional[float] = None
    branchName: Optional[str] = None
    
    
class MilkReceivingResponse(MilkReceiving):
    id: str
 
    
   
    
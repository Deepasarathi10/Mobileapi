from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional

class WhatsappMessage(BaseModel):
    whatsappMessageId: Optional[str] = None
    status: Optional[str] = None
    createdDate: Optional[datetime] = None
    updatedDate: Optional[datetime] = None
    enable: Optional[bool] = None
    content: Optional[str] = None
  
   
class WhatsappMessagePost(BaseModel):
    status: Optional[str] = "active"  # Default value
    createdDate: Optional[datetime] = None
    enable: Optional[bool] = False    # Default value
    content: Optional[str] = None
   
   


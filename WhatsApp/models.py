
from pydantic import BaseModel, Field
from typing import Optional

class WhatsApp(BaseModel):
    whatsAppId: Optional[str] = None
    whatsAppRollName: Optional[str] = None 
    mobileNumber: Optional[str] = None 
    status: Optional[str] = None
   

class WhatsAppPost(BaseModel):
    whatsAppRollName: Optional[str] = None 
    mobileNumber: Optional[str] = None 
    status: Optional[str] = None
   
   


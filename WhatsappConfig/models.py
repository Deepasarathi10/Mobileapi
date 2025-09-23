from datetime import datetime
from pydantic import BaseModel, Field
from typing import Any, Optional, List


class SubModule(BaseModel):
    subModuleId: Optional[str] = None
    subModuleName: Optional[str] = None
    status : Optional[bool] = None
    enableMessage : Optional[List] = None
    createdDate : Optional[datetime] = None
 

class WhatsappConfig(BaseModel):
    whatsappConfigId : Optional[str] = None
    module : Optional[str] = None
    subModules : Optional[List[SubModule]] = None
    createdDate : Optional[datetime] = None
    updateddate : Optional[datetime] = None
    status : Optional[bool] = None
    phoneNumber: Optional[str] = None
    

   
class WhatsappConfigPost(BaseModel):
    module : Optional[str] = None
    subModules : Optional[List[SubModule]] = None
    createdDate : Optional[datetime] = None
    status : Optional[bool] = None
    phoneNumber: Optional[str] = None
  
   


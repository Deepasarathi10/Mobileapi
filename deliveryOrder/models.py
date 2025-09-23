from datetime import datetime
from bson import ObjectId
from pydantic import BaseModel
from typing import List, Optional

class Configs(BaseModel):
    configId: Optional[str] = None
    configName:Optional[str]=None
    # configures: Optional[List[str]]=None  # Use a list of strings if needed
    noOfChangeableDate: Optional[int] = None
    createdDate: Optional[datetime] = None   
    updatedDate: Optional[datetime] = None
    status: Optional[str] = None


class deliveryOrder(BaseModel):
    deliveryOrderId: Optional[str] = None
    configures: Optional[List[Configs]] = None
    createdDate: Optional[datetime] = None
    updatedDate: Optional[datetime] = None
    noOfChangeableDate: Optional[int] = None
    remarks: Optional[str] = None
    status: Optional[str] = None
           
class deliveryOrderPost(BaseModel):
    configures: Optional[List[Configs]] = None
    createdDate: Optional[datetime] = None
    updatedDate: Optional[datetime] = None
    noOfChangeableDate: Optional[int] = None
    remarks: Optional[str] = None
    status: Optional[str] = None
   




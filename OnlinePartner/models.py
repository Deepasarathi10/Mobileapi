from datetime import datetime
from pydantic import BaseModel
from typing import  Optional



class onlinePartners(BaseModel):
     onlinePartnersId : Optional[str] = None
     partnerName : Optional[str] = None
     createdDate : Optional[datetime] = None
     updatedDate : Optional[datetime] = None
     status : Optional[str] = None

class onlinePartnersPost(BaseModel):
     partnerName : Optional[str] = None
     createdDate : Optional[datetime] = None 
     status : Optional[str] = None     


class dynamicData(BaseModel):
    dynamicDataId : Optional[str] = None
    itemName : Optional[str] = None
    Defaultprice : Optional[float] = None
    percentage: Optional[int] = None
    partnerPrice: Optional[float] = None
    status: Optional[str] = 'active'

## FOR CREATE A DATA IN DYNAMIC PARTNERS

class dynamicDataPost(BaseModel):
    itemName : Optional[str] = None
    Defaultprice : Optional[float] = None
    percentage: Optional[int] = None
    partnerPrice: Optional[float] = None
    status: Optional[str] = "active"



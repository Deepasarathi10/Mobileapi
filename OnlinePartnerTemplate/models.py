from numpy import double
from pydantic import BaseModel, Field
from typing import  List, Optional



class onlinePartnerTemplate(BaseModel): 
    onlinePartnerTemplateId: Optional[str] = None  
    itemName: Optional[str] = None
    Defaultprice: Optional[float] = None
    percentage: Optional[int] = None
    partnerPrice: Optional[float] = None
    assignedPartners: Optional[List[str]] = None      # This will store multiple partner names
    status: Optional[str] = None

class onlinePartnerTemplatePost(BaseModel): 
    itemName: Optional[str] = None   
    Defaultprice: Optional[float] = None
    percentage: Optional[int] = None
    partnerPrice: Optional[float] = None
    status: Optional[str] = "active"
    








## SENDING THE DATA FROM THE TEMPLATE TO DYNAMIC COLLECTION
 
class partnerPost(BaseModel):
    itemName : Optional[str] = None
    Defaultprice : Optional[float] = None
    percentage: Optional[int] = None
    partnerPrice: Optional[float] = None
    status: Optional[str] = "active"




class PartnerPostPayload(BaseModel):
    template_data: List[partnerPost]   

# Define a Pydantic model for the request body
class BulkDeleteRequest(BaseModel):
    item_names: List[str]        
























# from pydantic import BaseModel, Field
# from typing import List, Optional

# class onlinePartnerTemplate(BaseModel): 
#     onlinePartnerTemplateId: Optional[str] = None  
#     itemName: Optional[str] = None
#     Defaultprice: Optional[float] = None
#     percentage: Optional[int] = None
#     partnerPrice: Optional[float] = None
#     status: Optional[str] = None
    

# class onlinePartnerTemplatePost(BaseModel): 
#     itemName: Optional[str] = None
#     Defaultprice: Optional[float] = None
#     percentage: Optional[int] = None
#     partnerPrice: Optional[float] = None
#     status: Optional[str] = None

# class partnerPost(BaseModel):
#     itemName: Optional[str] = None
#     Defaultprice: Optional[float] = None
#     percentage: Optional[int] = None
#     partnerPrice: Optional[float] = None
#     status: Optional[str] = "active"

# class PartnerPostPayload(BaseModel):
#     template_data: List[partnerPost]























    


from pydantic import BaseModel, Field
from typing import Optional

class Details(BaseModel):
    detailsId: Optional[str] = None
    details:Optional[str]=None
    value:Optional[str]=None
    
class DetailsPost(BaseModel):
    details:Optional[str]=None
    value:Optional[str]=None
     
class DetailsPatch(BaseModel):
    details:Optional[str]=None
    value:Optional[str]=None
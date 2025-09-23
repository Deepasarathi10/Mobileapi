from pydantic import BaseModel, Field
from typing import Optional

class orderType(BaseModel):
    orderTypeId: Optional[str] = None  # Define _id field explicitly
    orderTypeName: Optional[str] = None
    status: Optional[str] = None
    randomId: Optional[str] = None
class orderTypePost(BaseModel):
     orderTypeName: Optional[str] = None
     status: Optional[str] = None
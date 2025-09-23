from pydantic import BaseModel, Field
from typing import Optional

class ItemGroup(BaseModel):
    itemGroupId: Optional[str] = None  # Define _id field explicitly
    itemGroupName: Optional[str] = None
    status: Optional[str] = None
    randomId: Optional[str] = None
class ItemGroupPost(BaseModel):
     itemGroupName: Optional[str] = None
     status: Optional[str] = None
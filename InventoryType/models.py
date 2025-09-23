from pydantic import BaseModel, Field
from typing import Any, Optional

class inventory(BaseModel):
    inventoryId: Optional[str] = None
    inventoryType: Optional[str] = None
    status: Optional[str] = None
    randomId:Optional[str] = None
    
class inventoryPost(BaseModel):
    inventoryType : Optional[str] = None
    status: Optional[str] = None
    randomId: Optional[str] = None
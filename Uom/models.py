from pydantic import BaseModel, Field
from typing import Any, Optional

class uom(BaseModel):
    uomId: Optional[str] = None  # Define _id field explicitly
    measurementType :Optional[str] = None
    uom: Optional[str] = None
    precision: Optional[Any] = None
    status: Optional[str] = None
    randomId: Optional[str] = None
    
class uomPost(BaseModel):
    measurementType :Optional[str] = None
    uom: Optional[str] = None
    precision: Optional[Any] = None
    status: Optional[str] = None
    randomId: Optional[str] = None
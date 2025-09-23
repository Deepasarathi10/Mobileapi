from pydantic import BaseModel, Field
from typing import Any, Optional

class measure(BaseModel):
    measureId: Optional[str] = None
    measurementType: Optional[str] = None
    status: Optional[str] = None
    randomId:Optional[str] = None
    
class measurePost(BaseModel):
    measurementType : Optional[str] = None
    status: Optional[str] = None
    randomId: Optional[str] = None
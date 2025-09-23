from pydantic import BaseModel, Field
from typing import Optional


class TareWeight(BaseModel):
    tareId: Optional[str]  # Include the tareId field
    plateName: Optional[str] = None  
    weight: Optional[str] = None
    uom: Optional[str] = None


class TareWeightPost(BaseModel):
    plateName: Optional[str] = None  
    weight: Optional[str] = None
    uom: Optional[str] = None
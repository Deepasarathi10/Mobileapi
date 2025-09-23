from pydantic import BaseModel, Field
from typing import List, Optional

class variant(BaseModel):
    variantId: Optional[str] = None
    variant: Optional[str] = None
    variantItems: Optional[List[str]] = None  # Make this field optional
    status: Optional[str] = None
    randomId: Optional[str] = None

class variantPost(BaseModel):
    variant: Optional[str] = None
    variantItems: Optional[List[str]] = None  # Make this field optional if necessary
    status: Optional[str] = None

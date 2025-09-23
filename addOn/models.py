from pydantic import BaseModel, Field
from typing import Any, List, Optional

class addOn(BaseModel):
    addOnId: Optional[str] = None
    addOn: Optional[str] = None
    addOnItems: Optional[List[str]] = None  # Make this field optional
    value: Optional[Any] = None
    status: Optional[Any] = None
    randomId: Optional[str] = None

class addOnPost(BaseModel):
    addOn: Optional[str] = None
    addOnItems: Optional[List[str]] = None  # Make this field optional if necessary
    value: Optional[Any] = None
    status: Optional[Any] = None

from pydantic import BaseModel, Field
from typing import Optional

class tax(BaseModel):
    taxId: Optional[str] = None  # Define _id field explicitly
    taxName: Optional[str] = None
    taxPercentage: Optional[str] = None
    status: Optional[str] = None
    randomId: Optional[str] = None
class taxPost(BaseModel):
    taxName: Optional[str] = None
    taxPercentage: Optional[str] = None
    status: Optional[str] = None
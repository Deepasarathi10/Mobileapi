from pydantic import BaseModel, Field
from typing import Optional, List

class Designation(BaseModel):
    designationId: Optional[str] = None  # Define _id field explicitly
    designationName: Optional[str] = None
    status: Optional[str] = None
    randomId: Optional[str] = None

class DesignationPost(BaseModel):
    designationName: Optional[str] = None
    status: Optional[str] = None

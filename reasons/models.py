from pydantic import BaseModel, Field
from typing import List

class ReasonPostWithModule(BaseModel):
    module: str
    reason: str

class ReasonGroupResponse(BaseModel):
    id: str = Field(..., alias="id")
    module: str
    reasons: List[str]

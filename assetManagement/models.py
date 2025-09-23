from pydantic import BaseModel, Field
from typing import Optional

class asset(BaseModel):
    assetId: Optional[str] = None  # Define _id field explicitly
    assetName: Optional[str] = None
    serialNo: Optional[str] = None
    status: Optional[str] = None
    randomId: Optional[str] = None
class assetPost(BaseModel):
    assetName: Optional[str] = None
    serialNo: Optional[str] = None
    status: Optional[str] = None
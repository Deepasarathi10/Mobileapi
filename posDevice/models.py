from pydantic import BaseModel, Field
from typing import Any, Optional

class postDevice(BaseModel):
    postDeviceId: Optional[str] = None
    device: Optional[str] = None
    deviceName : Optional[str] = None
    branchName : Optional[str] = None
    deviceCode : Optional[str] = None
    status: Optional[str] = None
    randomId:Optional[str] = None
    
class postDevicePost(BaseModel):
    device: Optional[str] = None
    deviceName : Optional[str] = None
    branchName : Optional[str] = None
    deviceCode : Optional[str] = None
    status: Optional[str] = None
    randomId: Optional[str] = None
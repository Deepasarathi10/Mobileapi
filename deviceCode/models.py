from pydantic import BaseModel, Field
from typing import Optional

class DeviceCode(BaseModel):
    deviceCodeId: Optional[str] = None
    companyName: Optional[str] = None
    companyId: Optional[str] = None
    deviceCode: Optional[str] = None
    deviceName: Optional[str] = None
    assetName: Optional[str] = None
    branchName: Optional[str] = None
    status: Optional[str] = None
    randomId: Optional[str] = None
class DeviceCodePost(BaseModel):  
     companyName: Optional[str] = None
     companyId: Optional[str] = None
     deviceCode: Optional[str] = None
     status: Optional[str] = None
     deviceName: Optional[str] = None
     branchName: Optional[str] = None
     assetName: Optional[str] = None
class DeviceCodePatch(BaseModel):
     companyName: Optional[str] = None
     companyId: Optional[str] = None
     deviceCode: Optional[str] = None
     status: Optional[str] = None
     deviceName: Optional[str] = None
     branchName: Optional[str] = None
     assetName: Optional[str] = None
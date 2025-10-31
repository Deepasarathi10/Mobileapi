from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, List, Union

class ItemType(BaseModel):
    itemtransferId: Optional[str] = None  
    itemCode: Optional[List[str]] = None
    itemName: Optional[List[str]] = None
    reqQty: Optional[List[Union[int, float]]] = None   # ✅ both int & float
    uom: Optional[List[str]] = None
    price: Optional[List[float]] = None                # ✅ price can be decimal
    receivedQty: Optional[List[Union[int, float]]] = None  
    sendQty: Optional[List[Union[int, float]]] = None  
    fromBranch: Optional[str] = None
    toBranch: Optional[str] = None
    fromLoginId: Optional[str] = None
    toLoginId: Optional[str] = None
    wareHouseCode: Optional[str] = None
    requestDateTime: Optional[datetime] = None  
    sentDateTime: Optional[datetime] = None  
    receiveDateTime: Optional[datetime] = None
    rejectDateTime: Optional[datetime] = None 
    status: Optional[str] = None


class ItemTypePost(BaseModel):
    itemCode: Optional[List[str]] = None
    itemName: Optional[List[str]] = None
    reqQty: Optional[List[Union[int, float]]] = None   # ✅ both supported
    uom: Optional[List[str]] = None
    price: Optional[List[float]] = None
    approvedQty: Optional[List[float]] = None
    receivedQty:Optional[List[Union[int, float]]] = None 
    sendQty:Optional[List[Union[int, float]]] = None 
    fromBranch: Optional[str] = None
    toBranch: Optional[str] = None
    fromLoginId: Optional[str] = None
    toLoginId: Optional[str] = None
    wareHouseCode: Optional[str] = None
    requestDateTime: Optional[datetime] = Field(default_factory=datetime.utcnow)
    sentDateTime: Optional[datetime] = Field(default_factory=datetime.utcnow)
    receiveDateTime: Optional[datetime] = Field(default_factory=datetime.utcnow)
    rejectDateTime: Optional[datetime] = Field(default_factory=datetime.utcnow)
    status: Optional[str] = None

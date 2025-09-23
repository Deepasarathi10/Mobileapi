from pydantic import BaseModel
from typing import Optional, List ,Any,Union

class Variance(BaseModel):
    varianceid: Optional[str] 
    varianceName: Optional[str] = None
    uom: Optional[str] = None
    varianceItemcode: Optional[str] = None
    status: Optional[str] = None
    subcategory: Optional[str] = None
    price: Optional[Union[float,int]] = None
    netPrice:  Optional[Union[float,int]] = None
    qr_code: Optional[str] = None
    shelfLife: Optional[int] = None  
    reorderLevel: Optional[int] = None
    itemName: Optional[str] = None
    tax: Optional[str] = None
    hsnCode: Optional[str] = None   

class VarianceCreate(BaseModel):
    varianceName:  Optional[str]= None
    uom:  Optional[str] = None
    varianceItemcode:  Optional[str] = None
    status:  Optional[str] = None
    subcategory:  Optional[str] = None
    price:   Optional[Union[float,int]] = None
    netPrice:  Optional[Union[float,int]] = None
    qr_code: Optional[str] =None
    shelfLife: Optional[int] = None
    reorderLevel: Optional[int] = None
    itemName: Optional[str] = None
    tax: Optional[str] = None
    hsnCode: Optional[str] = None 

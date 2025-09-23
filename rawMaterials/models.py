from pydantic import BaseModel, Field
from typing import Any, List, Optional, Union


class RawMaterials(BaseModel):
    rawMaterialid: Optional[str] 
    varianceName: Optional[str] = None
    uom: Optional[str] = None
    varianceItemcode: Optional[str] = None
    status: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    price: Optional[Union[float,int]] = None
    netPrice:  Optional[Union[float,int]] = None
    qr_code: Optional[str] = None
    shelfLife: Optional[int] = None  
    reorderLevel: Optional[int] = None
    itemName: Optional[str] = None
    tax: Optional[int] = None
    availableStock: Optional[float] = None
    hsnCode: Optional[str] = None

class RawMaterialsCreate(BaseModel):
    varianceName:  Optional[str]= None
    uom:  Optional[str] = None
    varianceItemcode:  Optional[str] = None
    status:  Optional[str] = None
    category:  Optional[str] = None
    subcategory:  Optional[str] = None
    price:   Optional[Union[float,int]] = None
    netPrice:  Optional[Union[float,int]] = None
    qr_code: Optional[str] =None
    shelfLife: Optional[int] = None
    reorderLevel: Optional[int] = None
    itemName: Optional[str] = None
    tax: Optional[int] = None
    availableStock: Optional[float] = None
    hsnCode: Optional[str] = None

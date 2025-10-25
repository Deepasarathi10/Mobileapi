from pydantic import BaseModel
from typing import Optional, List

class WarehouseStock(BaseModel):
    warehouseName: str
    stock: int

class WarehouseItemPost(BaseModel):
    varianceName: Optional[str] = ""
    variance_Uom: Optional[str] = ""
    varianceitemCode: Optional[str] = ""
    status: Optional[str] = ""
    system_stock: Optional[List[WarehouseStock]] = []
    subcategory: Optional[str] = ""
    variance_Defaultprice: Optional[float] = 0
    netPrice: Optional[float] = 0
    qr_code: Optional[str] = ""
    selfLife: Optional[int] = 0
    reorderLevel: Optional[int] = 0
    itemName: Optional[str] = ""
    tax: Optional[str] = ""
    hsnCode: Optional[str] = ""
    plateItems: Optional[bool] = True
    measurementType: Optional[str] = None

class WarehouseItemPatch(BaseModel):
    varianceName: Optional[str]
    variance_Uom: Optional[str]
    varianceitemCode: Optional[str]
    status: Optional[str]
    system_stock: Optional[List[WarehouseStock]]
    subcategory: Optional[str]
    variance_Defaultprice: Optional[float]
    netPrice: Optional[float]
    qr_code: Optional[str]
    selfLife: Optional[int]
    reorderLevel: Optional[int]
    itemName: Optional[str]
    tax: Optional[str]
    hsnCode: Optional[str]
    plateItems: Optional[bool]
    measurementType: Optional[str] = None

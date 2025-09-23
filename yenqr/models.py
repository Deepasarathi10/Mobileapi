from pydantic import BaseModel, Field
from typing import Optional ,List ,Any,Dict

class BranchwiseItem(BaseModel):
    branchwiseItemId: Optional[str]=None
    branchId: Optional[List[Any]]  = None 
    branch: Optional[List[Any]]  = None
    varianceName: Optional[str] = None
    itemName: Optional[str] = None
    defaultPrice: Optional[int] = None
    varianceItemcode: Optional[str] = None
    uom: Optional[str] = None
    tax:Optional[Any] =None
    hsnCode:Optional[Any] =None
    availableStock:Optional[str] =None
    category:Optional[str] =None
    description:Optional[Any] =None
    status: Optional[str] = None
    orderType:Optional[Any]  = None 
    itemId: Optional[str] = None
    create_item_Date: Optional[str] = None
    updated_item_Date: Optional[str] = None
    promotional_Offer:Optional[str]=None
    

class BranchwiseItemPost(BaseModel):
    branchId: Optional[List[Any]]  = None 
    branch:  Optional[List[Any]]  = None 
    varianceName: Optional[str] = None
    itemName: Optional[str] = None
    defaultPrice: Optional[int] = None
    varianceItemcode: Optional[str] = None
    uom: Optional[str] = None
    tax:Optional[Any] =None
    hsnCode:Optional[str] =None
    availableStock:Optional[str] =None
    category:Optional[str] =None
    type:Optional[str] =None
    description:Optional[str] =None
    itemType:Optional[str]=None
    status: Optional[str] = None
    type: Optional[str] = None
    orderType: Optional[Any]  = None 
    itemId: Optional[str] = None
    create_item_Date: Optional[str] = None
    updated_item_Date: Optional[str] = None
    promotional_Offer:Optional[str]=None
    
    
class BranchwiseItemPatch(BaseModel):
    varianceName: Optional[str] = None
    itemName: Optional[str] = None
    defaultPrice: Optional[float] = None
    varianceItemcode: Optional[str] = None
    uom: Optional[str] = None
    tax: Optional[Any] = None
    hsnCode: Optional[str] = None
    availableStock: Optional[int] = None
    category: Optional[str] = None
    type: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    orderType: Optional[dict] = None
    create_item_Date: Optional[str] = None
    updated_item_Date: Optional[str] = None
    promotional_Offer:Optional[str]=None


class ItemUpdate(BaseModel):
  
    updates: Dict[Any, Any]





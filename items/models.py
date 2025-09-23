from pydantic import BaseModel, Field
from typing import Optional,Any

class Item(BaseModel):
    itemid: Optional[str] = None
    itemCode: Optional[str] = None
    itemName: Optional[str] = None
    uom: Optional[str] = None
    tax: Optional[Any] = None
    category: Optional[str] = None
    itemGroup: Optional[str] = None
    status: Optional[str] = None
    description: Optional[Any] = None
    itemType: Optional[str] = None
    ordertype: Optional[str] = None
    create_item_date: Optional[str] = None
    updated_item_date: Optional[str] = None

class ItemPost(BaseModel):
    itemCode: Optional[str] = None
    itemName: Optional[str] = None
    uom: Optional[str] = None
    tax: Optional[str] = None
    category: Optional[str] = None
    itemGroup: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None
    itemType: Optional[str] = None
    ordertype: Optional[str] = None
    create_item_date: Optional[str] = None
    updated_item_date: Optional[str] = None

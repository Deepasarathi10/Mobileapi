from pydantic import BaseModel, Field
from typing import Optional

class SfgItems(BaseModel):
    sfgItemsId: Optional[str] = None  # Define _id field explicitly
    sfgName: Optional[str] = None
    price: Optional[int] = None
    uom: Optional[str] = None  # Define _id field explicitly
    fgCategory: Optional[str] = None   
    stockQty: Optional[float] = None   

    status: Optional[str] = None
    
   
class SfgItemsPost(BaseModel):
    sfgName: Optional[str] = None
    price: Optional[int] = None
    uom: Optional[str] = None  # Define _id field explicitly
    fgCategory: Optional[str] = None   
    stockQty: Optional[float] = None   
    status: Optional[str] = None
    
    

   
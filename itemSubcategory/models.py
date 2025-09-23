from pydantic import BaseModel, Field
from typing import Optional

class itemSubcategory(BaseModel):
    subCategoryId: Optional[str] = None  # Define _id field explicitly
    subCategoryName: Optional[str] = None
    status: Optional[str] = None
    randomId: Optional[str] = None
class itemSubcategoryPost(BaseModel):
    subCategoryName: Optional[str] = None
    status: Optional[str] = None
from pydantic import BaseModel, Field
from typing import Optional, List

class Category(BaseModel):
    categoryId: Optional[str] = None  # Define _id field explicitly
    categoryName: Optional[str] = None
    subCategory: Optional[List[str]] = None
    status: Optional[str] = None
    randomId: Optional[str] = None

class CategoryPost(BaseModel):
    categoryName: Optional[str] = None
    subCategory: Optional[List[str]] = None
    status: Optional[str] = None

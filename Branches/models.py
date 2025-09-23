from pydantic import BaseModel, Field
from typing import Any, Optional

class branch(BaseModel):
    branchId: Optional[str] = None  # Define _id field explicitly
    branchName: Optional[str] = None
    aliasName:Optional[str] =None 
    status: Optional[Any] = None
    randomId: Optional[str] = None
    address: Optional[Any] = None  # Define _id field explicitly
    country: Optional[str] = None
    state: Optional[Any] = None
    city: Optional[str] = None
    postalCode: Optional[Any] = None  # Define _id field explicitly
    phoneNumber: Optional[Any] = None
    email: Optional[str] = None
    latitude: Optional[Any] = None
    longitude: Optional[Any] = None
    description: Optional[str] = None
    openingHours: Optional[Any] = None
    managerName: Optional[str] = None
    managerContact: Optional[Any] = None  
    createdDate: Optional[str] = None
    lastUpdatedDate: Optional[str] = None
    code: Optional[str] = None
    location: Optional[str] = None
    Section: Optional[str] = None
    createdBy:Optional[str]=None
    
class branchPost(BaseModel):
    branchName: Optional[str] = None
    aliasName:Optional[str] =None 
    status: Optional[str] = None
    randomId: Optional[str] = None
    address: Optional[str] = None  # Define _id field explicitly
    country: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    postalCode: Optional[str] = None  # Define _id field explicitly
    phoneNumber: Optional[str] = None
    email: Optional[str] = None
    latitude: Optional[str] = None
    longitude: Optional[str] = None
    description: Optional[str] = None
    openingHours: Optional[str] = None
    managerName: Optional[str] = None
    managerContact: Optional[str] = None  # Define _id field explicitly
    createdDate: Optional[str] = None
    code: Optional[str] = None
    location: Optional[str] = None
    Section: Optional[str] = None
    lastUpdatedDate: Optional[str] = None
    createdBy:Optional[str]=None
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class WareHouse(BaseModel):
    wareHouseId: Optional[str] = None  # <-- This will map from MongoDB _id
    wareHouseName: Optional[str] = None 
    aliasName: Optional[str] = None
    status: Optional[int] = None
    randomId: Optional[str] = None
    address: Optional[str] = None
    country: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    postalCode: Optional[int] = None
    phoneNumber: Optional[str] = None
    email: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    description: Optional[str] = None
    openingHours: Optional[datetime] = None
    closingHours: Optional[datetime] = None
    managerName: Optional[str] = None
    managerContact: Optional[str] = None
    createdDate: Optional[datetime] = None
    lastUpdatedDate: Optional[datetime] = None
    createdBy: Optional[str] = None

class WareHousePost(BaseModel):
    wareHouseName: Optional[str] = None 
    aliasName: Optional[str] = None
    status: Optional[int] = None
    randomId: Optional[str] = None
    address: Optional[str] = None
    country: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    postalCode: Optional[int] = None
    phoneNumber: Optional[str] = None
    email: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    description: Optional[str] = None
    openingHours: Optional[datetime] = None
    closingHours: Optional[datetime] = None
    managerName: Optional[str] = None
    managerContact: Optional[str] = None
    createdDate: Optional[datetime] = None
    lastUpdatedDate: Optional[datetime] = None
    createdBy: Optional[str] = None

from pydantic import BaseModel, Field, validator
from typing import Any, Optional
from datetime import date, datetime
from bson import ObjectId

class BirthDayCake(BaseModel):
    id: Optional[str] = None
    cakeId: Optional[str] = None
    varianceName: Optional[str] = None
    branchName: Optional[str] = None
    selfLife: Optional[int] = None
    productionDate: Optional[date] = None
    expiryDate: Optional[date] = None
    status: Optional[str] = None
    itemCode: Optional[str] = None
    manufacture: Optional[str] = None
    recievedDate:Optional[str] = None
    
    @validator('productionDate', 'expiryDate', pre=False, always=True)
    def convert_date_to_datetime(cls, v):
        """Convert date objects to datetime for MongoDB compatibility"""
        if v and isinstance(v, date) and not isinstance(v, datetime):
            return datetime.combine(v, datetime.min.time())
        return v
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
            ObjectId: str
        }
        # For MongoDB, we need to use dict() instead of json() directly
        orm_mode = True

class BirthDayCakePost(BaseModel):
    cakeId: Optional[str] = None
    varianceName: Optional[str] = None
    branchName: Optional[str] = None
    selfLife: Optional[int] = None
    productionDate: Optional[date] = None
    expiryDate: Optional[date] = None
    status: Optional[str] = None
    itemCode: Optional[str] = None
    manufacture: Optional[str] = None
    recievedDate:Optional[str] = None
    
    @validator('productionDate', 'expiryDate', pre=False, always=True)
    def convert_date_to_datetime(cls, v):
        """Convert date objects to datetime for MongoDB compatibility"""
        if v and isinstance(v, date) and not isinstance(v, datetime):
            return datetime.combine(v, datetime.min.time())
        return v
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat()
        }
        orm_mode = True
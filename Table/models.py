

from pydantic import BaseModel, Field
from typing import List, Optional
from bson import ObjectId as BsonObjectId


class Table(BaseModel):
    tableNumber:Optional[str] = None
    seats: Optional[int] = None
   


class Area(BaseModel):
    # areaId: Optional[str] = None
    areaName: str
    tables: List[Table]
    tableCount: Optional[int] = Field(None, alias='tableCount')
    status:Optional[str] = 'active'

class TablesCreate(BaseModel):
    totalTableCount: int
    totalTable: List[Area]
    type: str
    location: str
    status:Optional[str] = 'active'

class TablesResponse(BaseModel):
    tableId: Optional[str] = Field(None, alias="_id")
    totalTableCount: int
    totalTable: List[Area]
    type: str
    location: str
    status : Optional[str] = None

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            BsonObjectId: str
        }


class UpdateTableModel(BaseModel):
    totalTableCount: Optional[int] = None
    totalTable: Optional[List[Area]] = None
    type: Optional[str] = None
    location: Optional[str] = None
    status:Optional[str] = 'active'
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class kotTableStatus(BaseModel):
    kotTableStatusId: Optional[str] = None
    fullyBookedSeatCount: Optional[int] = None
    partiallyBookedSeatCount: Optional[int] = None
    availableSeatCount: Optional[int] = None
    fullyBookedTables: List[str] = None
    partiallyBookedTables: List[str] = None
    availableTables:  List[str] = None
    branchName: Optional[str] = None
    status: Optional[str] = None
    updatedDate:Optional[str] = None
    updatedTime: Optional[str] = None
    hiveStatusId:  Optional[str] = None

class kotTableStatusPost(BaseModel):  
    fullyBookedSeatCount: Optional[int] = None
    partiallyBookedSeatCount: Optional[int] = None
    availableSeatCount: Optional[int] = None
    fullyBookedTables: List[str] = None
    partiallyBookedTables: List[str] = None
    availableTables:  List[str] = None
    branchName: Optional[str] = None
    status: Optional[str] = None
    updatedDate: Optional[str] =  None
    updatedTime: Optional[str] =  None
    hiveStatusId:  Optional[str] = None

class kotTableStatusPatch(BaseModel):
    fullyBookedSeatCount: Optional[int] = None
    partiallyBookedSeatCount: Optional[int] = None
    availableSeatCount: Optional[int] = None
    fullyBookedTables: List[str] = None
    partiallyBookedTables: List[str] = None
    availableTables:  List[str] = None
    branchName: Optional[str] = None
    status: Optional[str] = None
    updatedDate: Optional[str] =  None
    updatedTime: Optional[str] =  None
    hiveStatusId:  Optional[str] = None
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class Employee(BaseModel):
   # id:str
    empName: Optional[str]=None
    date: Optional[datetime] = Field(default_factory=datetime.now)
    status: str = Field(default="active")
    branchId: Optional[str] = None
    branchName: Optional[str] = None
    viewStates: Optional[str] = Field(default="wait")
    reMark: str = Field(default="wait")



class RemarkUpdate(BaseModel):
    reMark: str = Field(..., description="Remark text to update")
 
class viewStatesUpdate(BaseModel):
   viewStates: str = Field(..., description="viewStates text to update")
    
class EmployeeGet(Employee):
    id: str

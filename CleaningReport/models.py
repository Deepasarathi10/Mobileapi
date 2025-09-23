from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Employee(BaseModel):
    empName:str
    date:Optional[datetime]= Field(default_factory=datetime.now)
    status: str = Field(default="active")
    branchId:Optional[str] =None
    branchName:Optional[str] =None
    reMark: str = Field(default="wait")
    viewStates: str = Field(default="wait")
    
class RemarkUpdate(BaseModel):
    reMark: str = Field(..., description="Remark text to update")
class viewStatesUpdate(BaseModel):
   viewStates: str = Field(..., description="viewStates text to update")
class EmployeeGet(Employee):
  
    id:str
  
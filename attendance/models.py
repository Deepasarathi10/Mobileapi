from pydantic import BaseModel, Field
from typing import Any, Optional,Union
from datetime import date
from datetime import time


class Attendance(BaseModel):
    id: Optional[str] = Field(None, alias="id")
    empId: Optional[str] = None
    empNumber: Optional[str] = None
    empName: Optional[str] = None
    reportingDate: Optional[str] = None
    reportingTime: Optional[str] = None
    manualReportingDate: Optional[str] = None
    manualReportingTime: Optional[str] = None
    reportingLocation: Optional[str] = None
    reportingType: Optional[str] = None
    baseLocation: Optional[str] = None


class AttendancePut(BaseModel):
    empId: Optional[Union[int, str]] = None
    empNumber: Optional[Union[int, str]] = None
    empName: Optional[str] = None
    reportingDate: Optional[Union[str, date]] = None
    reportingTime: Optional[Union[str, time]] = None
    manualReportingDate: Optional[Union[str, date]] = None
    manualReportingTime: Optional[Union[str, time]] = None
    reportingLocation: Optional[str] = None
    reportingType: Optional[str] = None
    baseLocation: Optional[str] = None
    
    
   
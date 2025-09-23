from pydantic import BaseModel, Field
from typing import Any, Optional,Union ,List



class FacialRecognition(BaseModel):
    id: Optional[str] = Field(None, alias="facialRecognizationId")
    empId: Optional[str] = None
    empNumber: Optional[str] = None
    empName: Optional[str] = None
    templates: Optional[List] = None
    faceJpg: Optional[List] = None
    _class: Optional[str] = None


class FacialRecognitionPost(BaseModel):

    empId: Optional[Union[str, int]] = None
    empNumber: Optional[Union[str, int]] = None
    empName: Optional[str] = None
    templates: Optional[List] = None
    faceJpg: Optional[List] = None
    _class: Optional[str] = None
    
    
   
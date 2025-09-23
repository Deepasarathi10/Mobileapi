from pydantic import BaseModel, Field
from typing import Optional


class Gst(BaseModel):
    gstId: Optional[str] = None  
    gst: Optional[str] = None
    status: Optional[str] = None


class GstPost(BaseModel):
    gst: Optional[str] = None
    status: Optional[str] = None

from datetime import datetime
from typing import Optional, Dict, Any
from uuid import uuid4
from pydantic import BaseModel, Field, Extra

class CustomerDeviceData(BaseModel):
    device_id: str = Field(default_factory=lambda: str(uuid4()))
    device_name: str
    device_model: str
    app_label: Optional[str] = None          #  ← "customerApp1", "customerApp2", …
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        extra = Extra.allow                  # keep screen_w, screen_h, etc.

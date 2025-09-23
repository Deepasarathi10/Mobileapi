from pydantic import BaseModel, Field
from typing import Any, Optional
from datetime import date, time

class Stickercount(BaseModel):
    stickercountId: Optional[str] = None
    itemCode: Optional[str] = None
    itemName: Optional[str] = None
    date: Optional[Any] = None  # Use `date` directly from datetime module
    Time: Optional[str] = None  # Use `time` directly from datetime module
    Count: Optional[int] = None


class StickercountPost(BaseModel):
    itemCode: Optional[str] = None
    itemName: Optional[str] = None
    date: Optional[str] = None  # Use `date` directly from datetime module
    Time: Optional[str] = None  # Use `time` directly from datetime module
    Count: Optional[int] = None

from datetime import datetime
from pydantic import BaseModel, Field
from typing import Any, List, Optional
import pytz
from fastapi import HTTPException

# Helper function to get the formatted ISO datetime
def get_iso_datetime(timezone: str = "Asia/Kolkata") -> str:
    try:
        # Set the specified timezone
        specified_timezone = pytz.timezone(timezone)
    except pytz.UnknownTimeZoneError:
        raise HTTPException(status_code=400, detail="Invalid timezone")

    # Get the current time in the specified timezone
    current_time = datetime.now(specified_timezone)

    # Format the date and time in ISO 8601 format
    iso_datetime = current_time.isoformat()
    return iso_datetime

# Models
class Stockclossing(BaseModel):
    stockclosingId: Optional[str] = None
    itemName: Optional[List[str]] = None  # Accepts a list of item names
    date: Optional[datetime] = None  # ISO 8601 formatted datetime
    branch: Optional[str] = None
    closingQty: Optional[List[Any]] = None  # Accepts a list of quantities
    requireQty: Optional[List[Any]] = None  # Accepts a list of quantities
    postedBy: Optional[str] = None

class StockclossingPost(BaseModel):
    itemName: Optional[List[str]] = None  # Accepts a list of item names
    date: Optional[str] = Field(default_factory=lambda: get_iso_datetime())
    branch: Optional[str] = None
    closingQty: Optional[List[Any]] = None  # Accepts a list of quantities
    requireQty: Optional[List[Any]] = None  # Accepts a list of quantities
    postedBy: Optional[str] = None
    
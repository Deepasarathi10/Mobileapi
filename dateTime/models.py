from enum import Enum
from pydantic import BaseModel
from typing import Optional

class DateFormat(str, Enum):
    DDMMYYYY = "DD/MM/YYYY"
    MMYYYYDD = "MM/YYYY/DD"
    YYYYMMDD = "YYYY/MM/DD"

class TimeFormat(str, Enum):
    HOUR_12 = "12-hour"
    HOUR_24 = "24-hour"

DATE_FORMAT_PATTERNS = {
    DateFormat.DDMMYYYY: "%d/%m/%Y",
    DateFormat.MMYYYYDD: "%m/%Y/%d",
    DateFormat.YYYYMMDD: "%Y/%m/%d"
}

TIME_FORMAT_PATTERNS = {
    TimeFormat.HOUR_12: "%I:%M:%S %p",
    TimeFormat.HOUR_24: "%H:%M:%S %p"
}

class DateTimeSettings(BaseModel):
    date_format: DateFormat = DateFormat.DDMMYYYY
    time_format: TimeFormat = TimeFormat.HOUR_24
    timezone: str = "UTC"  # Default timezone is UTC

class UpdateSettingsRequest(BaseModel):
    date_format: Optional[DateFormat] = None
    time_format: Optional[TimeFormat] = None
    timezone: Optional[str] = None

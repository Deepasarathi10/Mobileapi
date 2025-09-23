from fastapi import APIRouter
from datetime import datetime
from zoneinfo import ZoneInfo
from pymongo import MongoClient
from dateTime.models import (
    DateFormat, TimeFormat, DateTimeSettings,
    UpdateSettingsRequest, DATE_FORMAT_PATTERNS, TIME_FORMAT_PATTERNS
)
from .utils import collection
router = APIRouter()

# Set your default timezone here
DEFAULT_TIMEZONE = "Asia/Kolkata"  # Change this to your local timezone

def format_current_datetime(settings: DateTimeSettings, force_utc: bool = False) -> dict:
    # Always get current time in UTC first
    now_utc = datetime.now(ZoneInfo("UTC"))
    
    if force_utc:
        # If forcing UTC, use UTC timezone
        now_tz = now_utc
        tz_display = "UTC"
    else:
        # Convert to requested timezone
        tz = ZoneInfo(settings.timezone)
        now_tz = now_utc.astimezone(tz)
        tz_display = settings.timezone

    date_str = now_tz.strftime(DATE_FORMAT_PATTERNS[settings.date_format])
    time_str = now_tz.strftime(TIME_FORMAT_PATTERNS[settings.time_format])

    return {
        "formatted_date": date_str,
        "formatted_time": time_str,
        "timezone": tz_display,
        "datetime_object": now_tz.isoformat()
    }

def get_current_settings_from_db() -> DateTimeSettings:
    doc = collection.find_one({})   
    if doc:
        return DateTimeSettings(
            date_format=DateFormat(doc.get("date_format", DateFormat.DDMMYYYY)),
            time_format=TimeFormat(doc.get("time_format", TimeFormat.HOUR_24)),
            timezone=doc.get("timezone", DEFAULT_TIMEZONE)  # Use default timezone if not set
        )
    # Create new settings with default timezone
    default_settings = DateTimeSettings(timezone=DEFAULT_TIMEZONE)
    collection.insert_one(default_settings.dict())
    return default_settings

def save_settings_to_db(settings: DateTimeSettings):
    collection.update_one({}, {"$set": settings.dict()}, upsert=True)

@router.get("/current_datetime")
def get_current_datetime(force_utc: bool = False):
    settings = get_current_settings_from_db()
    return format_current_datetime(settings, force_utc=force_utc)

@router.get("/settings", response_model=DateTimeSettings)
def get_settings():
    return get_current_settings_from_db()

@router.patch("/settings", response_model=DateTimeSettings)
def update_settings(request: UpdateSettingsRequest):
    settings = get_current_settings_from_db()
    if request.date_format:
        settings.date_format = request.date_format
    if request.time_format:
        settings.time_format = request.time_format
    if request.timezone:
        settings.timezone = request.timezone
    save_settings_to_db(settings)
    return settings

@router.get("/available_formats")
def get_available_formats():
    return {
        "date_formats": [fmt.value for fmt in DateFormat],
        "time_formats": [fmt.value for fmt in TimeFormat],
        "timezones": ["UTC", "Asia/Kolkata", "America/New_York", "Europe/London"]
    }
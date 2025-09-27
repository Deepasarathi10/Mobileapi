from datetime import datetime
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Any, Optional, List
import pytz

app = FastAPI()

def get_iso_datetime(date_str: str) -> Optional[datetime]:
    """
    Parse a date string (DD-MM-YYYY or YYYY-MM-DD) into a timezone-aware datetime (UTC).
    Returns None if parsing fails.
    """
    for fmt in ("%d-%m-%Y", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.replace(tzinfo=pytz.UTC)
        except ValueError:
            continue
    return None

# Models
class Productionsummary(BaseModel):
    varianceName: Optional[List[str]] = None
    uom: Optional[List[str]] = None
    itemName: Optional[List[str]] = None
    uom: Optional[List[str]] = None
    price: Optional[List[float]] = None
    totalqty: Optional[List[int]] = None
    amount: Optional[List[float]] = None   
    weight: Optional[List[float]] = None
    date: Optional[datetime] = None  # ISO 8601 formatted datetime
    category: Optional[List[str]] = None
    subcategory: Optional[List[str]] = None
    totalAmount: Optional[float] = None



class ProductionsummaryPost(BaseModel):
    varianceName: Optional[List[str]] = None
    uom: Optional[List[str]] = None
    itemName: Optional[List[str]] = None
    qty: Optional[List[int]] = None
    uom: Optional[List[str]] = None
    price: Optional[List[float]] = None    
    amount: Optional[List[float]] = None   
    weight: Optional[List[float]] = None
    date: Optional[datetime] = None  # ISO 8601 formatted datetime
    category: Optional[List[str]] = None
    subcategory: Optional[List[str]] = None
    totalAmount: Optional[float] = None
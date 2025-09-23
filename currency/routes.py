from typing import Collection, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pymongo import MongoClient
from pydantic import BaseModel
# from Currency import currencies
from .utils import get_currency_collection
from .models import CurrencyPreference

router = APIRouter()

# Endpoint to get all countries (no changes needed here)
@router.get("/countries", response_model=List[dict])
async def get_countries():
    db: Collection = get_currency_collection()
    cursor = db.find()

    countries = []
    for doc in cursor:
        doc.pop("_id", None)  # remove MongoDB internal ID
        countries.append(doc)

    return countries
# Endpoint to save currency preference
@router.patch("/save-preference")
async def save_currency_preference(preference: CurrencyPreference):
    db = get_currency_collection()
    
    # You can use a static ID for the document
    db.update_one(
        {"_id": "user_currency_preference"},
        {"$set": {
            "countryName": preference.countryName,
            "symbol": preference.symbol
        }},
        upsert=True
    )
    
    return {
        "message": "Currency preference saved",
        "data": preference
    }

# Endpoint to get saved preference
@router.get("/get-preference", response_model=dict)
async def get_currency_preference():
    db = get_currency_collection()
    preference = db.find_one({"_id": "user_currency_preference"})

    if preference:
        preference.pop("_id", None)
        return preference
    
    raise HTTPException(status_code=404, detail="No saved currency preference found.")


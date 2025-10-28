import json
import urllib
from fastapi import APIRouter, Request
from datetime import datetime
from pymongo import ReturnDocument
from .utils import get_cakeId_collection
import requests
from requests.auth import HTTPBasicAuth
import razorpay

router = APIRouter()

@router.get("/cakeId")
async def get_cakeId():
    coll = get_cakeId_collection()
    # get today’s date in DD-MM-YYYY form
    today_dt = datetime.now()
    date_str = today_dt.strftime("%d-%m-%Y")
    
    # Filter for today’s document
    filter_query = {"date": date_str}
    
    # Update: increment cakeId by 1 if exists, else insert a new document with cakeId = 1
    update_doc = {
        "$inc": {"cakeId": 1},
        "$setOnInsert": {"date": date_str}
    }
    
    # Note: upsert = True so that if no document exists for today, one will be created
    updated = await coll.find_one_and_update(
        filter_query,
        update_doc,
        upsert=True,
        return_document=ReturnDocument.AFTER
    )
    
    # Now updated is the document after update/insert. It has cakeId and date
    # If inserted new, cakeId will be 1 (because inc on non-existent field starts from 0 in MongoDB + inc → 1)
    
    cake_id = updated.get("cakeId")
    # Format return string like "19092025-<cakeId>"
    out = today_dt.strftime("%d%m%Y") + f"{cake_id}"
    return out




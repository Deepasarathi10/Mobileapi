from typing import List
from fastapi import APIRouter, HTTPException,status
from bson import ObjectId
from .models import DayEnd,DayEndPost
from .utils import get_dayEnd_collection
from datetime import datetime
from fastapi import Body
from shift.utils import get_shift_collection
from HeldOrders.utils import get_holdOrder_collection
from SalesOrder.utils import get_salesOrder_collection 
from dispatch.utils import get_dispatch_collection
from itemTransfer.utils import get_itemtransfer_collection 
   
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from fastapi import HTTPException, Body
from typing import List# 👈 assuming you already have this

router = APIRouter()

@router.post("/", response_model=str)
async def create_dayEnd(day: DayEndPost):
    new_day = day.model_dump(exclude_unset=True)  
    result =  await get_dayEnd_collection().insert_one(new_day)  # Notice the parentheses here
    return str(result.inserted_id)


IST = ZoneInfo("Asia/Kolkata")

async def to_local(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(IST)

async def parse_dt(val):
    if isinstance(val, datetime):
        return val
    if isinstance(val, str):
        s = val.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(s)
        except ValueError:
            return None
    return None

async def first_opening_dt(shift_doc):
    for key in ("OpeningDateTime", "openingDateTime", "shiftStartTime"):
        dt = await parse_dt(shift_doc.get(key))
        if dt:
            return dt
    return None

def to_dec(x) -> Decimal:
    if x in (None, ""):
        return Decimal("0")
    try:
        return Decimal(str(x))
    except InvalidOperation:
        return Decimal("0")

async def get_difference_type(difference: Decimal) -> str:
    if difference < 0:
        return "shortage"
    elif difference > 0:
        return "excess"
    return "no difference"

# @router.post("/dayend", response_model=str)
# async def create_dayend(dayend_data: DayEnd = Body(...)):
#     shift_collection = get_shift_collection()
#     if not dayend_data.branchName:
#         raise HTTPException(status_code=400, detail="branchName is required")
    
#     open_shifts = await shift_collection.find(
#         {"branchName": dayend_data.branchName, "dayEndStatus": "open"}
#     ).sort("OpeningDateTime", 1).to_list(length=None)
    
#     if not open_shifts:
#         raise HTTPException(status_code=404, detail="No open shifts found")
    
#     first_dt = None
#     for shift in open_shifts:
#         dt = await first_opening_dt(shift)
#         if dt:
#             first_dt = dt
#             break
#     if not first_dt:
#         raise HTTPException(status_code=400, detail="Invalid OpeningDateTime")
    
#     local_open = await to_local(first_dt)
#     dayOpeningDate = local_open.date().isoformat()
#     dayOpeningTime = local_open.time().isoformat(timespec="seconds")
    
#     now_utc = datetime.now(timezone.utc)
#     local_close = await to_local(now_utc)
#     dayClosingDate = local_close.date().isoformat()
#     dayClosingTime = local_close.time().isoformat(timespec="seconds")
    
#     # Summation
#     systemCash = sum( to_dec(s.get("systemCashSales")) for s in open_shifts)
#     systemCard = sum( to_dec(s.get("systemCardSales")) for s in open_shifts)
#     systemUpi  = sum( to_dec(s.get("systemUpiSales"))  for s in open_shifts)
    
#     manualCash = sum( to_dec(s.get("manualCashsales")) for s in open_shifts)
#     manualCard = sum( to_dec(s.get("manualCardsales")) for s in open_shifts)
#     manualUpi  = sum( to_dec(s.get("manualUpisales"))  for s in open_shifts)

#     cashDifference = manualCash - systemCash
#     cardDifference = manualCard - systemCard
#     upiDifference  = manualUpi  - systemUpi
    
#     totalSystem = systemCash + systemCard + systemUpi
#     totalManual = manualCash + manualCard + manualUpi
#     totalDifference = totalManual - totalSystem
    
#     new_dayend = dayend_data.model_dump(exclude_unset=True)
#     new_dayend.update({
#         "dayOpeningDate": dayOpeningDate,
#         "dayOpeningTime": dayOpeningTime,
#         "dayClosingDate": dayClosingDate,
#         "dayClosingTime": dayClosingTime,
#         "systemCashSales": str(systemCash),
#         "systemCardSales": str(systemCard),
#         "systemUpiSales":  str(systemUpi),
#         "manualCashSales": str(manualCash),
#         "manualCardSales": str(manualCard),
#         "manualUpiSales":  str(manualUpi),
#         "cashDifferenceAmount": str(cashDifference),
#         "cashDifferenceType": await get_difference_type(cashDifference),
#         "cardDifferenceAmount": str(cardDifference),
#         "cardDifferenceType": await get_difference_type(cardDifference),
#         "upiDifferenceAmount": str(upiDifference),
#         "upiDifferenceType": await get_difference_type(upiDifference),
#         "totalSystemSales": str(totalSystem),
#         "totalManualSales": str(totalManual),
#         "totalDifferenceAmount": str(totalDifference),
#         "totalDifferenceType": await get_difference_type(totalDifference),
#         "status": "closed",
#     })
    
#     dayend_collection = get_dayEnd_collection()
#     result = await dayend_collection.insert_one(new_dayend)
#     await dayend_collection.update_one(
#         {"_id": result.inserted_id}, {"$set": {"dayEndId": str(result.inserted_id)}}
#     )
#     return str(result.inserted_id)

@router.post("/dayend", response_model=str)
async def create_dayend(dayend_data: DayEnd = Body(...)):
    shift_collection = get_shift_collection()
    if not dayend_data.branchName:
        raise HTTPException(status_code=400, detail="branchName is required")
    
    open_shifts = await shift_collection.find(
        {"branchName": dayend_data.branchName, "dayEndStatus": "open"}
    ).sort("OpeningDateTime", 1).to_list(length=None)
    
    if not open_shifts:
        raise HTTPException(status_code=404, detail="No open shifts found")
    
    # --- Opening and Closing DateTimes ---
    first_dt = None
    for shift in open_shifts:
        dt = await first_opening_dt(shift)
        if dt:
            first_dt = dt
            break
    if not first_dt:
        raise HTTPException(status_code=400, detail="Invalid OpeningDateTime")
    
    local_open = await to_local(first_dt)
    dayOpeningDate = local_open.date().isoformat()
    dayOpeningTime = local_open.time().isoformat(timespec="seconds")
    
    now_utc = datetime.now(timezone.utc)
    local_close = await to_local(now_utc)
    dayClosingDate = local_close.date().isoformat()
    dayClosingTime = local_close.time().isoformat(timespec="seconds")

    # --- Summations across open shifts ---
    systemCash = sum(to_dec(s.get("systemCashSales")) for s in open_shifts)
    systemCard = sum(to_dec(s.get("systemCardSales")) for s in open_shifts)
    systemUpi  = sum(to_dec(s.get("systemUpiSales"))  for s in open_shifts)
    
    manualCash = sum(to_dec(s.get("manualCashsales")) for s in open_shifts)
    manualCard = sum(to_dec(s.get("manualCardsales")) for s in open_shifts)
    manualUpi  = sum(to_dec(s.get("manualUpisales"))  for s in open_shifts)

    # --- New per-type sales aggregation ---
    kotCash = sum(to_dec(s.get("kotCashSales")) for s in open_shifts)
    kotCard = sum(to_dec(s.get("kotCardSales")) for s in open_shifts)
    kotUpi  = sum(to_dec(s.get("kotUpiSales"))  for s in open_shifts)

    takeCash = sum(to_dec(s.get("takeAwayCashSales")) for s in open_shifts)
    takeCard = sum(to_dec(s.get("takeAwayCardSales")) for s in open_shifts)
    takeUpi  = sum(to_dec(s.get("takeAwayUpiSales"))  for s in open_shifts)

    soCash = sum(to_dec(s.get("saleOrderCashSales")) for s in open_shifts)
    soCard = sum(to_dec(s.get("saleOrderCardSales")) for s in open_shifts)
    soUpi  = sum(to_dec(s.get("saleOrderUpiSales"))  for s in open_shifts)

    bdCash = sum(to_dec(s.get("bdCakeCashSales")) for s in open_shifts)
    bdCard = sum(to_dec(s.get("bdCakeCardSales")) for s in open_shifts)
    bdUpi  = sum(to_dec(s.get("bdCakeUpiSales"))  for s in open_shifts)

    # --- Differences ---
    cashDifference = manualCash - systemCash
    cardDifference = manualCard - systemCard
    upiDifference  = manualUpi  - systemUpi
    
    totalSystem = systemCash + systemCard + systemUpi
    totalManual = manualCash + manualCard + manualUpi
    totalDifference = totalManual - totalSystem
    
    # --- Totals by type ---
    totalKotSales       = kotCash + kotCard + kotUpi
    totalTakeAwaySales  = takeCash + takeCard + takeUpi
    totalSaleOrderSales = soCash + soCard + soUpi
    totalBdCakeSales    = bdCash + bdCard + bdUpi
    
    # --- Final DayEnd document ---
    new_dayend = dayend_data.model_dump(exclude_unset=True)
    new_dayend.update({
        "dayOpeningDate": dayOpeningDate,
        "dayOpeningTime": dayOpeningTime,
        "dayClosingDate": dayClosingDate,
        "dayClosingTime": dayClosingTime,
        
        "systemCashSales": str(systemCash),
        "systemCardSales": str(systemCard),
        "systemUpiSales":  str(systemUpi),

        "manualCashSales": str(manualCash),
        "manualCardSales": str(manualCard),
        "manualUpiSales":  str(manualUpi),

        "kotCashSales": str(kotCash),
        "kotCardSales": str(kotCard),
        "kotUpiSales":  str(kotUpi),

        "takeAwayCashSales": str(takeCash),
        "takeAwayCardSales": str(takeCard),
        "takeAwayUpiSales":  str(takeUpi),

        "saleOrderCashSales": str(soCash),
        "saleOrderCardSales": str(soCard),
        "saleOrderUpiSales":  str(soUpi),

        "bdCakeCashSales": str(bdCash),
        "bdCakeCardSales": str(bdCard),
        "bdCakeUpiSales":  str(bdUpi),

        "totalKotSales": str(totalKotSales),
        "totalTakeAwaySales": str(totalTakeAwaySales),
        "totalSaleOrderSales": str(totalSaleOrderSales),
        "totalBdCakeSales": str(totalBdCakeSales),

        "cashDifferenceAmount": str(cashDifference),
        "cashDifferenceType": await get_difference_type(cashDifference),
        "cardDifferenceAmount": str(cardDifference),
        "cardDifferenceType": await get_difference_type(cardDifference),
        "upiDifferenceAmount": str(upiDifference),
        "upiDifferenceType": await get_difference_type(upiDifference),

        "totalSystemSales": str(totalSystem),
        "totalManualSales": str(totalManual),
        "totalDifferenceAmount": str(totalDifference),
        "totalDifferenceType": await get_difference_type(totalDifference),
        "status": "closed",
    })
    
    dayend_collection = get_dayEnd_collection()
    result = await dayend_collection.insert_one(new_dayend)
    await dayend_collection.update_one(
        {"_id": result.inserted_id}, {"$set": {"dayEndId": str(result.inserted_id)}}
    )
    return str(result.inserted_id)


async def convert_to_string_or_emptys(data):
    if isinstance(data, list):
        return [str(value) if value is not None and value != "" else None for value in data]
    elif isinstance(data, (int, float)):
        return str(data)
    else:
        return str(data) if data is not None and data != "" else None
    

@router.get("/", response_model=List[DayEndPost])
async def get_all_dayEnd():
    dayEnd_collection = get_dayEnd_collection()

    # ✅ fetch all dayend docs properly
    dayend_docs = await dayEnd_collection.find().to_list(length=None)

    if not dayend_docs:
        return []

    formatted_dayEnd = []
    for day in dayend_docs:
        dayEnd_data = {key: await convert_to_string_or_emptys(value) for key, value in day.items()}
        dayEnd_data["dayEndId"] = str(dayEnd_data.pop("_id"))
        formatted_dayEnd.append(DayEndPost(**dayEnd_data))

    return formatted_dayEnd


@router.get("/{dayEnd_id}", response_model=DayEnd)
async def get_dayEnd_by_id(dayEnd_id: str):
    shift_collection = get_shift_collection()
    dayEnd = await shift_collection.find_one({"_id": ObjectId(dayEnd_id)})
    if dayEnd:
        
        dayEnd_data = {key: convert_to_string_or_emptys(value) for key, value in dayEnd.items()}
        dayEnd_data["_id"] = str(dayEnd["_id"])
        return DayEnd(**dayEnd_data)
    else:
        raise HTTPException(status_code=404, detail="DayEnd not found")


@router.patch("/{dayEnd_id}")
async def patch_shift(dayEnd_id: str, dayEnd_update: DayEndPost):
    existing_dayEnd =  get_dayEnd_collection.find_one({"_id": ObjectId(dayEnd_id)})
    if existing_dayEnd:
        updated_fields = dayEnd_update.model_dump(exclude_unset=True)
      
        result = get_dayEnd_collection().update_one(
            {"_id": ObjectId(dayEnd_id)},
            {"$set": updated_fields}
        )
        if result.modified_count == 0:
            raise HTTPException(status_code=400, detail="Failed to update DayEnd.")
        return {"message": "DayEnd updated successfully"}
    else:
        raise HTTPException(status_code=404, detail="DayEnd not found")

@router.delete("/{dayEnd_id}")
async def delete_dayEnd(dayEnd_id: str):
    result =  get_dayEnd_collection().delete_one({"_id": ObjectId(dayEnd_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="DayEnd not found")
    return {"message": "DayEnd deleted successfully"}

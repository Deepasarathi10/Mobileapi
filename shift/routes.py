import datetime
from typing import Dict, List, Optional,Any
from fastapi import APIRouter, HTTPException, Query, status
from bson import ObjectId
from .models import Shift, ShiftPost, get_iso_datetime
from .utils import get_shift_collection
from Invoice.utils import get_invoice_collection
from SalesOrder.utils import get_salesOrder_collection
from datetime import datetime

router = APIRouter()

# ---------------- CREATE ----------------
@router.post("/", response_model=str)
async def create_shift(shift: ShiftPost):
    shift_collection = get_shift_collection()

    iso_now = await get_iso_datetime()  # Current ISO datetime string (Asia/Kolkata)
    current_date_str = iso_now.split("T")[0]  # YYYY-MM-DD

    # Find last shift today
    last_shift = await shift_collection.find_one(
        {"OpeningDateTime": {"$regex": f"^{current_date_str}"}},
        sort=[("shiftNumber", -1)]
    )

    next_shift_number = 1
    if last_shift and last_shift.get("shiftNumber") is not None:
        try:
            next_shift_number = int(last_shift["shiftNumber"]) + 1
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid shiftNumber format in DB")

    new_shift = shift.model_dump(exclude_unset=True)
    new_shift["shiftNumber"] = next_shift_number
    new_shift["OpeningDateTime"] = iso_now

    result =  await shift_collection.insert_one(new_shift)
    return str(result.inserted_id)

# ---------------- CHECK OPEN SHIFT ----------------
@router.get("/check-open-shift", response_model=dict)
async def check_open_shift(branch_name: str):
    if not branch_name:
        raise HTTPException(status_code=400, detail="branch_name is required")

    iso_now = await get_iso_datetime()
    current_date_str = iso_now.split("T")[0]
    shift_collection = get_shift_collection()

    query = {
        "branchName": branch_name,
        "dayEndStatus": "open",
        "status": "open",
        "OpeningDateTime": {"$regex": f"^{current_date_str}"}
    }

    open_shift = await shift_collection.find_one(query, sort=[("OpeningDateTime", -1)])

    if open_shift:
        return {
            "shiftId": str(open_shift["_id"]),
            "shiftNumber": int(open_shift.get("shiftNumber", 0)),
        }
    else:
        return {"shiftId": "0", "shiftNumber": 0}  

# ---------------- UTILS ----------------
async def convert_to_string_or_emptys(data):
    if isinstance(data, list):
        return [str(value) if value is not None and value != "" else None for value in data]
    elif isinstance(data, (int, float)):
        return str(data)
    else:
        return str(data) if data is not None and data != "" else None

async def parse_id(shift_id: str):
    try:
        return ObjectId(shift_id)
    except Exception:
        return shift_id

# ---------------- READ ----------------
@router.get("/all", response_model=List[Shift])
async def get_all_shifts(branchName: Optional[str] = Query(default=None, alias="branchName")):
    shift_collection = get_shift_collection()

    filter_query = {}
    if branchName:
        filter_query["branchName"] = branchName

    # fetch with filter
    shifts = await shift_collection.find(filter_query).to_list(length=None)

    formatted_shifts = []
    for shift in shifts:
        shift_data = {}
        for key, value in shift.items():
            converted = await convert_to_string_or_emptys(value)
            shift_data[key] = converted

        # rename _id
        shift_data["shiftId"] = str(shift_data.pop("_id"))
        formatted_shifts.append(Shift(**shift_data))

    return formatted_shifts


@router.get("/{shift_id}", response_model=Shift)
async def get_shift_by_id(shift_id: str):
    shift_collection = get_shift_collection()
    
    # Correct: await parse_id
    parsed_id = await parse_id(shift_id)
    
    shift = await shift_collection.find_one({"_id": parsed_id})
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    
    shift_data = {
        key: await convert_to_string_or_emptys(value)
        for key, value in shift.items()
    }
    shift_data["shiftId"] = str(shift["_id"])
    return Shift(**shift_data)


# ---------------- UPDATE ----------------
@router.patch("/{shift_id}")
async def patch_shift(shift_id: str, shift_update: ShiftPost):
    shift_collection = get_shift_collection()  # Correctly awaiting coroutine

    parsed_id = await parse_id(shift_id)  # Also ensure you await async helpers

    existing_shift = await shift_collection.find_one({"_id": parsed_id})
    if not existing_shift:
        raise HTTPException(status_code=404, detail="Shift not found")

    updated_fields = shift_update.model_dump(exclude_unset=True)

    result = await shift_collection.update_one(
        {"_id": parsed_id},
        {"$set": updated_fields}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=400, detail="Failed to update shift.")

    return {"message": "Shift updated successfully"}


async def get_diff_type(amount: float) -> str:
    if amount == 0:
        return "no difference"
    return "excess" if amount > 0 else "shortage"

# async def calculate_sales(
#     branch_name: str,
#     shift_id: str,
#     manualCashsales: float = 0.0,
#     manualCardsales: float = 0.0,
#     manualUpisales: float = 0.0
# ):
#     salesorder_col =  get_salesOrder_collection()
#     invoice_col =  get_invoice_collection()

#     try:
#         shift_obj_id = ObjectId(shift_id)
#     except Exception:
#         shift_obj_id = None

#     sales_filter = {
#         "branchName": branch_name,
#         "shiftId": shift_id
#     }

#     invoice_filter = {
#         "branchName": branch_name,
#         "$or": [
#             {"shiftId": shift_id},
#             {"shiftId": shift_obj_id} if shift_obj_id else {}
#         ]
#     }

#     salesorders = list(salesorder_col.find(sales_filter))
#     invoices = list(invoice_col.find(invoice_filter))

#     # System calculated sales
#     systemCashSales = systemCardSales = systemUpiSales = systemOtherSales = 0.0

#     for sale in salesorders + invoices:
#         payment_mode = str(sale.get("paymentType", "")).strip().lower()

#         if not payment_mode:
#             if sale.get("cash"):
#                 payment_mode = "cash"
#             elif sale.get("card"):
#                 payment_mode = "card"
#             elif sale.get("upi"):
#                 payment_mode = "upi"
#             else:
#                 payment_mode = "other"

#         try:
#             total_amount = float(sale.get("totalAmount") or 0)
#         except (ValueError, TypeError):
#             total_amount = 0.0

#         if payment_mode == "cash":
#             systemCashSales += total_amount
#         elif payment_mode == "card":
#             systemCardSales += total_amount
#         elif payment_mode == "upi":
#             systemUpiSales += total_amount
#         else:
#             systemOtherSales += total_amount

#     # ✅ Difference Calculations
#     cashSaleDifferenceAmount = float(manualCashsales or 0) - systemCashSales
#     cardSaleDifferenceAmount = float(manualCardsales or 0) - systemCardSales
#     upiSaleDifferenceAmount = float(manualUpisales or 0) - systemUpiSales

#     cashSaleDifferenceType = await get_diff_type(cashSaleDifferenceAmount)
#     cardSaleDifferenceType = await get_diff_type(cardSaleDifferenceAmount)
#     upiSaleDifferenceType = await get_diff_type(upiSaleDifferenceAmount)

#     # ✅ Totals
#     totalSystemSales = systemCashSales + systemCardSales + systemUpiSales + systemOtherSales
#     totalManualSales = float(manualCashsales or 0) + float(manualCardsales or 0) + float(manualUpisales or 0)

#     totalDifferenceAmount = totalManualSales - totalSystemSales
#     totalDifferenceType = await get_diff_type(totalDifferenceAmount)

#     result = {
#         # System values
#         "systemCashSales": systemCashSales,
#         "systemCardSales": systemCardSales,
#         "systemUpiSales": systemUpiSales,
#         "systemOtherSales": systemOtherSales,
#         "totalSystemSales": totalSystemSales,

#         # Manual values
#         "manualCashsales": manualCashsales,
#         "manualCardsales": manualCardsales,
#         "manualUpisales": manualUpisales,
#         "totalManualSales": totalManualSales,

#         # Differences (per mode)
#         "cashSaleDifferenceAmount": cashSaleDifferenceAmount,
#         "cashSaleDifferenceType": cashSaleDifferenceType,

#         "cardSaleDifferenceAmount": cardSaleDifferenceAmount,
#         "cardSaleDifferenceType": cardSaleDifferenceType,

#         "upiSaleDifferenceAmount": upiSaleDifferenceAmount,
#         "upiSaleDifferenceType": upiSaleDifferenceType,

#         # ✅ Total difference
#         "totalDifferenceAmount": totalDifferenceAmount,
#         "totalDifferenceType": totalDifferenceType,
#     }

#     print("✅ Calculated sales result with differences:", result)
#     return result
async def safe_float(value, default=0.0):
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


async def calculate_sales(
    branch_name: str,
    shift_id: str,
    manualCashsales: float = 0.0,
    manualCardsales: float = 0.0,
    manualUpisales: float = 0.0
):
    salesorder_col = get_salesOrder_collection()
    invoice_col = get_invoice_collection()

    try:
        shift_obj_id = ObjectId(shift_id)
    except Exception:
        shift_obj_id = None

    sales_filter = {
        "shiftId": shift_id
    }
    invoice_filter = {
        "$or": [
            {"shiftId": shift_id},
            {"shiftId": shift_obj_id} if shift_obj_id else {}
        ]
    }

    salesorders = await invoice_col.find(sales_filter).to_list(None)  # regular invoices
    saleorders = await salesorder_col.find({}).to_list(None)  # all sale orders
    invoices = await invoice_col.find(invoice_filter).to_list(None)  # invoices again?

    # Totals across all types
    systemCashSales = 0.0
    systemCardSales = 0.0
    systemUpiSales = 0.0
    systemOtherSales = 0.0

    # Per-type breakdown dictionaries
    kot_cash = kot_card = kot_upi = 0.0
    take_cash = take_card = take_upi = 0.0
    so_cash = so_card = so_upi = 0.0
    bd_cash = bd_card = bd_upi = 0.0
    other_cash = other_card = other_upi = 0.0

    # Process invoices + regular sales
    all_sales = invoices
    for sale in all_sales:
        payment_modes = sale.get("paymentType", [])

        if not isinstance(payment_modes, list):
            payment_modes = [str(payment_modes)]
        payment_modes = [p.lower().strip() for p in payment_modes if p]

        if not payment_modes:
            if sale.get("cash"):
                payment_modes = ["cash"]
            elif sale.get("card"):
                payment_modes = ["card"]
            elif sale.get("upi"):
                payment_modes = ["upi"]
            else:
                payment_modes = ["other"]

        amt_cash = float(sale.get("cash") or 0)
        amt_card = float(sale.get("card") or 0)
        amt_upi = float(sale.get("upi") or 0)
        amt_other = float(sale.get("others") or 0)
        total_amount = float(sale.get("totalAmount") or 0)

        if "cash" in payment_modes:
            systemCashSales += amt_cash
        if "card" in payment_modes:
            systemCardSales += amt_card
        if "upi" in payment_modes:
            systemUpiSales += amt_upi
        if "other" in payment_modes:
            systemOtherSales += amt_other if amt_other else total_amount - (amt_cash + amt_card + amt_upi)

        stype = str(sale.get("salesType", "") or "").strip().lower()
        if stype in ["dinning", "dining", "kot"]:
            if "cash" in payment_modes:
                kot_cash += amt_cash
            if "card" in payment_modes:
                kot_card += amt_card
            if "upi" in payment_modes:
                kot_upi += amt_upi
        elif stype in ["takeaway", "take away"]:
            if "cash" in payment_modes:
                take_cash += amt_cash
            if "card" in payment_modes:
                take_card += amt_card
            if "upi" in payment_modes:
                take_upi += amt_upi
        elif stype in ["birthdaycake", "bdcake"]:
            if "cash" in payment_modes:
                bd_cash += amt_cash
            if "card" in payment_modes:
                bd_card += amt_card
            if "upi" in payment_modes:
                bd_upi += amt_upi
        elif stype in ["saleorder", "salesorder","salesorders","saleorders"]:
            if "cash" in payment_modes:
                so_cash += amt_cash
            if "card" in payment_modes:
                so_card += amt_card
            if "upi" in payment_modes:
                so_upi += amt_upi
        else:
            if "cash" in payment_modes:
                other_cash += amt_cash
            if "card" in payment_modes:
                other_card += amt_card
            if "upi" in payment_modes:
                other_upi += amt_upi

    # ------------------ Process Sale Orders for advance payments ------------------
    for so in saleorders:
        shift_ids = so.get("shiftId", [])
        if shift_id not in shift_ids and str(shift_obj_id) not in shift_ids:
            continue  # skip non-matching shiftIds

        advance_types_list = so.get("advancePaymentType", [])  # e.g., [["cash","upi"], ["card"]]
        mode_amount_list = so.get("modeWiseAmount", [])  # e.g., [[50,50],[100]]
        
        if not advance_types_list or not mode_amount_list:
            continue

        for types, amounts in zip(advance_types_list, mode_amount_list):
            for t, amt in zip(types, amounts):
                t = t.lower().strip()
                if t == "cash":
                    so_cash += float(amt)
                    systemCashSales += float(amt)
                elif t == "card":
                    so_card += float(amt)
                    systemCardSales += float(amt)
                elif t == "upi":
                    so_upi += float(amt)
                    systemUpiSales += float(amt)
                else:
                    systemOtherSales += float(amt)

    # Differences
    cashDiff = float(manualCashsales or 0) - systemCashSales
    cardDiff = float(manualCardsales or 0) - systemCardSales
    upiDiff = float(manualUpisales or 0) - systemUpiSales

    cashDiffType = await get_diff_type(cashDiff)
    cardDiffType = await get_diff_type(cardDiff)
    upiDiffType = await get_diff_type(upiDiff)

    totalSystemSales = systemCashSales + systemCardSales + systemUpiSales + systemOtherSales
    totalManualSales = float(manualCashsales or 0) + float(manualCardsales or 0) + float(manualUpisales or 0)
    totalDiff = totalManualSales - totalSystemSales
    totalDiffType = await get_diff_type(totalDiff)

    totalKotSales = kot_cash + kot_card + kot_upi
    totalTakeAwaySales = take_cash + take_card + take_upi
    totalSaleOrderSales = so_cash + so_card + so_upi
    totalBdCakeSales = bd_cash + bd_card + bd_upi

    return {
        "systemCashSales": systemCashSales,
        "systemCardSales": systemCardSales,
        "systemUpiSales": systemUpiSales,
        "systemOtherSales": systemOtherSales,
        "totalSystemSales": totalSystemSales,
        "manualCashsales": manualCashsales,
        "manualCardsales": manualCardsales,
        "manualUpisales": manualUpisales,
        "totalManualSales": totalManualSales,
        "cashSaleDifferenceAmount": cashDiff,
        "cashSaleDifferenceType": cashDiffType,
        "cardSaleDifferenceAmount": cardDiff,
        "cardSaleDifferenceType": cardDiffType,
        "upiSaleDifferenceAmount": upiDiff,
        "upiSaleDifferenceType": upiDiffType,
        "totalDifferenceAmount": totalDiff,
        "totalDifferenceType": totalDiffType,
        "kotCashSales": kot_cash,
        "kotCardSales": kot_card,
        "kotUpiSales": kot_upi,
        "takeAwayCashSales": take_cash,
        "takeAwayCardSales": take_card,
        "takeAwayUpiSales": take_upi,
        "saleOrderCashSales": so_cash,
        "saleOrderCardSales": so_card,
        "saleOrderUpiSales": so_upi,
        "bdCakeCashSales": bd_cash,
        "bdCakeCardSales": bd_card,
        "bdCakeUpiSales": bd_upi,
        "otherCashSales": other_cash,
        "otherCardSales": other_card,
        "otherUpiSales": other_upi,
        "totalKotSales": totalKotSales,
        "totalTakeAwaySales": totalTakeAwaySales,
        "totalSaleOrderSales": totalSaleOrderSales,
        "totalBdCakeSales": totalBdCakeSales,
    }
   

# --------------------- Close Shift API ---------------------
@router.patch("/close-shift/{shift_id}", response_model=Shift)
async def close_shift(shift_id: str, shift_update: ShiftPost):
    shift_collection = get_shift_collection()
    parsed_id = await parse_id(shift_id)

    existing_shift = await shift_collection.find_one({"_id": parsed_id})
    if not existing_shift:
        raise HTTPException(status_code=404, detail="Shift not found")

    updated_fields = shift_update.model_dump(exclude_unset=True)
    updated_fields["ClosingDateTime"] = await get_iso_datetime()

    manualCashsales = updated_fields.get("manualCashsales", 0.0)
    manualCardsales = updated_fields.get("manualCardsales", 0.0)
    manualUpisales = updated_fields.get("manualUpisales", 0.0)

    # ✅ Await calculate_sales
    sales_data = await calculate_sales(
        branch_name=existing_shift["branchName"],
        shift_id=shift_id,
        manualCashsales=await safe_float(manualCashsales),
        manualCardsales=await safe_float(manualCardsales),
        manualUpisales=await safe_float(manualUpisales)
    )

    updated_fields.update(sales_data)

    result = await shift_collection.update_one(
        {"_id": parsed_id},
        {"$set": updated_fields}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=400, detail="Failed to close shift.")

    updated_shift = await shift_collection.find_one({"_id": parsed_id})
    shift_data = {
        key: await convert_to_string_or_emptys(value)
        for key, value in updated_shift.items()
    }
    shift_data["shiftId"] = str(updated_shift["_id"])

    return Shift(**shift_data)

@router.patch("/dayend/{branch_name}", response_model=List[Shift])
async def close_shifts_and_mark_dayend(branch_name: str):
    if not branch_name:
        raise HTTPException(status_code=400, detail="branch_name is required")

    shift_collection = get_shift_collection()

    # 1) Close ALL open shifts for this branch
    await shift_collection.update_many(
        {"branchName": branch_name, "status": "open"},
        {"$set": {"status": "closed"}}
    )

    # 2) For ALL closed shifts of this branch, mark dayEndStatus = "closed"
    await shift_collection.update_many(
        {"branchName": branch_name, "status": "closed", "dayEndStatus": {"$ne": "closed"}},
        {"$set": {"dayEndStatus": "closed"}}
    )

    # 3) Return all closed shifts for this branch (after updates)
    updated_docs = await shift_collection.find(
        {"branchName": branch_name, "status": "closed"}
    ).to_list(length=None)

    if not updated_docs:
        raise HTTPException(status_code=404, detail=f"No shifts found to update for branch '{branch_name}'")

    formatted = []
    for doc in updated_docs:
        shift_data = {k: await convert_to_string_or_emptys(v) for k, v in doc.items()}
        shift_data["shiftId"] = str(doc["_id"])
        formatted.append(Shift(**shift_data))

    return formatted

# ---------------- DELETE ----------------
@router.delete("/{shift_id}")
async def delete_shift(shift_id: str):
    result = await get_shift_collection().delete_one({"_id": parse_id(shift_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Shift not found")
    return {"message": "Shift deleted successfully"}

# ---------------- OPENING BALANCE ----------------
@router.get("/openingbalance/", response_model=dict)
async def get_manual_opening_balance_by_branch_date(branch_name: str, date: str) -> Optional[dict]:
    try:
        date_parsed = datetime.strptime(date, "%d-%m-%Y").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Please use DD-MM-YYYY.")
    
    shift_collection = get_shift_collection()

    shifts = await shift_collection.find({
        "branchName": branch_name,
        "dayEndStatus": "open",
        "status": "open"
    }).to_list(length=None)

    shift = None
    for s in shifts:
        opening_dt = s.get("OpeningDateTime")
        if isinstance(opening_dt, datetime):
            if opening_dt.date() == date_parsed:
                shift = s
                break
        elif isinstance(opening_dt, str):
            try:
                parsed = datetime.fromisoformat(opening_dt.replace("Z", ""))
                if parsed.date() == date_parsed:
                    shift = s
                    break
            except Exception:
                continue

    if not shift:
        raise HTTPException(status_code=404, detail="No open shift found for given branch name and date.")

    manual_balance = shift.get("manualOpeningBalance", "0")
    return {"manualOpeningBalance": str(manual_balance)}

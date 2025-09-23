from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime
import pytz
from productionEntrys.utils import get_productionEntry_collection
from variance2.utils import get_variences_collection
from production_summary.models import Productionsummary

router = APIRouter()


# ---------------------------
# Utility: Parse Date
# ---------------------------
def get_iso_datetime(date_str: str) -> Optional[datetime]:
    for fmt in ("%d-%m-%Y", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.replace(tzinfo=pytz.UTC)
        except ValueError:
            continue
    return None


# ---------------------------
# Utility: Flatten nested lists
# ---------------------------
def flatten_items(item):
    flat = []
    if isinstance(item, list):
        for i in item:
            flat.extend(flatten_items(i))
    else:
        flat.append(str(item))
    return flat



# ---------------------------
# Get All Production Summary Entries
# ---------------------------
@router.get("/", response_model=List[Productionsummary])
async def get_all_productionsummary_entries(
    date: Optional[str] = Query(None, description="Filter by specific date (DD-MM-YYYY or YYYY-MM-DD)"),
    start_date: Optional[str] = Query(None, description="Start date for range filter"),
    end_date: Optional[str] = Query(None, description="End date for range filter"),
):
    query = {"status": {"$ne": "Cancel"}}

    # ---------------- Date Filter ----------------
    date_filter = {}
    if date:
        date_obj = get_iso_datetime(date)
        if not date_obj:
            raise HTTPException(status_code=400, detail="Invalid date format.")
        start_dt = date_obj.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        end_dt = date_obj.replace(hour=23, minute=59, second=59, microsecond=999999).isoformat()
        date_filter = {"$gte": start_dt, "$lte": end_dt}
    else:
        if start_date:
            start_obj = get_iso_datetime(start_date)
            if not start_obj:
                raise HTTPException(status_code=400, detail="Invalid start_date format.")
            date_filter["$gte"] = start_obj.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        if end_date:
            end_obj = get_iso_datetime(end_date)
            if not end_obj:
                raise HTTPException(status_code=400, detail="Invalid end_date format.")
            date_filter["$lte"] = end_obj.replace(hour=23, minute=59, second=59, microsecond=999999).isoformat()

    if date_filter:
        query["date"] = date_filter

    # ---------------- Collections ----------------
    productionEntry_collection = get_productionEntry_collection()
    variance2_collection = get_variences_collection()

    # ---------------- Variances ----------------
    variance2_cursor = variance2_collection.find(
        {},
        {"varianceName": 1, "varianceItemcode": 1, "category": 1, "subCategory": 1}
    )
    variance2_list = await variance2_cursor.to_list(length=None)

    # Build variance map
    variance2_map = {}
    for v in variance2_list:
        variance_names = flatten_items(v.get("varianceName", []))
        for name in variance_names:
            variance2_map[name] = {
                "itemCode": v.get("varianceItemcode", ""),
                "category": v.get("category") or "",
                "subCategory": v.get("subCategory") or "",
            }

    # ---------------- Summary Entries ----------------
    summary_cursor = productionEntry_collection.find(query)
    summary_list = await summary_cursor.to_list(length=None)

    formatted_summary_entries = []
    for entry in summary_list:
        entry["summaryId"] = str(entry.get("_id", ""))

        # Parse date
        if isinstance(entry.get("date"), str):
            try:
                entry["date"] = datetime.fromisoformat(entry["date"])
            except Exception:
                entry["date"] = datetime.utcnow().replace(tzinfo=pytz.UTC)

        # Flatten arrays
        item_names = flatten_items(entry.get("itemName", []))
        qtys = flatten_items(entry.get("qty", []))
        prices = flatten_items(entry.get("price", []))

        entry["itemCode"] = []
        entry["category"] = []
        entry["subCategory"] = []
        entry["totalqty"] = []
        entry["amount"] = []

        grand_qty = 0
        grand_amount = 0.0

        for idx, name in enumerate(item_names):
            mapped_data = variance2_map.get(name, {"itemCode": "", "category": "", "subCategory": ""})

            # qty from production entry (safe cast to int)
            try:
                item_qty = int(qtys[idx]) if idx < len(qtys) else 0
            except (ValueError, TypeError):
                item_qty = 0

            # price from production entry (safe cast to float)
            try:
                item_price = float(prices[idx]) if idx < len(prices) else 0.0
            except (ValueError, TypeError):
                item_price = 0.0

            # amount = qty × price
            item_amount = item_qty * item_price

            # Append per-item data
            entry["itemCode"].append(mapped_data["itemCode"])
            entry["category"].append(mapped_data["category"])
            entry["subCategory"].append(mapped_data["subCategory"])
            entry["totalqty"].append(item_qty)
            entry["amount"].append(item_amount)

            # Accumulate grand totals
            grand_qty += item_qty
            grand_amount += item_amount

        # ✅ Store per entry grand totals
        entry["grandTotalQty"] = grand_qty
        entry["grandTotalAmount"] = grand_amount

        # ✅ Ensure numeric fields are properly converted
        try:
            entry["totalAmount"] = float(entry.get("totalAmount", 0.0))
        except (ValueError, TypeError):
            entry["totalAmount"] = 0.0

        # Convert arrays too, just in case DB had strings
        entry["amount"] = [float(a) if isinstance(a, (int, float, str)) and str(a).replace('.', '', 1).isdigit() else 0.0 for a in entry["amount"]]
        entry["totalqty"] = [int(q) if str(q).isdigit() else 0 for q in entry["totalqty"]]

        formatted_summary_entries.append(Productionsummary(**entry))

    return formatted_summary_entries


from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime
import pytz
from productionEntrys.utils import get_productionEntry_collection
from variance2.utils import get_variences_collection
from production_summary.models import Productionsummary
from collections import defaultdict

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


@router.get("/grouped", response_model=List[Productionsummary])
async def get_grouped_productionsummary_entries(
    date: Optional[str] = Query(None, description="Filter by specific date (DD-MM-YYYY or YYYY-MM-DD)"),
):
    query = {"status": {"$ne": "Cancel"}}  # ✅ Exclude only cancelled
    filter_date = None

    # ---------------- Date filter ----------------
    if date:
        date_obj = get_iso_datetime(date)
        if not date_obj:
            raise HTTPException(status_code=400, detail="Invalid date format.")
        start_dt = date_obj.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        end_dt = date_obj.replace(hour=23, minute=59, second=59, microsecond=999999).isoformat()
        query["date"] = {"$gte": start_dt, "$lte": end_dt}
        filter_date = date_obj

    productionEntry_collection = get_productionEntry_collection()
    variance2_collection = get_variences_collection()
    
    count = await variance2_collection.count_documents({})
    print("Total documents in variance2_collection:", count)

    sample = await variance2_collection.find_one({})
    print("Sample document:", sample)


    # ---------------- Variance map ----------------
    variance2_list = await variance2_collection.find(
        {}, {"varianceName": 1, "varianceItemcode": 1,"category": 1,  "subcategory": 1} 
    ).to_list(length=None)
    
    print("variance list", variance2_list)

    variance2_map = {}
    for v in variance2_list:
        variance_names = flatten_items(v.get("varianceName", []))
        for name in variance_names:
            variance2_map[name] = {
                "itemCode": v.get("varianceItemcode", ""),
                "category": v.get("category") or "",
                "subcategory": v.get("subcategory") or "",  # ✅ fixed key
            }

    # ---------------- Fetch production entries ----------------
    summary_list = await productionEntry_collection.find(query).to_list(length=None)

    # ---------------- GROUPING LOGIC ----------------
    grouped = defaultdict(lambda: {"qty": 0, "amount": 0.0, "price": 0.0, "uom": ""})

    for entry in summary_list:
        item_names = flatten_items(entry.get("itemName", []))
        qtys = flatten_items(entry.get("qty", []))
        prices = flatten_items(entry.get("price", []))
        uoms = flatten_items(entry.get("uom", []))

        for idx, name in enumerate(item_names):
            mapped_data = variance2_map.get(name, {"itemCode": "", "category": "", "subcategory": ""})

            qty = int(qtys[idx]) if idx < len(qtys) and str(qtys[idx]).isdigit() else 0
            price = float(prices[idx]) if idx < len(prices) else 0.0
            amount = qty * price
            uom = uoms[idx] if idx < len(uoms) else ""

            # Use entry values if exist, else fallback to variance2
            category = ""
            subcategory = ""
            if entry.get("category") and idx < len(entry["category"]):
                category = entry["category"][idx] or ""
            else:
                category = mapped_data["category"]

            if entry.get("subcategory") and idx < len(entry["subcategory"]):
                subcategory = entry["subcategory"][idx] or ""
            else:
                subcategory = mapped_data["subcategory"]

            key = (name, category, subcategory, uom)
            grouped[key]["qty"] += qty
            grouped[key]["amount"] += amount
            grouped[key]["price"] = price   # latest price for that item
            grouped[key]["uom"] = uom

    # ---------------- SINGLE RECORD FORMAT ----------------
    variance_names, item_names, categories, subcategories, uoms = [], [], [], [], []
    qtys, amounts, prices = [], [], []

    for (name, category, subcategory, uom), values in grouped.items():
        variance_names.append(name)
        item_names.append(name)
        categories.append(category)
        subcategories.append(subcategory)
        uoms.append(uom)
        qtys.append(values["qty"])
        amounts.append(values["amount"])
        prices.append(values["price"])

    single_record = Productionsummary(
        varianceName=variance_names,
        itemName=item_names,
        category=categories,
        subcategory=subcategories,   # ✅ fixed to match schema
        uom=uoms,
        totalqty=qtys,
        price=prices,
        amount=amounts,
        totalAmount=sum(amounts),
        date=filter_date
    )
    return [single_record]
    
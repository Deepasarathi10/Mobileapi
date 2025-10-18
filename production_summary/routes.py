from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime
import pytz
from collections import defaultdict

from app.productionEntrys.utils import get_productionEntry_collection
from app.variance2.utils import get_variences_collection
from app.production_summary.models import Productionsummary

router = APIRouter()


# ---------------------------
# Utility: Parse Date
# ---------------------------
def get_iso_datetime(date_str: str) -> Optional[datetime]:
    """Parse date in either DD-MM-YYYY or YYYY-MM-DD format."""
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
    """Recursively flatten lists into a flat list of strings."""
    if isinstance(item, list):
        result = []
        for i in item:
            result.extend(flatten_items(i))
        return result
    return [str(item)]


# ---------------------------
# API: Grouped Production Summary
# ---------------------------
@router.get("/grouped", response_model=List[Productionsummary])
async def get_grouped_productionsummary_entries(
    date: Optional[str] = Query(None, description="Filter by specific date (DD-MM-YYYY or YYYY-MM-DD)")
):
    # ---------------- Prepare Query ----------------
    query = {"status": {"$ne": "deactive"}}
    filter_date = None

    if date:
        date_obj = get_iso_datetime(date)
        if not date_obj:
            raise HTTPException(status_code=400, detail="Invalid date format. Use DD-MM-YYYY or YYYY-MM-DD")

        start_dt = date_obj.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        end_dt = date_obj.replace(hour=23, minute=59, second=59, microsecond=999999).isoformat()
        query["date"] = {"$gte": start_dt, "$lte": end_dt}
        filter_date = date_obj

    # ---------------- Get Collections ----------------
    productionEntry_collection = get_productionEntry_collection()
    variance2_collection = get_variences_collection()

    # ---------------- Load Variance Map ----------------
    variance_docs = await variance2_collection.find(
        {}, {"varianceName": 1, "varianceItemcode": 1, "category": 1, "subcategory": 1}
    ).to_list(length=None)

    variance2_map = {}
    for v in variance_docs:
        names = flatten_items(v.get("varianceName", []))
        for name in names:
            variance2_map[name] = {
                "itemCode": v.get("varianceItemcode", ""),
                "category": v.get("category") or "",
                "subcategory": v.get("subcategory") or "",
            }

    # ---------------- Fetch Production Entries ----------------
    entries = await productionEntry_collection.find(query).to_list(length=None)

    # ---------------- Grouping Logic ----------------
    grouped = defaultdict(lambda: {"qty": 0, "amount": 0.0, "price": 0.0, "uom": "", "weight": 0.0})

    for entry in entries:
        item_names = flatten_items(entry.get("itemName", []))
        qtys = flatten_items(entry.get("qty", []))
        prices = flatten_items(entry.get("price", []))
        uoms = flatten_items(entry.get("uom", []))
        weights = flatten_items(entry.get("weight", []))

        categories = flatten_items(entry.get("category", []))
        subcategories = flatten_items(entry.get("subcategory", []))

        for idx, name in enumerate(item_names):
            mapped_data = variance2_map.get(name, {"itemCode": "", "category": "", "subcategory": ""})

            # Safely get numeric values
            qty = float(qtys[idx]) if idx < len(qtys) and str(qtys[idx]).replace('.', '', 1).isdigit() else 0.0
            weight = float(weights[idx]) if idx < len(weights) and str(weights[idx]).replace('.', '', 1).isdigit() else 0.0
            price = float(prices[idx]) if idx < len(prices) else 0.0
            uom = uoms[idx] if idx < len(uoms) else ""

            category = categories[idx] if idx < len(categories) else mapped_data["category"]
            subcategory = subcategories[idx] if idx < len(subcategories) else mapped_data["subcategory"]

            key = (name, category, subcategory, uom)
            grouped[key]["qty"] += qty
            grouped[key]["amount"] += qty * price
            grouped[key]["price"] = price  # latest known price
            grouped[key]["uom"] = uom
            grouped[key]["weight"] += weight

    # ---------------- Combine into Single Summary ----------------
    item_names, categories, subcategories, uoms = [], [], [], []
    qtys, amounts, prices, weights = [], [], [], []

    for (name, category, subcategory, uom), values in grouped.items():
        item_names.append(name)
        categories.append(category)
        subcategories.append(subcategory)
        uoms.append(uom)
        qtys.append(values["qty"])
        amounts.append(values["amount"])
        prices.append(values["price"])
        weights.append(values["weight"])

    single_record = Productionsummary(
        varianceName=item_names,
        itemName=item_names,
        category=categories,
        subcategory=subcategories,
        uom=uoms,
        totalqty=qtys,
        price=prices,
        amount=amounts,
        weight=weights,
        totalAmount=sum(amounts),
        date=filter_date,
    )

    return [single_record]

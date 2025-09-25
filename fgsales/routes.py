from fastapi import APIRouter, Query, HTTPException
from typing import List, Dict, Any, Optional
from datetime import datetime
from fgsummary.utils import get_sfgtofgdata_collection
from Invoice.utils import get_invoice_collection

router = APIRouter()

@router.get("/fg-sales")
async def get_fg_sales(
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    branch: Optional[str] = Query(None, description="Branch name")
) -> Dict[str, List[Dict[str, Any]]]:

    fg_sales_col = get_sfgtofgdata_collection()   # AsyncIOMotorCollection
    invoices_col = get_invoice_collection()     # AsyncIOMotorCollection

    # --- FG summary filter ---
    fg_sales_filter: Dict[str, Any] = {}
    if branch:
        fg_sales_filter["branch"] = branch
    if date:
        try:
            start_date = datetime.strptime(date, "%Y-%m-%d")
            end_date = start_date.replace(hour=23, minute=59, second=59)
            fg_sales_filter["dateTime"] = {"$gte": start_date, "$lte": end_date}
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    fg_sales_data = await fg_sales_col.find(fg_sales_filter).to_list(length=1000)

    # --- Invoice filter ---
    invoices_filter: Dict[str, Any] = {}
    if branch:
        invoices_filter["branchName"] = branch
    if date:
        try:
            dt = datetime.strptime(date, "%Y-%m-%d")
            invoice_date_str = dt.strftime("%d-%m-%Y")
            invoices_filter["invoiceDate"] = invoice_date_str
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    invoices_data = await invoices_col.find(invoices_filter).to_list(length=1000)  # ✅ await here

    # --- Build invoice sales map: itemName -> total qty ---
    invoice_sales_map: Dict[str, int] = {}

    for inv in invoices_data:
        item_names = inv.get("itemName") or []
        qtys = inv.get("qty") or []

        if not isinstance(item_names, list) or not isinstance(qtys, list):
            continue

        for name, qty in zip(item_names, qtys):
            if not name:
                continue
            try:
                qty_int = int(qty)
            except (ValueError, TypeError):
                qty_int = 0
            key = name.strip().upper()
            invoice_sales_map[key] = invoice_sales_map.get(key, 0) + qty_int

    # --- Build FG sales response ---
    fg_saleses: List[Dict[str, Any]] = []
    for item in fg_sales_data:
        fg_group = (item.get("fgCategory") or "").strip().upper()
        fg_converted = int(item.get("availableStock", 0))
        fg_sales = invoice_sales_map.get(fg_group, 0)
        fg_stock = fg_converted - fg_sales

        fg_saleses.append({
            "fgGroup": fg_group,
            "fgConverted": fg_converted,
            "fgSales": fg_sales,
            "fgStock": fg_stock,
            "dateTime": item.get("dateTime"),
            "branch": item.get("branch")
        })

    return {"fgSales": fg_saleses}

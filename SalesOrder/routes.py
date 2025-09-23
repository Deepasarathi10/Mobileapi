from io import BytesIO
import json
import os
import tempfile
from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, HTTPException, Path, Query, logger
from bson import ObjectId
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fpdf import FPDF
import httpx

from pydantic import BaseModel
from pymongo import ASCENDING, ReturnDocument
from HeldOrders.utils import get_holdOrder_collection
from dispatch.utils import get_dispatch_collection
from productionEntrys.models import get_iso_datetime
from productionEntrys.utils import get_productionEntry_collection
from toapprove.utils import get_toApprove_collection
from .models import Invoice, SalesOrder, SalesOrderPost, SalesOrderResponse, AdvancePaymentType, ModeWiseAmount
from .utils import  get_counter_collection, get_invoice_collection, get_salesOrder_collection
import logging
from datetime import datetime, timedelta
import time
from bson.errors import InvalidId
from typing import List, Optional
from datetime import datetime
from fastapi import Query, HTTPException
router = APIRouter()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def convert_to_date(date_str: str) -> datetime:
    """
    Converts a date string in "dd-MM-yyyy" format to a datetime object.
    Raises an exception if the format is invalid.
    """
    try:
        return datetime.strptime(date_str, "%d-%m-%Y")
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid date format: {date_str}. Please use dd-MM-yyyy."
        )
    
def fetch_sales_orders(query: dict) -> List[dict]:
    """
    Fetches sales orders from MongoDB based on the query.

    Args:
        query (dict): MongoDB query dictionary.

    Returns:
        List[dict]: List of sales orders retrieved from the database.
    """
    try:
        # Get the collection
        collection = get_salesOrder_collection()

        # Execute the query
        logger.debug(f"Executing MongoDB query: {query}")
        results = list(collection.find(query))

        logger.info(f"Retrieved {len(results)} records from MongoDB.")
        return results
    except Exception as e:
        logger.error(f"Error querying MongoDB: {e}", exc_info=True)
        raise    

def serialize_document_forget(order: dict):
    if isinstance(order["_id"], ObjectId):
        # Store the _id in salesOrderId for easier access
        order["salesOrderId"] = str(order["_id"])  # Convert ObjectId to string and store it in salesOrderId
        del order["_id"]  # Optionally remove the _id field, since it's now in salesOrderId

    # Convert deliveryDate to dd-mm-yyyy
    if order.get("deliveryDate"):
        order["deliveryDate"] = format_date_to_ddmmyyyy(order["deliveryDate"])

    if order.get("orderDate"):
        order["orderDate"] = format_date_to_ddmmyyyy_fororder(order["orderDate"])

    return order

def serialize_document_without_pagination(order: dict):
    if isinstance(order["_id"], ObjectId):
        # Store the _id in salesOrderId for easier access
        order["salesOrderId"] = str(order["_id"])  # Convert ObjectId to string and store it in salesOrderId
        del order["_id"]  # Optionally remove the _id field, since it's now in salesOrderId

    # Convert deliveryDate to dd-mm-yyyy
    if order.get("deliveryDate"):
        order["deliveryDate"] = format_date_to_ddmmyyyy(order["deliveryDate"])

    if order.get("orderDate"):
        order["orderDate"] = format_date_to_ddmmyyyy_fororder(order["orderDate"])

    return order    
def format_date_to_ddmmyyyy(date):
    if isinstance(date, str):
        # If already a string in dd-mm-yyyy format, return it directly
        try:
            datetime.strptime(date, "%d-%m-%Y")  # Validate the format
            return date
        except ValueError:
            raise ValueError(f"Invalid date format: {date}. Expected dd-mm-yyyy.")
    elif isinstance(date, datetime):
        return date.strftime("%d-%m-%Y")
    else:
        raise TypeError(f"Unsupported type for date: {type(date)}")
        
def format_date_to_ddmmyyyy_fororder(date):
    if isinstance(date, str) and "T" in date:  # Check for ISODate format
        return datetime.strptime(date[:10], "%Y-%m-%d").strftime("%d-%m-%Y")
    elif isinstance(date, datetime):
        return date.strftime("%d-%m-%Y")
    return date
    
def fetch_sales_orders_try(query: dict) -> List[dict]:
   
    try:
        # Get the collection
        collection = get_salesOrder_collection()

        # Execute the query
        logger.debug(f"Executing MongoDB query: {query}")
        results = list(collection.find(query))

        logger.info(f"Retrieved {len(results)} records from MongoDB.")
        return results
    except Exception as e:
        logger.error(f"Error querying MongoDB: {e}", exc_info=True)
        raise  

@router.post("/", response_model=str)
async def create_salesOrder(payload: dict):
    try:
        # Extract data from payload
        if "data" in payload:
            post_data = payload["data"]
            if isinstance(post_data, list):
                post_data = post_data[0]
            elif not isinstance(post_data, dict):
                raise HTTPException(status_code=400, detail="Invalid data format")
        else:
            post_data = payload

        if not post_data:
            raise HTTPException(status_code=400, detail="Missing data")

        # Process deliveryDate if present
        if "deliveryDate" in post_data:
            try:
                post_data["deliveryDate"] = convert_to_date(post_data["deliveryDate"])
            except ValueError as ve:
                raise HTTPException(status_code=400, detail=str(ve))
            
        if "eventDate" in post_data:
            try:
                post_data["eventDate"] = convert_to_date(post_data["eventDate"])
            except ValueError as ve:
                raise HTTPException(status_code=400, detail=str(ve))            


        # Insert the provided data into MongoDB
        result = await get_salesOrder_collection().insert_one(post_data)
        inserted_id = str(result.inserted_id)
        print(f"Data posted with ID: {inserted_id}")
        return inserted_id

    except Exception as e:
        print(f"Error posting data: {e}")
        raise HTTPException(status_code=500, detail="Failed to post data")
    
@router.get("/")    
async def get_sales_orders(
    deliveryStartDate: Optional[str] = Query(None),
    deliveryEndDate: Optional[str] = Query(None),
    deliveryDate: Optional[str] = Query(None),
    customerNumber: Optional[str] = None,
    customerName: Optional[str] = None,
    saleOrderNo: Optional[str] = None,
    orderDate: Optional[str] = None,
    paymentType: Optional[str] = None,
    minAdvanceAmount: Optional[float] = None,
    salesOrderLast5Digits: Optional[str] = None,
    status: Optional[str] = None,
    branchName: Optional[str] = None,
    filterCreditCustomer: Optional[bool] = Query(False, alias="filter-credit-customer"),
    filterCreditCustomerPreinvoice: Optional[bool] = Query(False, alias="filter-credit-customer-preinvoice"),
    approvalStatus: Optional[str] = None,
    approvalType: Optional[str] = None,
    summary: Optional[str] = None,
    approvalDate: Optional[str] = Query(None),
    approvalStartDate: Optional[str] = Query(None),
    approvalEndDate: Optional[str] = Query(None),
    page: Optional[int]= Query(1, ge=1),
    limit: Optional[int]= Query(10, ge=1, le=100)
):
    try:
        logger.info("Received request to fetch sales orders.")

        query = {}
        approval_filter = {}

        # --- Apply filters (same as your code) ---
        if deliveryStartDate and deliveryEndDate:
            start_date = datetime.strptime(deliveryStartDate, "%d-%m-%Y")
            end_date = datetime.strptime(deliveryEndDate, "%d-%m-%Y").replace(hour=23, minute=59, second=59)
            query["deliveryDate"] = {"$gte": start_date, "$lte": end_date}
        elif deliveryDate:
            query["deliveryDate"] = datetime.strptime(deliveryDate, "%d-%m-%Y")

        if approvalStatus:
            approval_filter["approvalStatus"] = {"$regex": f"^{approvalStatus}$", "$options": "i"}
        if approvalType:
            approval_filter["approvalType"] = {"$regex": f"^{approvalType}$", "$options": "i"}
        if summary:
            approval_filter["summary"] = {"$regex": f"^{summary}$", "$options": "i"}

        if approvalStartDate and approvalEndDate:
            start_date = datetime.strptime(approvalStartDate, "%d-%m-%Y")
            end_date = datetime.strptime(approvalEndDate, "%d-%m-%Y").replace(hour=23, minute=59, second=59)
            approval_filter["approvalDate"] = {"$gte": start_date, "$lte": end_date}
        elif approvalStartDate:
            approval_filter["approvalDate"] = {"$gte": datetime.strptime(approvalStartDate, "%d-%m-%Y")}
        elif approvalEndDate:
            approval_filter["approvalDate"] = {"$lte": datetime.strptime(approvalEndDate, "%d-%m-%Y").replace(hour=23, minute=59, second=59)}

        if approvalDate:
            approval_filter["approvalDate"] = datetime.strptime(approvalDate, "%d-%m-%Y")

        if approval_filter:
            query["approvalDetails"] = {"$elemMatch": approval_filter}

        if customerName:
            query["customerName"] = {"$regex": customerName, "$options": "i"}
        if customerNumber:
            query["customerNumber"] = {"$regex": customerNumber, "$options": "i"}
        if status:
            query["status"] = {"$regex": f"^{status}$", "$options": "i"}
        if branchName:
            query["branchName"] = {"$regex": branchName, "$options": "i"}
        if salesOrderLast5Digits:
            query["salesOrderId"] = {"$regex": f"{salesOrderLast5Digits}$", "$options": "i"}
        if saleOrderNo:
            query["saleOrderNo"] = {"$regex": saleOrderNo, "$options": "i"}

        if filterCreditCustomer:
            query["creditCustomerOrder"] = "yes"
        if filterCreditCustomerPreinvoice:
            query["creditCustomerOrder"] = "credit sales order pre invoiced"

        # ✅ Fetch data asynchronously
        raw_orders = await fetch_sales_orders(query, page, limit)

        # ✅ Count documents asynchronously
        total_items = await get_salesOrder_collection().count_documents(query)
        total_pages = (total_items + limit - 1) // limit

        # Serialize results
        serialized_orders = [serialize_document_forget(order) for order in raw_orders]

        return {
            "data": serialized_orders,
            "pagination": {
                "total_items": total_items,
                "total_pages": total_pages,
                "current_page": page,
                "items_per_page": limit
            }
        }

    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


# ✅ Keep only the async fetch_sales_orders
async def fetch_sales_orders(query, page, limit):
    skip = (page - 1) * limit
    cursor =  get_salesOrder_collection().find(query).skip(skip).limit(limit)
    return await cursor.to_list(length=limit)

async def fetch_sales_orders_without_paginatiom(query):
    collection = get_salesOrder_collection()
    
    # Fetch all matching documents asynchronously
    results = await collection.find(query).to_list(length=None)
    return results

@router.get("/grouped-by-delivery-date")
async def get_sales_orders_grouped_by_delivery_date(
    deliveryStartDate: Optional[str] = Query(None),
    deliveryEndDate: Optional[str] = Query(None),
    customerNumber: Optional[str] = None,
    saleOrderNo: Optional[str] = None,
    customerName: Optional[str] = None,
    status: Optional[str] = None,
    branchName: Optional[str] = None,
    page: Optional[int] = Query(1, ge=1),  # Default to page 1
    limit: Optional[int] = Query(4, ge=1, le=100)  # Default to 10 items per page, max 100
):
    """
    Fetch sales orders grouped by deliveryDate with filtering options.
    """
    try:
        logger.info("Received request to fetch grouped sales orders.")

        # Build query
        query = {}

        # Parse delivery date filters
        if deliveryStartDate and deliveryEndDate:
            start_date = datetime.strptime(deliveryStartDate, "%d-%m-%Y")
            end_date = datetime.strptime(deliveryEndDate, "%d-%m-%Y").replace(hour=23, minute=59, second=59)
            query["deliveryDate"] = {"$gte": start_date, "$lte": end_date}
        elif deliveryStartDate:
            start_date = datetime.strptime(deliveryStartDate, "%d-%m-%Y")
            query["deliveryDate"] = {"$gte": start_date}
        elif deliveryEndDate:
            end_date = datetime.strptime(deliveryEndDate, "%d-%m-%Y").replace(hour=23, minute=59, second=59)
            query["deliveryDate"] = {"$lte": end_date}

        # Apply optional filters
        if customerName:
            query["customerName"] = {"$regex": customerName, "$options": "i"}
        if customerNumber:
            query["customerNumber"] = {"$regex": customerNumber, "$options": "i"}
        if status:
            query["status"] = {"$regex": f"^{status}$", "$options": "i"}
        if branchName:
            query["branchName"] = {"$regex": branchName, "$options": "i"}
        if saleOrderNo:
            query["saleOrderNo"] = {"$regex": f"{saleOrderNo}", "$options": "i"}  # Partial match enabled
            logger.debug(f"Updated query with partial saleOrderNo filter: {query}")            

        logger.debug(f"Final query for grouping: {query}")

        # Group by deliveryDate using MongoDB aggregation
        grouped_orders = fetch_grouped_sales_orders(query, page, limit)

        for group in grouped_orders:
            for order in group["orders"]:
                order["salesOrderId"] = order.pop("_id")


        return {
            "data": grouped_orders,
            "pagination": {
                "current_page": page,
                "items_per_page": limit
            }
        }

    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


def serialize_document(doc):
    """Convert MongoDB document to JSON serializable format"""
    if isinstance(doc, ObjectId):
        return str(doc)
    if isinstance(doc, dict):
        return {k: serialize_document(v) for k, v in doc.items()}
    if isinstance(doc, list):
        return [serialize_document(i) for i in doc]
    return doc


def fetch_grouped_sales_orders(query, page, limit):
    collection = get_salesOrder_collection()
    pipeline = [
        {"$match": query},
        {"$group": {
            "_id": "$deliveryDate",
            "orders": {"$push": "$$ROOT"},
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id": 1}},  # Sort by deliveryDate
        {"$skip": (page - 1) * limit},  # Pagination
        {"$limit": limit}
    ]
    
    grouped_orders = list(collection.aggregate(pipeline))
    
    # Convert ObjectId to string
    return serialize_document(grouped_orders)


@router.get("/grouped-by-order-date")
async def get_sales_orders_grouped_by_order_date(
    orderStartDate: Optional[str] = Query(None),
    orderEndDate: Optional[str] = Query(None),
    customerNumber: Optional[str] = None,
    saleOrderNo: Optional[str] = None,
    customerName: Optional[str] = None,
    status: Optional[str] = None,
    branchName: Optional[str] = None,
    page: Optional[int] = Query(1, ge=1),  # Default to page 1
    limit: Optional[int] = Query(4, ge=1, le=100)  # Default to 10 items per page, max 100
):
    """
    Fetch sales orders grouped by orderDate with filtering options.
    """
    try:
        logger.info("Received request to fetch grouped sales orders by orderDate.")

        # Build query
        query = {}

        # Parse order date filters
        if orderStartDate and orderEndDate:
            start_date = datetime.strptime(orderStartDate, "%d-%m-%Y")
            end_date = datetime.strptime(orderEndDate, "%d-%m-%Y").replace(hour=23, minute=59, second=59)
            query["orderDate"] = {"$gte": start_date, "$lte": end_date}
        elif orderStartDate:
            start_date = datetime.strptime(orderStartDate, "%d-%m-%Y")
            query["orderDate"] = {"$gte": start_date}
        elif orderEndDate:
            end_date = datetime.strptime(orderEndDate, "%d-%m-%Y").replace(hour=23, minute=59, second=59)
            query["orderDate"] = {"$lte": end_date}

        # Apply optional filters
        if customerName:
            query["customerName"] = {"$regex": customerName, "$options": "i"}
        if customerNumber:
            query["customerNumber"] = {"$regex": customerNumber, "$options": "i"}
        if status:
            query["status"] = {"$regex": f"^{status}$", "$options": "i"}
        if branchName:
            query["branchName"] = {"$regex": branchName, "$options": "i"}
        if saleOrderNo:
            query["saleOrderNo"] = {"$regex": f"{saleOrderNo}", "$options": "i"}  # Partial match enabled
            logger.debug(f"Updated query with partial saleOrderNo filter: {query}")

        logger.debug(f"Final query for grouping by orderDate: {query}")

        # Group by orderDate using MongoDB aggregation
        grouped_orders = fetch_grouped_sales_orders_fororder(query, page, limit, group_by_field="orderDate")

        for group in grouped_orders:
            for order in group["orders"]:
                order["salesOrderId"] = order.pop("_id")

        return {
            "data": grouped_orders,
            "pagination": {
                "current_page": page,
                "items_per_page": limit
            }
        }

    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")

def fetch_grouped_sales_orders_fororder(query, page, limit, group_by_field="orderDate"):
    collection = get_salesOrder_collection()
    pipeline = [
        {"$match": query},
        {"$group": {
            "_id": "$" + group_by_field,
            "orders": {"$push": "$$ROOT"}
        }},
        {"$sort": {"_id": 1}},  # Sort by orderDate
        {"$skip": (page - 1) * limit},
        {"$limit": limit}
    ]
    
   
    grouped_orders = list(collection.aggregate(pipeline))
    
    # Convert ObjectId to string
    return serialize_document(grouped_orders)
    # return list(mongo_collection.aggregate(pipeline))



class PDF(FPDF):
    def multi_cell_in_table(self, w, h, txt, border=0, align='L', fill=False):
        """Multi-cell that stays in the same row (for wrapped text)."""
        x = self.get_x()
        y = self.get_y()
        self.multi_cell(w, h, txt, border, align, fill)
        self.set_xy(x + w, y)


def generate_sales_order_pdf_for_items(orders: List[Dict[Any, Any]]) -> StreamingResponse:
    pdf = PDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_margins(10, 10, 10)

    # Title
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(277, 12, "Sales Order Summary Report", ln=True, align='C')
    pdf.set_font('Arial', '', 10)
    pdf.cell(277, 8, f"Generated on: {datetime.now().strftime('%d-%m-%Y %H:%M')}", ln=True, align='C')
    pdf.ln(4)
    
    grand_total = sum(float(order.get("totalAmount", 0)) for order in orders)

    # Print overall total above the table
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(277, 10, f"Overall Total Amount: {grand_total:.2f}", ln=True, align='R')
    pdf.ln(4)

    # Column configuration
    columns = [
        {"header": "Customer Name", "width": 32, "align": "L", "field": "customerName"},
        {"header": "Customer No.", "width": 23, "align": "C", "field": "customerNumber"},
        {"header": "SaleOrder No.", "width": 23, "align": "C", "field": "saleOrderNo"},
        {"header": "Branch", "width": 20, "align": "L", "field": "branchName"},
        {"header": "Item Name", "width": 32, "align": "L", "field": "itemName"},
        {"header": "Qty", "width": 13, "align": "R", "field": "qty"},
        {"header": "Price", "width": 13, "align": "R", "field": "price"},
        {"header": "Weight", "width": 18, "align": "R", "field": "weight"},
        {"header": "Amount", "width": 15, "align": "R", "field": "amount"},
        {"header": "Tax", "width": 7, "align": "R", "field": "tax"},
        {"header": "UOM", "width": 11, "align": "C", "field": "uom"},
        {"header": "Status", "width": 18, "align": "L", "field": "approvalStatus"},  # wrapped
        {"header": "Approval Date", "width": 25, "align": "C", "field": "approvalDate"},
        {"header": "Net Price", "width": 18, "align": "R", "field": "netPrice"},
        {"header": "Total", "width": 18, "align": "R", "field": "totalAmount"},
    ]

    # Draw header
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font('Arial', 'B', 9)
    for col in columns:
        pdf.cell(col["width"], 8, col["header"], border=1, align=col["align"], fill=True)
    pdf.ln()

    # Body
    pdf.set_font('Arial', '', 8)
    for order in orders:
        customer_data = {
            "customerName": str(order.get("customerName", "")),
            "customerNumber": str(order.get("customerNumber", "")),
            "saleOrderNo": str(order.get("saleOrderNo","")),
            "branchName": str(order.get("branchName", "")),
            "approvalStatus": str(order.get("approvalStatus", "")),
            "netPrice": f"{float(order.get('netPrice', 0)):.2f}",
            "totalAmount": f"{float(order.get('totalAmount', 0)):.2f}",
        }

        # Approval date formatting
        approval_date = None
        if isinstance(order.get("approvalDetails"), dict):
            approval_date = order["approvalDetails"].get("approvalDate")
        elif isinstance(order.get("approvalDetails"), list) and order["approvalDetails"]:
            approval_date = order["approvalDetails"][0].get("approvalDate")

        if isinstance(approval_date, datetime):
            customer_data["approvalDate"] = approval_date.strftime("%d-%m-%Y")
        elif isinstance(approval_date, str):
            try:
                customer_data["approvalDate"] = datetime.strptime(approval_date, "%Y-%m-%d").strftime("%d-%m-%Y")
            except ValueError:
                customer_data["approvalDate"] = ""
        else:
            customer_data["approvalDate"] = ""

        # Items
        item_lists = {
            "itemName": order.get("itemName", []),
            "qty": order.get("qty", []),
            "price": order.get("price", []),
            "weight": order.get("weight", []),
            "amount": order.get("amount", []),
            "tax": order.get("tax", []),
            "uom": order.get("uom", []),
        }

        max_items = max((len(v) if isinstance(v, list) else 0) for v in item_lists.values()) or 1
        for k, v in item_lists.items():
            if not isinstance(v, list):
                item_lists[k] = [v]
            item_lists[k] += [""] * (max_items - len(item_lists[k]))

        for i in range(max_items):
            pdf.set_fill_color(252, 252, 252) if i % 2 == 0 else pdf.set_fill_color(248, 248, 248)

            for col in columns:
                if col["field"] in item_lists:
                    value = str(item_lists[col["field"]][i])
                else:
                    value = customer_data.get(col["field"], "") if i == 0 else ""

                if col["field"] == "approvalStatus" and len(value) > 12:
                    pdf.multi_cell_in_table(col["width"], 4, value, border=1, align=col["align"], fill=True)
                else:
                    pdf.cell(col["width"], 7, value, border=1, align=col["align"], fill=True)
            pdf.ln()

        pdf.cell(sum(col["width"] for col in columns), 0, "", border="T")
        pdf.ln(1)

    # Output PDF
    pdf_output = BytesIO()
    pdf_output.write(pdf.output(dest="S").encode("latin1"))
    pdf_output.seek(0)

    return StreamingResponse(
        pdf_output,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=sales_order_summary.pdf"}
    )
    
@router.get("/download_sales_orders_pdf")
async def download_sales_orders_pdf(
    approvalStartDate: Optional[str] = Query(None),
    approvalEndDate: Optional[str] = Query(None),
):
    print("▶ Entered download_sales_orders_pdf endpoint")
    print(f"📝 Received Query Params → approvalStartDate={approvalStartDate}, approvalEndDate={approvalEndDate}")

    # Field path for nested approval date
    date_field = "approvalDetails.approvalDate"
    query = {}
    print(f"📌 Initial empty query object: {query}")

    # ---------------------------
    # Date Filtering Logic
    # ---------------------------
    if approvalStartDate and approvalEndDate:
        print("🔍 Both approvalStartDate and approvalEndDate are provided.")
        try:
            start_date = datetime.strptime(approvalStartDate, "%d-%m-%Y")
            end_date = datetime.strptime(approvalEndDate, "%d-%m-%Y").replace(hour=23, minute=59, second=59)
            print(f"   ✅ Parsed start_date: {start_date} | end_date: {end_date}")
            query[date_field] = {"$gte": start_date, "$lte": end_date}
            print(f"   📌 Applied range filter on '{date_field}': {query[date_field]}")
        except ValueError:
            print("   ❌ Invalid date format detected. Expected format: DD-MM-YYYY")
            raise HTTPException(status_code=400, detail="Invalid date format. Use DD-MM-YYYY.")

    elif approvalStartDate:
        print("🔍 Only approvalStartDate is provided.")
        try:
            start_date = datetime.strptime(approvalStartDate, "%d-%m-%Y")
            print(f"   ✅ Parsed start_date: {start_date}")
            query[date_field] = {"$gte": start_date}
            print(f"   📌 Applied start date filter on '{date_field}': {query[date_field]}")
        except ValueError:
            print("   ❌ Invalid approvalStartDate format.")
            raise HTTPException(status_code=400, detail="Invalid start date format. Use DD-MM-YYYY.")

    elif approvalEndDate:
        print("🔍 Only approvalEndDate is provided.")
        try:
            end_date = datetime.strptime(approvalEndDate, "%d-%m-%Y").replace(hour=23, minute=59, second=59)
            print(f"   ✅ Parsed end_date: {end_date}")
            query[date_field] = {"$lte": end_date}
            print(f"   📌 Applied end date filter on '{date_field}': {query[date_field]}")
        except ValueError:
            print("   ❌ Invalid approvalEndDate format.")
            raise HTTPException(status_code=400, detail="Invalid end date format. Use DD-MM-YYYY.")

    else:
        print("ℹ No date filters applied.")

    print(f"✅ Final MongoDB query object: {query}")

    # ---------------------------
    # Fetching Orders
    # ---------------------------
    try:
        print("⏳ Calling fetch_sales_orders_try() with query...")
        raw_orders = fetch_sales_orders_try(query)
        print(f"📦 Raw fetched orders count: {len(raw_orders) if raw_orders else 0}")
        print(f"📦 Raw fetched orders (sample): {raw_orders[:1] if raw_orders else 'No data'}")

        if not raw_orders:
            print("❌ No sales orders found matching the given criteria.")
            raise HTTPException(status_code=404, detail="No sales orders found for the given criteria.")

        print(f"✅ Found {len(raw_orders)} matching orders. Proceeding to PDF generation.")

        # ---------------------------
        # PDF Generation
        # ---------------------------
        print("⏳ Generating PDF from fetched orders...")
        pdf_response = generate_sales_order_pdf(raw_orders)
        print("✅ PDF generated successfully. Returning response to client.")

        return pdf_response

    except HTTPException as http_err:
        print(f"❌ HTTPException occurred: {http_err.detail}")
        raise
    except Exception as e:
        print(f"💥 Unexpected error occurred in download_sales_orders_pdf: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


def generate_sales_order_pdf(orders):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Header
    pdf.set_font("Arial", size=12, style='B')
    pdf.cell(200, 10, txt="Sales Order Summary Report", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", size=10)
    pdf.cell(200, 10, txt=f"Generated On: {datetime.now().strftime('%d-%m-%Y')}", ln=True, align='C')
    pdf.ln(10)

    # Table Header
    pdf.set_font("Arial", size=10, style='B')
    pdf.cell(30, 10, "Sale Order No", border=1, align='C')
    pdf.cell(50, 10, "Customer Name", border=1, align='C')
    pdf.cell(35, 10, "Approval Status", border=1, align='C')
    pdf.cell(30, 10, "Approval Date", border=1, align='C')
    pdf.cell(30, 10, "Amount", border=1, align='C')
    pdf.ln()

    # Table Data
    pdf.set_font("Arial", size=10)
    for order in orders:
        sale_order_no = str(order.get("saleOrderNo", ""))
        customer_name = str(order.get("customerName", ""))
        approval_status = str(order.get("approvalStatus", ""))

        # ✅ FIX: Handle approvalDetails as list or dict
        approval_date = None
        if "approvalDetails" in order:
            details = order["approvalDetails"]

            if isinstance(details, dict):
                approval_date = details.get("approvalDate")
            elif isinstance(details, list) and len(details) > 0 and isinstance(details[0], dict):
                approval_date = details[0].get("approvalDate")

        # Convert approval_date to display format
        if isinstance(approval_date, datetime):
            approval_date = approval_date.strftime("%d-%m-%Y")
        elif isinstance(approval_date, str):
            try:
                approval_date = datetime.strptime(approval_date, "%Y-%m-%d").strftime("%d-%m-%Y")
            except ValueError:
                approval_date = "N/A"
        else:
            approval_date = "N/A"

        total_amount = str(order.get("totalAmount", ""))

        pdf.cell(30, 10, sale_order_no, border=1, align='C')
        pdf.cell(50, 10, customer_name, border=1, align='C')
        pdf.cell(35, 10, approval_status, border=1, align='C')
        pdf.cell(30, 10, approval_date, border=1, align='C')
        pdf.cell(30, 10, total_amount, border=1, align='C')
        pdf.ln()

    pdf_output = BytesIO()
    pdf_data = pdf.output(dest='S').encode('latin1')
    pdf_output.write(pdf_data)
    pdf_output.seek(0)

    return StreamingResponse(
        pdf_output,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline; filename=sales_order_summary.pdf"}
    )
    
@router.get("/download_sales_orders_items_pdf")
async def download_sales_orders_pdf_items(
    approvalStartDate: Optional[str] = Query(None),  # New filter
    approvalEndDate: Optional[str] = Query(None),  # New filter
    # Other parameters can be added here...
):
    """
    Fetch sales orders based on query parameters, with approvalDate filtering.
    """
    try:
        # Log incoming request parameters
        logger.info("Received request to fetch sales orders.")
        logger.info(f"Input parameters: approvalStartDate={approvalStartDate}, approvalEndDate={approvalEndDate}")

        # Initialize the query object
        date_field = "approvalDetails.approvalDate"
        query = {}
        logger.debug(f"Initial query: {query}")

        # Apply approval start and end date filters
        if approvalStartDate and approvalEndDate:
            try:
                # Parse start and end dates from query parameters
                start_date = datetime.strptime(approvalStartDate, "%d-%m-%Y")
                end_date =  datetime.strptime(approvalEndDate, "%d-%m-%Y")
                end_date = end_date.replace(hour=23, minute=59, second=59)  # Set end time to end of the day

                # Update the query to filter on approvalDate range
                query[date_field] = {"$gte": start_date, "$lte": end_date}
                logger.debug(f"Updated query with approvalDate filter: {query}")
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Use DD-MM-YYYY.")
        elif approvalStartDate:
            try:
                start_date = datetime.strptime(approvalStartDate, "%d-%m-%Y")
                query[date_field] = {"$gte": start_date}
                logger.debug(f"Updated query with approvalStartDate filter: {query}")
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid start date format. Use DD-MM-YYYY.")
        elif approvalEndDate:
            try:
                end_date = datetime.strptime(approvalEndDate, "%d-%m-%Y")
                end_date = end_date.replace(hour=23, minute=59, second=59)  # Set end time to end of the day
                query[date_field] = {"$lte": end_date}
                logger.debug(f"Updated query with approvalEndDate filter: {query}")
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid end date format. Use DD-MM-YYYY.")

        # Final query to be used in the database query
        logger.debug(f"Final query: {query}")

        # Fetch sales orders from the database (replace with your actual DB call)
        raw_orders = fetch_sales_orders_try(query)

        logger.debug(f"Raw orders fetched from DB: {raw_orders}")

        if not raw_orders:  
            # logger.debug("No orders found based on the query.")
            # return []
             raise HTTPException(status_code=404, detail="No sales orders found for the given criteria.")
        
        pdf_response = generate_sales_order_pdf_for_items(raw_orders)
        # Serialize the fetched orders (replace with your actual serialization method)
        # serialized_orders = [serialize_document(order) for order in raw_orders]
        # logger.debug(f"Serialized orders: {serialized_orders}")

        # # Return the serialized orders
        return pdf_response

    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")
@router.get("/{salesOrder_id}", response_model=SalesOrder)
async def get_salesOrder_by_id(salesOrder_id: str):
    salesOrder = get_salesOrder_collection().find_one({"_id": ObjectId(salesOrder_id)})
    if salesOrder:
        salesOrder["salesOrderId"] = str(salesOrder["_id"])
        return SalesOrder(**salesOrder)
    else:
        raise HTTPException(status_code=404, detail="SalesOrder not found")


@router.get("/withoutpagination/")
async def get_sales_orders(
    deliveryStartDate: Optional[str] = Query(None),
    deliveryEndDate: Optional[str] = Query(None),
    deliveryDate: Optional[str] = Query(None),
    deliveryDates: Optional[List[str]] = Query(None),  # New filter for multiple delivery dates
    customerNumber: Optional[str] = None,
    customerName: Optional[str] = None,
    saleOrderNo: Optional[str] = None,
    orderDate: Optional[str] = None,
    paymentType: Optional[str] = None,
    minAdvanceAmount: Optional[float] = None,
    salesOrderLast5Digits: Optional[str] = None,
    status: Optional[str] = None,
    branchName: Optional[str] = None,
    filterCreditCustomer: Optional[bool] = Query(False, alias="filter-credit-customer"),
    filterCreditCustomerPreinvoice: Optional[bool] = Query(False, alias="filter-credit-customer-preinvoice"),
    approvalStatus: Optional[str] = None,
    approvalType: Optional[str] = None,
    summary: Optional[str] = None,
    approvalDate: Optional[str] = Query(None),
    approvalStartDate: Optional[str] = Query(None),
    approvalEndDate: Optional[str] = Query(None)
):
    """
    Fetch sales orders based on query parameters, now supporting multiple delivery dates.
    """
    try:
        logger.info("Received request to fetch sales orders with multiple delivery date filters.")

        query = {}
        approval_filter = {}
        # Handle delivery date range filtering
        if deliveryStartDate and deliveryEndDate:
            start_date = datetime.strptime(deliveryStartDate, "%d-%m-%Y")
            end_date = datetime.strptime(deliveryEndDate, "%d-%m-%Y").replace(hour=23, minute=59, second=59)
            query["deliveryDate"] = {"$gte": start_date, "$lte": end_date}
        
        elif deliveryStartDate:
            start_date = datetime.strptime(deliveryStartDate, "%d-%m-%Y")
            query["deliveryDate"] = {"$gte": start_date}
        
        elif deliveryEndDate:
            end_date = datetime.strptime(deliveryEndDate, "%d-%m-%Y").replace(hour=23, minute=59, second=59)
            query["deliveryDate"] = {"$lte": end_date}

        # elif deliveryDate:
        #     try:
        #         delivery_date = datetime.strptime(deliveryDate, "%d-%m-%Y").replace(hour=23, minute=59, second=59)
        #         query["deliveryDate"] = delivery_date
        #     except ValueError:
        #         raise HTTPException(status_code=400, detail="Invalid delivery date format. Use DD-MM-YYYY.")    
        elif deliveryDate:
            specific_date = datetime.strptime(deliveryDate, "%d-%m-%Y")
            query["deliveryDate"] = specific_date
            logger.debug(f"Updated query with specific deliveryDate filter: {query}")        

        # Handle multiple delivery dates filtering
        if deliveryDates:
            try:
                parsed_dates = [datetime.strptime(date, "%d-%m-%Y") for date in deliveryDates]
                query["deliveryDate"] = {"$in": parsed_dates}
                logger.debug(f"Updated query with multiple deliveryDates filter: {query}")
            except ValueError as e:
                logger.error(f"Error parsing deliveryDates: {deliveryDates} - {e}")
                raise HTTPException(status_code=400, detail="Invalid delivery date format. Use DD-MM-YYYY.")
            
        if approvalStatus:
            approval_filter["approvalStatus"] = {"$regex": f"^{approvalStatus}$", "$options": "i"}
        if approvalType:
            approval_filter["approvalType"] = {"$regex": f"^{approvalType}$", "$options": "i"}
        if summary:
            approval_filter["summary"] = {"$regex": f"^{summary}$", "$options": "i"}

        if approvalStartDate and approvalEndDate:
            start_date = datetime.strptime(approvalStartDate, "%d-%m-%Y")
            end_date = datetime.strptime(approvalEndDate, "%d-%m-%Y")
            end_date = end_date.replace(hour=23, minute=59, second=59)
            approval_filter["approvalDate"] = {"$gte": start_date, "$lte": end_date}
        elif approvalStartDate:
            start_date = datetime.strptime(approvalStartDate, "%d-%m-%Y")
            approval_filter["approvalDate"] = {"$gte": start_date}
        elif approvalEndDate:
            end_date = datetime.strptime(approvalEndDate, "%d-%m-%Y")
            end_date = end_date.replace(hour=23, minute=59, second=59)
            approval_filter["approvalDate"] = {"$lte": end_date}

        if approvalDate:
            approval_date = datetime.strptime(approvalDate, "%d-%m-%Y")
            approval_filter["approvalDate"] = approval_date

        if approval_filter:
            query["approvalDetails"] = {"$elemMatch": approval_filter}

        if saleOrderNo:
            query["saleOrderNo"] = {"$regex": f"{saleOrderNo}", "$options": "i"}  # Partial match enabled
            logger.debug(f"Updated query with partial saleOrderNo filter: {query}")

        if status:
            query["status"] = {"$regex": f"^{status}$", "$options": "i"}  # Match exact status (case-insensitive)
            logger.debug(f"Updated query with status filter: {query}")

        # Apply branchName filter (existing code)
        if branchName:
            query["branchName"] = {"$regex": branchName, "$options": "i"}  # Partial match enabled for branchName
            logger.debug(f"Updated query with branchName filter: {query}")

        # Fetch sales orders from MongoDB
        raw_orders = await fetch_sales_orders_without_paginatiom(query)

        logger.debug(f"Raw orders fetched from DB: {raw_orders}")

        if not raw_orders:  
            logger.debug("No orders found based on the query.")

        # Serialize the fetched orders
        serialized_orders = [serialize_document_without_pagination(order) for order in raw_orders]
        logger.debug(f"Serialized orders: {serialized_orders}")

        # Return the serialized orders
        return serialized_orders

    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")



@router.patch("/{salesOrder_id}")
async def patch_salesOrder(salesOrder_id: str, salesOrder_patch: SalesOrderPost):
    # Await the find_one call
    try:
        existing_salesOrder = await get_salesOrder_collection().find_one({"_id": ObjectId(salesOrder_id)})
    except Exception as e:
        print(f"Error fetching sales order: {e}")
        raise HTTPException(status_code=500, detail="Database fetch error")

    if not existing_salesOrder:
        raise HTTPException(status_code=404, detail="salesOrder not found")

    # Convert Pydantic model to dict
    updated_fields = salesOrder_patch.dict(exclude_unset=True)

    # Convert deliveryDate if present
    if "deliveryDate" in updated_fields:
        delivery_date_str = updated_fields["deliveryDate"]
        if isinstance(delivery_date_str, str):
            updated_fields["deliveryDate"] = convert_to_date(delivery_date_str)

    # Update the document if there are changes
    if updated_fields:
        try:
            result = await get_salesOrder_collection().update_one(
                {"_id": ObjectId(salesOrder_id)},
                {"$set": updated_fields}
            )
            if result.modified_count == 0:
                # Could mean no fields changed
                print(f"No fields updated for salesOrder {salesOrder_id}")
        except Exception as e:
            print(f"Error updating salesOrder {salesOrder_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to update salesOrder")


    # Fetch and return the updated document
    updated_salesOrder = await get_salesOrder_collection().find_one({"_id": ObjectId(salesOrder_id)})
    updated_salesOrder["_id"] = str(updated_salesOrder["_id"])
    return updated_salesOrder


@router.delete("/{salesOrder_id}")
async def delete_salesOrder(salesOrder_id: str):
    result = get_salesOrder_collection().delete_one({"_id": ObjectId(salesOrder_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="salesOrder not found")
    return {"message": "salesOrder deleted successfully"}

@router.get("/filter-by-order-date-today/", response_model=List[SalesOrder])
async def filter_by_order_date_today():
    # Get the current date in dd-MM-yyyy format
    current_date = datetime.now().strftime("%d-%m-%Y")
    print(f"Current date for filtering: {current_date}")

    # Construct MongoDB query
    query = {"orderDate": {"$eq": current_date}}
    print(f"Query for filtering: {query}")

    # ✅ Use to_list() instead of list()
    salesOrders = await get_salesOrder_collection().find(query).to_list(length=None)
    print(f"Sales Orders fetched: {salesOrders}")

    if not salesOrders:
        print("No orders found for today.")
        raise HTTPException(status_code=404, detail="No orders found for today.")

    # Add salesOrderId and convert to response model
    result = []
    for salesOrder in salesOrders:
        salesOrder["salesOrderId"] = str(salesOrder["_id"])
        print(f"Processed Sales Order: {salesOrder}")
        result.append(SalesOrder(**salesOrder))

    return result

@router.get("/soadvancedtotalcash", response_model=List[SalesOrder])
async def get_sales_orders(
   
    orderDate: Optional[str] = None,
    paymentType: Optional[str] = None,
    minAdvanceAmount: Optional[float] = None,
):
    """
    Retrieve sales orders based on customerNumber, customerName, deliveryDate, orderDate,
    paymentType, and advanceAmount.
    
    """
    # Build the query dynamically based on the provided filters
    query = {}
    
    if orderDate:
        query["orderDate"] = orderDate
    if paymentType:
        query["paymentType"] = paymentType
    if minAdvanceAmount is not None:
        query["advanceAmount"] = {"$gt": minAdvanceAmount}  # Greater than specified advanceAmount

    # Log the query for debugging
    logging.info(f"Executing query: {query}")

    # Fetch sales orders matching the query
    salesOrders = await get_salesOrder_collection().find(query).to_list(length=None)

    if not salesOrders:
        raise HTTPException(status_code=404, detail="No sales orders found for the given criteria.")

    # Format the response
    formatted_salesOrders = [
        SalesOrder(**{**order, "salesOrderId": str(order["_id"])}) for order in salesOrders
    ]

    return formatted_salesOrders

@router.patch("/create_invoice/{salesOrder_id}")
async def create_invoice(salesOrder_id: str, body: dict):
    try:
        # Fetch the sales order
        sales_order_collection =   get_salesOrder_collection()
        sales_order = sales_order_collection.find_one({"_id": ObjectId(salesOrder_id)})

        if not sales_order:
            raise HTTPException(status_code=404, detail="Sales Order not found")

        # Extract data from the request body
        payment_type = body.get("paymentType", sales_order.get("paymentType", "Unknown"))
        status = body.get("status", "SalesOrder Completed")
        cash = body.get("cash", sales_order.get("cash", 0.0))
        card = body.get("card", sales_order.get("card", 0.0))                                   
        upi = body.get("upi", sales_order.get("upi", 0.0))

        # Map sales order data to invoice model
        invoice_data = Invoice(
            itemName=sales_order.get("itemName"),
            price=sales_order.get("price"),
            weight=sales_order.get("weight"),
            qty=sales_order.get("qty"),
            amount=sales_order.get("amount"),
            tax=sales_order.get("tax"),
            uom=sales_order.get("uom"),
            totalAmount=sales_order.get("totalAmount"),
            totalAmount2=sales_order.get("totalAmount2"),
            totalAmount3=sales_order.get("totalAmount"),
            status="Invoiced",
            salesType=sales_order.get("salesType"),
            customerPhoneNumber=sales_order.get("customerPhoneNumber", "No Number"),
            employeeName=sales_order.get("employeeName"),
            branchId=sales_order.get("branchId"),
            branchName=sales_order.get("branchName"),
            paymentType=payment_type,
            cash=cash,
            card=card,
            upi=upi,
            others=sales_order.get("others"),
            invoiceDate=datetime.now().strftime("%d-%m-%Y"),
            invoiceTime=datetime.now().strftime("%H:%M:%S"),
            shiftNumber=sales_order.get("shiftNumber"),
            shiftId=sales_order.get("shiftId"),
            invoiceNo="INV" + str(ObjectId()),  # Generate unique Invoice Number
            customCharge=sales_order.get("customCharge"),
            discountAmount=sales_order.get("discountAmount"),
            discountPercentage=sales_order.get("discountPercentage"),
            user=sales_order.get("user"),
        )

        # Insert the invoice data into the invoice collection
        invoice_collection = get_invoice_collection()
        invoice_result = invoice_collection.insert_one(invoice_data.dict())

        # Update the sales order with new status and additional details
        update_data = {
            "status": status,
            "invoiceDate": datetime.now().strftime("%d-%m-%Y"),
            "paymentType": payment_type,
            "cash": cash,
            "card": card,
            "upi": upi,
        }

        update_result = await sales_order_collection.update_one(
            {"_id": ObjectId(salesOrder_id)},
            {"$set": update_data}
        )

        if update_result.modified_count == 0:
            raise HTTPException(status_code=500, detail="Failed to update the sales order status")

        return {
            "message": "Sales Order status updated and Invoice created successfully",
            "invoiceId": str(invoice_result.inserted_id),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")    
    
    
    
@router.patch("/crsopreinvoice/")
async def patch_multiple_credit_sales_orders_pre_invoiced(salesOrder_ids: List[str]):
        """
        Updates multiple sales orders to set `creditCustomerOrder` to
        "credit sales order pre invoiced".

        Args:
            salesOrder_ids (List[str]): The list of sales order IDs to update.

        Returns:
            dict: The updated sales orders or an error message if not found.
        """
        try:
            updated_sales_orders = []
            for salesOrder_id in salesOrder_ids:
                # Validate and convert the salesOrder_id to ObjectId
                try:
                    object_id = ObjectId(salesOrder_id)
                except InvalidId as e:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid salesOrder_id: {e}"
                    )

                # Find the sales order by ID
                existing_sales_order =await  get_salesOrder_collection().find_one({"_id": object_id})
                if not existing_sales_order:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Sales order not found for ID: {salesOrder_id}"
                    )

                # Update the sales order
                update_data = {
                    "$set": {
                        "creditCustomerOrder": "credit sales order pre invoiced"
                    }
                }
                result =await  get_salesOrder_collection().update_one({"_id": object_id}, update_data)

                if result.modified_count == 0:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to update the sales order for ID: {salesOrder_id}"
                    )

                # Fetch the updated sales order
                updated_sales_order = await get_salesOrder_collection().find_one({"_id": object_id})
                updated_sales_order["_id"] = str(updated_sales_order["_id"])  # Convert ObjectId to string
                updated_sales_orders.append(updated_sales_order)

            return {
                "message": "Sales orders updated successfully",
                "salesOrders": updated_sales_orders
            }

        except Exception as e:
            logger.error(f"Error during update: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Internal Server Error")

@router.patch("/crsoinvoice/")
async def patch_multiple_credit_sales_orders_pre_invoiced(salesOrder_ids: List[str]):
        """
        Updates multiple sales orders to set `creditCustomerOrder` to
        "credit sales order pre invoiced".

        Args:
            salesOrder_ids (List[str]): The list of sales order IDs to update.

        Returns:
            dict: The updated sales orders or an error message if not found.
            
        """
        try:
            updated_sales_orders = []
            for salesOrder_id in salesOrder_ids:
                # Validate and convert the salesOrder_id to ObjectId
                try:
                    object_id = ObjectId(salesOrder_id)
                except InvalidId as e:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid salesOrder_id: {e}"
                    )

                # Find the sales order by ID
                existing_sales_order = get_salesOrder_collection().find_one({"_id": object_id})
                if not existing_sales_order:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Sales order not found for ID: {salesOrder_id}"
                    )

                # Update the sales order
                update_data = {
                    "$set": {
                        "creditCustomerOrder": "credit sales order invoiced"
                    }
                }
                result =await get_salesOrder_collection().update_one({"_id": object_id}, update_data)

                if result.modified_count == 0:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to update the sales order for ID: {salesOrder_id}"
                    )

                # Fetch the updated sales order
                updated_sales_order = get_salesOrder_collection().find_one({"_id": object_id})
                updated_sales_order["_id"] = str(updated_sales_order["_id"])  # Convert ObjectId to string
                updated_sales_orders.append(updated_sales_order)

            return {
                "message": "Sales orders updated successfully",
                "salesOrders": updated_sales_orders
            }

        except Exception as e:
            logger.error(f"Error during update: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Internal Server Error")    

@router.patch("/create_production_entry/{salesOrder_id}")
async def create_production_entry(salesOrder_id: str):
    try:
        # Get collections
        sales_order_collection = get_salesOrder_collection()
        production_entry_collection = get_productionEntry_collection()

        # Fetch the sales order (Motor is async → need await)
        sales_order = await sales_order_collection.find_one({"_id": ObjectId(salesOrder_id)})
        if not sales_order:
            raise HTTPException(status_code=404, detail="Sales Order not found")

        # Map sales order fields to Production Entry
        production_entry_data = {
            "saleOrderNo": sales_order.get("saleOrderNo"),   # ✅ link with sale order number
            "type": "sale order",                            # ✅ mark as sale order type
            "varianceName": sales_order.get("varianceName"),
            "uom": sales_order.get("uom"),
            "itemName": sales_order.get("itemName"),
            "price": sales_order.get("price"),
            "itemCode": sales_order.get("itemCode"),
            "weight": sales_order.get("weight"),
            "qty": sales_order.get("qty"),
            "amount": sales_order.get("amount"),
            "totalAmount": sales_order.get("totalAmount"),
            "date": get_iso_datetime(),                      # Auto-generate timestamp
        }

        # Insert into Production Entry collection
        production_result = await production_entry_collection.insert_one(production_entry_data)

        # Update Sales Order Status
        update_result = await sales_order_collection.update_one(
            {"_id": ObjectId(salesOrder_id)},
            {"$set": {"status": "ProductionEntry"}}
        )

        if update_result.modified_count == 0:
            raise HTTPException(status_code=500, detail="Failed to update sales order status")

        return {
            "message": "Production Entry created and Sales Order updated successfully",
            "productionEntryId": str(production_result.inserted_id),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")


@router.get("/warehouse/whordercount")
async def whordercount(
    status: Optional[str] = "Confirm Order",
    orderDate: Optional[str] = Query(None),
    deliveryStartDate: Optional[str] = Query(None),
    deliveryEndDate: Optional[str] = Query(None)
):
    """
    Fetch warehouse order count with total amounts, pending calculations, and optional date filters.
    """
    try:
        print("Received request to fetch warehouse order count.")
        logger.info("Received request to fetch warehouse order count.")

        # Determine date filters
        if orderDate:
            specific_date = datetime.strptime(orderDate, "%d-%m-%Y")
        else:
            specific_date = datetime.now()

        if deliveryStartDate and deliveryEndDate:
            start_date = datetime.strptime(deliveryStartDate, "%d-%m-%Y")
            end_date = datetime.strptime(deliveryEndDate, "%d-%m-%Y")
            end_date = end_date.replace(hour=23, minute=59, second=59)
            date_filter = {"$gte": start_date, "$lte": end_date}
        else:
            date_filter = {
                "$gte": specific_date.replace(hour=0, minute=0, second=0),
                "$lte": specific_date.replace(hour=23, minute=59, second=59),
            }

        # Fetch orders with statuses: "Confirm Order", "Printed", "Production Entry", "dispatched"
        status_query = {
            "status": {"$regex": "^(Confirm Order|Printed|ProductionEntry|dispatched)$", "$options": "i"},
            "deliveryDate": date_filter,
        }
        all_status_orders = await fetch_sales_orders_without_paginatiom(status_query)

        total_orders = len(all_status_orders)
        total_amount = sum(
            order.get("totalAmount", 0) if isinstance(order.get("totalAmount", 0), (int, float)) else 0
            for order in all_status_orders
        )

        # Fetch dispatched orders
        dispatch_query = {
            "status": {"$regex": "^dispatched$", "$options": "i"},
            "deliveryDate": date_filter,
        }
        dispatched_orders = await fetch_sales_orders_without_paginatiom(dispatch_query)

        total_dispatch = len(dispatched_orders)
        total_dispatch_amount = sum(
            order.get("totalAmount", 0) if isinstance(order.get("totalAmount", 0), (int, float)) else 0
            for order in dispatched_orders
        )

        # Fetch "Printed" orders
        printed_query = {
            "status": {"$regex": "^Printed$", "$options": "i"},
            "deliveryDate": date_filter,
        }
        printed_orders = await fetch_sales_orders_without_paginatiom(printed_query)
        printed_amount = sum(
            order.get("totalAmount", 0) if isinstance(order.get("totalAmount", 0), (int, float)) else 0
            for order in printed_orders
        )

        # Fetch "Production Entry" orders
        production_query = {
            "status": {"$regex": "^ProductionEntry$", "$options": "i"},
            "deliveryDate": date_filter,
        }
        production_orders = await fetch_sales_orders_without_paginatiom(production_query)
        production_amount = sum(
            order.get("totalAmount", 0) if isinstance(order.get("totalAmount", 0), (int, float)) else 0
            for order in production_orders
        )

        # Fetch "Confirm Order" orders separately
        confirm_order_query = {
            "status": {"$regex": "^Confirm Order$", "$options": "i"},
            "deliveryDate": date_filter,
        }
        confirm_orders = await fetch_sales_orders_without_paginatiom(confirm_order_query)
        confirm_order_amount = sum(
            order.get("totalAmount", 0) if isinstance(order.get("totalAmount", 0), (int, float)) else 0
            for order in confirm_orders
        )

        # Calculate pending orders and amount
        pending_orders = max(total_orders - total_dispatch, 0)
        pending_amount = max(total_amount - total_dispatch_amount, 0)

        # Return response
        response = {
            "total_orders": total_orders,
            "total_amount": total_amount,
            "total_dispatch": total_dispatch,
            "total_dispatch_amount": total_dispatch_amount,
            "printed_orders": len(printed_orders),
            "printed_amount": printed_amount,
            "production_entry_orders": len(production_orders),
            "production_entry_amount": production_amount,
            "confirm_orders": len(confirm_orders),
            "confirm_order_amount": confirm_order_amount,
            "pending_orders": pending_orders,
            "pending_amount": pending_amount
        }

        return response

    except Exception as e:
        logger.error(f"An error occurred in whordercount: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/count/")
async def get_filtered_order_count(
    approvalStatus: Optional[str] = None,
    approvalType: Optional[str] = None,
):
    """
    Get the count of sales orders based on essential filters.
    Returns discount, cancellation, and modified counts.
    """
    try:
        # Initialize counts
        discount_count = 0
        cancel_order_count = 0
        modified_count = 0

        # Discount count query
        discount_query = {
            "approvalDetails.approvalType": {"$regex": "^Discount$", "$options": "i"},
            "status": {"$regex": "^Waiting for Approval$", "$options": "i"}
        }        
        print(f"Discount Query: {discount_query}")
        discount_count = get_holdOrder_collection().count_documents(discount_query)
        print(f"Discount Count: {discount_count}")

        # Cancel order count query
        cancel_query = {
            "approvalDetails.approvalType": {"$regex": "^Cancel Order$", "$options": "i"},
            "status": {"$regex": "^Waiting for Approval$", "$options": "i"}
        }
        print(f"Cancel Order Query: {cancel_query}")
        cancel_order_count = get_salesOrder_collection().count_documents(cancel_query)
        print(f"Cancel Order Count: {cancel_order_count}")

        # Modified count query
        modified_query = {
            "status": {"$regex": "^Modified$", "$options": "i"}
        }
        modified_orders = get_salesOrder_collection().find(modified_query)
        for order in modified_orders:
            sale_order_no = order.get("saleOrderNo")
            previous_id = order.get("_id")  # Get the current order's ID
            
            # Check if there is a matching record in toApprove collection
            to_approve_query = {
                "previous_id": previous_id,
                "saleOrderNo": sale_order_no
            }
            print(f"Modified Query: {to_approve_query}")
            count = get_toApprove_collection().count_documents(to_approve_query)
            modified_count += count
            print(f"Modified Count: {modified_count}")

        # Return the counts as a response
        return {
            "discount_count": discount_count,
            "cancel_order_count": cancel_order_count,
            "modified_count": modified_count
        }

    except Exception as e:
        logger.error(f"Error while fetching order count: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.patch("/patchapproval/{salesOrder_id}")
async def patch_salesOrder(salesOrder_id: str, salesOrder_patch: SalesOrderPost):
    existing_salesOrder = get_salesOrder_collection().find_one({"_id": ObjectId(salesOrder_id)})
    if not existing_salesOrder:
        raise HTTPException(status_code=404, detail="salesOrder not found")

    # Convert the Pydantic model to a dictionary, excluding unset values
    updated_fields = salesOrder_patch.dict(exclude_unset=True)

    # Check if 'deliveryDate' exists and is in the correct format
    if "deliveryDate" in updated_fields:
        delivery_date_str = updated_fields["deliveryDate"]
        if isinstance(delivery_date_str, str):
            updated_fields["deliveryDate"] = convert_to_date(delivery_date_str)

    # Update only the last approval detail if it exists
    if "approvalDetails" in updated_fields:
        new_approval = updated_fields["approvalDetails"][0]
        existing_approvals = existing_salesOrder.get("approvalDetails", [])

        if existing_approvals:
            # Update the last approval detail in the list
            existing_approvals[-1].update(new_approval)
            updated_fields["approvalDetails"] = existing_approvals
        else:
            # If no existing approvals, just add the new one
            updated_fields["approvalDetails"] = [new_approval]

    # Update the document if there are changes
    if updated_fields:
        result =await  get_salesOrder_collection().update_one(
            {"_id": ObjectId(salesOrder_id)},
            {"$set": updated_fields}
        )
        if result.modified_count == 0:
            raise HTTPException(status_code=500, detail="Failed to update salesOrder")

    # Fetch and return the updated sales order
    updated_salesOrder = get_salesOrder_collection().find_one({"_id": ObjectId(salesOrder_id)})
    updated_salesOrder["_id"] = str(updated_salesOrder["_id"])
    return updated_salesOrder
@router.get("/salesorders/", response_model=List[SalesOrderResponse])
async def get_sales_orders(
    startDate: Optional[str] = Query(None),
    endDate: Optional[str] = Query(None),
    specificDate: Optional[str] = Query(None),
    saleOrderNo: Optional[str] = Query(None),
    branchName: Optional[str] = Query(None),
    receivedStatus: Optional[str] = Query(None)
):
    """
    Fetch sales orders with optional filters: date range, specific date, sale order number, and branch name.
    Default is today's date if no date is provided.
    """
    try:
        # Set default date to today if no date is provided
        if not (startDate or endDate or specificDate or saleOrderNo or branchName):
            today = datetime.now().strftime("%d-%m-%Y")
            startDate = endDate = today

        query = {}

        # Apply sale order number filter if provided
        if saleOrderNo:
            query["saleOrderNo"] = saleOrderNo

        # Apply branch name filter if provided
        if branchName:
            query["branchName"] = branchName

        # Apply received status filter
        if receivedStatus == "received":
            query["eventDate"] = {"$ne": None}
        elif receivedStatus == "not_received":
            query["eventDate"] = None

        # Parse date filters
        if startDate and endDate:
            start_date = datetime.strptime(startDate, "%d-%m-%Y")
            end_date = datetime.strptime(endDate, "%d-%m-%Y").replace(hour=23, minute=59, second=59)
            query["deliveryDate"] = {"$gte": start_date, "$lte": end_date}
        elif specificDate:
            date = datetime.strptime(specificDate, "%d-%m-%Y")
            query["deliveryDate"] = date

        logger.info(f"Fetching sales orders with query: {query}")

        # ✅ Use Motor async to fetch data
        cursor = get_salesOrder_collection().find(query, {
            "_id": 0,
            "saleOrderNo": 1,
            "customerName": 1,
            "orderDate": 1,
            "deliveryDate": 1,
            "branchName": 1,
            "receivedTime": 1,
            "invoiceTime": 1,
            "varianceName": 1,
            "qty": 1,
            "price": 1,
            "weight": 1,
            "amount": 1,
            "uom": 1,
            "totalAmount": 1
        })
        sales_orders = await cursor.to_list(length=None)

        if not sales_orders:
            return []

        for order in sales_orders:
            sale_order_no = order["saleOrderNo"]

            # ✅ Fetch production time only if type == "sale order"
            production_entry = await get_productionEntry_collection().find_one(
                {"saleOrderNo": sale_order_no, "type": "sale order"},
                {"_id": 0, "date": 1, "type": 1}
            )
            if production_entry and "date" in production_entry:
                prod_date = production_entry["date"]
                if isinstance(prod_date, str):
                    try:
                        prod_date = datetime.fromisoformat(prod_date)
                    except Exception:
                        pass
                order["productionTime"] = prod_date
            else:
                order["productionTime"] = None

            # Fetch dispatch time
            dispatch_entry = await get_dispatch_collection().find_one(
                {"saleOrderNo": sale_order_no}, {"_id": 0, "date": 1}
            )
            order["dispatchTime"] = dispatch_entry["date"] if dispatch_entry else None

            # Fetch received & invoice times
            sale_order_details = await get_salesOrder_collection().find_one(
                {"saleOrderNo": sale_order_no}, {"_id": 0, "eventDate": 1, "invoiceDate": 1}
            )
            order["receivedTime"] = sale_order_details.get("eventDate") if sale_order_details else None
            order["invoiceTime"] = sale_order_details.get("invoiceDate") if sale_order_details else None

        return sales_orders

    except Exception as e:
        logger.error(f"Error fetching sales orders: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")
@router.patch("/by-saleorderno/{saleOrderNo}")
async def patch_salesOrder_by_saleOrderNo(saleOrderNo: str, salesOrder_patch: SalesOrderPost):
    request_id = str(uuid.uuid4())
    log_extra = {"request_id": request_id}

    logger.info(f"Received PATCH request for saleOrderNo: {saleOrderNo}, payload: {salesOrder_patch.dict()}", extra=log_extra)

    try:
        existing_salesOrder = await get_salesOrder_collection().find_one({"saleOrderNo": saleOrderNo})
        if not existing_salesOrder:
            raise HTTPException(status_code=404, detail=f"Sales order with saleOrderNo {saleOrderNo} not found")

        # Only include fields that are set and not None
        updated_fields = {k: v for k, v in salesOrder_patch.dict(exclude_unset=True).items() if v is not None}

        if updated_fields:
            result = await get_salesOrder_collection().update_one(
                {"saleOrderNo": saleOrderNo},
                {"$set": updated_fields}
            )
            if result.matched_count == 0:
                raise HTTPException(status_code=500, detail="Failed to update sales order: No matching document found")
            updated_salesOrder = await get_salesOrder_collection().find_one({"saleOrderNo": saleOrderNo})
        else:
            updated_salesOrder = existing_salesOrder

        updated_salesOrder["_id"] = str(updated_salesOrder["_id"])
        return updated_salesOrder

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error processing saleOrderNo: {saleOrderNo}: {str(e)}", extra=log_extra)
        raise HTTPException(status_code=500, detail=f"Internal server error processing saleOrderNo {saleOrderNo}")

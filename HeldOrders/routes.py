
from io import BytesIO
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Path, Query, logger
from bson import ObjectId
from .models import  SalesOrder, SalesOrderPost
from .utils import  get_counter_collection, get_holdOrder_collection
import logging
from datetime import datetime, timedelta
from bson.errors import InvalidId
from fastapi import Query
from math import ceil

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
   
    try:
        # Get the collection
        collection = get_holdOrder_collection()

        # Execute the query
        logger.debug(f"Executing MongoDB query: {query}")
        results = list(collection.find(query))

        logger.info(f"Retrieved {len(results)} records from MongoDB.")
        return results
    except Exception as e:
        logger.error(f"Error querying MongoDB: {e}", exc_info=True)
        raise    


def fetch_sales_orders_try(query: dict) -> List[dict]:
   
    try:
        # Get the collection
        collection = get_holdOrder_collection()

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
    
def get_next_sequence(prefix: str) -> str:

    counters_collection = get_counter_collection()  # A function to get the counters collection
    try:
        # Find the counter for the prefix and increment it atomically
        result = counters_collection.find_one_and_update(
            {"prefix": prefix},
            {"$inc": {"sequence": 1}},
            upsert=True,  # Create a new document if it doesn't exist
            return_document=True
        )
        sequence = result["sequence"]
        # Format the sequence as a zero-padded number
        return f"{prefix}{str(sequence).zfill(4)}"
    except Exception as e:
        logger.error(f"Error generating sequence for prefix {prefix}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate sales order number")


# @router.post("/", response_model=str)
# async def create_salesOrder(payload: dict):
#     try:
#         # Extract sales order data
#         salesOrderData = payload.get("data", [])

#         if not salesOrderData:
#             raise HTTPException(status_code=400, detail="Missing sales order data")

#         salesOrder = SalesOrderPost(**salesOrderData[0])

#         # Ensure saleOrderNo is valid
#         if not salesOrder.saleOrderNo or not salesOrder.saleOrderNo.strip():
#             raise HTTPException(status_code=400, detail="Prefix is required for sales order.")

#         # Generate new sales order number
#         sales_order_no = get_next_sequence(salesOrder.saleOrderNo)
#         delivery_date = convert_to_date(salesOrder.deliveryDate)

#         # Prepare sales order data
#         new_salesOrder_data = { 
#             **salesOrder.dict(),
#             "saleOrderNo": sales_order_no,
#             "deliveryDate": delivery_date,
#         }

#         if hasattr(salesOrder, "eventDate") and salesOrder.eventDate:
#             new_salesOrder_data["eventDate"] = convert_to_date(salesOrder.eventDate)

#         # Insert into MongoDB
#         result = get_holdOrder_collection().insert_one(new_salesOrder_data)
#         inserted_id = str(result.inserted_id)

#         print(f"Sales order created with ID: {inserted_id} and Sales Order No: {sales_order_no}")

        
#         return inserted_id

#     except Exception as e:
#         print(f"Error creating sales order: {e}")
#         raise HTTPException(status_code=500, detail="Failed to create sales order")


@router.post("/", response_model=str)
async def create_salesOrder(payload: dict):
    try:
        # Extract data from nested lists under the "data" key
        post_data = payload.get("data", payload)  # Use entire payload if "data" is missing
        
        # Unwrap nested lists until we get a dictionary
        while isinstance(post_data, list) and len(post_data) > 0:
            post_data = post_data[0]
        
        # Ensure the final data is a dictionary
        if not isinstance(post_data, dict):
            raise HTTPException(status_code=400, detail="Data must be a JSON object")
        
        # Process deliveryDate if needed (example)
        if "deliveryDate" in post_data and post_data["deliveryDate"]:
            post_data["deliveryDate"] = convert_to_date(post_data["deliveryDate"])
        
        # Insert into MongoDB
        result = get_holdOrder_collection().insert_one(post_data)
        print(f"Inserted document ID: {result.inserted_id}")
        return str(result.inserted_id)
    
    except HTTPException as he:
        raise he  # Re-raise HTTP exceptions
    except Exception as e:
        print(f"Server error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    

# @router.get("/")
# async def get_sales_orders(
#     deliveryStartDate: Optional[str] = Query(None),
#     deliveryEndDate: Optional[str] = Query(None),
#     deliveryDate: Optional[str] = Query(None),
#     customerNumber: Optional[str] = None,
#     customerName: Optional[str] = None,
#     saleOrderNo: Optional[str] = None,
#     orderDate: Optional[str] = None,
#     paymentType: Optional[str] = None,
#     minAdvanceAmount: Optional[float] = None,
#     salesOrderLast5Digits: Optional[str] = None,
#     status: Optional[str] = None,
#     branchName: Optional[str] = None,
#     filterCreditCustomer: Optional[bool] = Query(False, alias="filter-credit-customer"),
#     filterCreditCustomerPreinvoice: Optional[bool] = Query(False, alias="filter-credit-customer-preinvoice"),
#     approvalStatus: Optional[str] = None,
#     approvalType: Optional[str] = None,
#     summary: Optional[str] = None,
#     approvalDate: Optional[str] = Query(None),
#     approvalStartDate: Optional[str] = Query(None),
#     approvalEndDate: Optional[str] = Query(None)
# ):
#     """
#     Fetch sales orders based on query parameters without pagination.
#     """
#     try:
#         logger.info("Received request to fetch sales orders without pagination.")
#         query = {}
#         approval_filter = {}

#         # Delivery date filters
#         if deliveryStartDate and deliveryEndDate:
#             start_date = datetime.strptime(deliveryStartDate, "%d-%m-%Y")
#             end_date = datetime.strptime(deliveryEndDate, "%d-%m-%Y")
#             end_date = end_date.replace(hour=23, minute=59, second=59)
#             query["deliveryDate"] = {"$gte": start_date, "$lte": end_date}
#         elif deliveryDate:
#             specific_date = datetime.strptime(deliveryDate, "%d-%m-%Y")
#             query["deliveryDate"] = specific_date

#         # Approval filters
#         if approvalStatus:
#             approval_filter["approvalStatus"] = {"$regex": f"^{approvalStatus}$", "$options": "i"}
#         if approvalType:
#             approval_filter["approvalType"] = {"$regex": f"^{approvalType}$", "$options": "i"}
#         if summary:
#             approval_filter["summary"] = {"$regex": f"^{summary}$", "$options": "i"}

#         if approvalStartDate and approvalEndDate:
#             start_date = datetime.strptime(approvalStartDate, "%d-%m-%Y")
#             end_date = datetime.strptime(approvalEndDate, "%d-%m-%Y")
#             end_date = end_date.replace(hour=23, minute=59, second=59)
#             approval_filter["approvalDate"] = {"$gte": start_date, "$lte": end_date}
#         elif approvalStartDate:
#             start_date = datetime.strptime(approvalStartDate, "%d-%m-%Y")
#             approval_filter["approvalDate"] = {"$gte": start_date}
#         elif approvalEndDate:
#             end_date = datetime.strptime(approvalEndDate, "%d-%m-%Y")
#             end_date = end_date.replace(hour=23, minute=59, second=59)
#             approval_filter["approvalDate"] = {"$lte": end_date}

#         if approvalDate:
#             approval_date = datetime.strptime(approvalDate, "%d-%m-%Y")
#             approval_filter["approvalDate"] = approval_date

#         if approval_filter:
#             query["approvalDetails"] = {"$elemMatch": approval_filter}

#         # Customer filters
#         if customerName:
#             query["customerName"] = {"$regex": customerName, "$options": "i"}
#         if customerNumber:
#             query["customerNumber"] = {"$regex": customerNumber, "$options": "i"}
#         if status:
#             query["status"] = {"$regex": f"^{status}$", "$options": "i"}
#         if branchName:
#             query["branchName"] = {"$regex": branchName, "$options": "i"}

#         # Sales order number filters
#         if salesOrderLast5Digits:
#             query["salesOrderId"] = {"$regex": f"{salesOrderLast5Digits}$", "$options": "i"}
#         if saleOrderNo:
#             if len(saleOrderNo) == 5 and saleOrderNo.isdigit():
#                 query["saleOrderNo"] = {"$regex": f"{saleOrderNo}$", "$options": "i"}
#             else:
#                 query["saleOrderNo"] = {"$regex": saleOrderNo, "$options": "i"}

#         # Payment and advance amount filters
#         if paymentType:
#             query["paymentType"] = {"$regex": paymentType, "$options": "i"}
#         if minAdvanceAmount is not None:
#             query["advanceAmount"] = {"$gte": minAdvanceAmount}

#         # Credit customer filters
#         if filterCreditCustomer:
#             query["creditCustomerOrder"] = "yes"
#         if filterCreditCustomerPreinvoice:
#             query["creditCustomerOrder"] = "credit sales order pre invoiced"

                    

#         logger.debug(f"Final query: {query}")

#         # Fetch sales orders from the database
#         raw_orders = fetch_sales_orders(query)
#         serialized_orders = [serialize_document_forget(order) for order in raw_orders]

#         # return {"data": serialized_orders}
#         return  serialized_orders

#     except Exception as e:
#         logger.error(f"An error occurred: {e}", exc_info=True)
#         raise HTTPException(status_code=500, detail="Internal Server Error")

# @router.get("/")
# async def get_sales_orders(
#     deliveryStartDate: Optional[str] = Query(None),
#     deliveryEndDate: Optional[str] = Query(None),
#     deliveryDate: Optional[str] = Query(None),
#     customerNumber: Optional[str] = None,
#     customerName: Optional[str] = None,
#     saleOrderNo: Optional[str] = None,
#     orderDate: Optional[str] = None,
#     paymentType: Optional[str] = None,
#     minAdvanceAmount: Optional[float] = None,
#     salesOrderLast5Digits: Optional[str] = None,
#     salesOrderIdLast5Digits: Optional[str] = None,  # ✅ NEW PARAM
#     status: Optional[str] = None,
#     branchName: Optional[str] = None,
#     filterCreditCustomer: Optional[bool] = Query(False, alias="filter-credit-customer"),
#     filterCreditCustomerPreinvoice: Optional[bool] = Query(False, alias="filter-credit-customer-preinvoice"),
#     approvalStatus: Optional[str] = None,
#     approvalType: Optional[str] = None,
#     summary: Optional[str] = None,
#     approvalDate: Optional[str] = Query(None),
#     approvalStartDate: Optional[str] = Query(None),
#     approvalEndDate: Optional[str] = Query(None)
# ):
#     """
#     Fetch sales orders based on query parameters without pagination.
#     """
#     try:
#         logger.info("Received request to fetch sales orders without pagination.")
#         query = {}
#         approval_filter = {}

#         # Delivery date filters
#         if deliveryStartDate and deliveryEndDate:
#             start_date = datetime.strptime(deliveryStartDate, "%d-%m-%Y")
#             end_date = datetime.strptime(deliveryEndDate, "%d-%m-%Y")
#             end_date = end_date.replace(hour=23, minute=59, second=59)
#             query["deliveryDate"] = {"$gte": start_date, "$lte": end_date}
#         elif deliveryDate:
#             specific_date = datetime.strptime(deliveryDate, "%d-%m-%Y")
#             query["deliveryDate"] = specific_date

#         # Approval filters
#         if approvalStatus:
#             approval_filter["approvalStatus"] = {"$regex": f"^{approvalStatus}$", "$options": "i"}
#         if approvalType:
#             approval_filter["approvalType"] = {"$regex": f"^{approvalType}$", "$options": "i"}
#         if summary:
#             approval_filter["summary"] = {"$regex": f"^{summary}$", "$options": "i"}

#         if approvalStartDate and approvalEndDate:
#             start_date = datetime.strptime(approvalStartDate, "%d-%m-%Y")
#             end_date = datetime.strptime(approvalEndDate, "%d-%m-%Y")
#             end_date = end_date.replace(hour=23, minute=59, second=59)
#             approval_filter["approvalDate"] = {"$gte": start_date, "$lte": end_date}
#         elif approvalStartDate:
#             start_date = datetime.strptime(approvalStartDate, "%d-%m-%Y")
#             approval_filter["approvalDate"] = {"$gte": start_date}
#         elif approvalEndDate:
#             end_date = datetime.strptime(approvalEndDate, "%d-%m-%Y")
#             end_date = end_date.replace(hour=23, minute=59, second=59)
#             approval_filter["approvalDate"] = {"$lte": end_date}

#         if approvalDate:
#             approval_date = datetime.strptime(approvalDate, "%d-%m-%Y")
#             approval_filter["approvalDate"] = approval_date

#         if approval_filter:
#             query["approvalDetails"] = {"$elemMatch": approval_filter}

#         # Customer filters
#         if customerName:
#             query["customerName"] = {"$regex": customerName, "$options": "i"}
#         if customerNumber:
#             query["customerNumber"] = {"$regex": customerNumber, "$options": "i"}
#         if status:
#             query["status"] = {"$regex": f"^{status}$", "$options": "i"}
#         if branchName:
#             query["branchName"] = {"$regex": branchName, "$options": "i"}

#         # Sales order number filters
#         if salesOrderLast5Digits:
#             query["salesOrderId"] = {"$regex": f"{salesOrderLast5Digits}$", "$options": "i"}
#         if saleOrderNo:
#             if len(saleOrderNo) == 5 and saleOrderNo.isdigit():
#                 query["saleOrderNo"] = {"$regex": f"{saleOrderNo}$", "$options": "i"}
#             else:
#                 query["saleOrderNo"] = {"$regex": saleOrderNo, "$options": "i"}

#         # Payment and advance amount filters
#         if paymentType:
#             query["paymentType"] = {"$regex": paymentType, "$options": "i"}
#         if minAdvanceAmount is not None:
#             query["advanceAmount"] = {"$gte": minAdvanceAmount}

#         # Credit customer filters
#         if filterCreditCustomer:
#             query["creditCustomerOrder"] = "yes"
#         if filterCreditCustomerPreinvoice:
#             query["creditCustomerOrder"] = "credit sales order pre invoiced"

#         logger.debug(f"Final query: {query}")

#         # Fetch sales orders from the database
#         raw_orders = fetch_sales_orders(query)

#         # ✅ Post-filter by ObjectId last 5 characters
#         if salesOrderIdLast5Digits:
#             salesOrderIdLast5Digits = salesOrderIdLast5Digits.lower()
#             raw_orders = [
#                 order for order in raw_orders
#                 if str(order["_id"])[-5:].lower() == salesOrderIdLast5Digits
#             ]

#         serialized_orders = [serialize_document_forget(order) for order in raw_orders]

#         return serialized_orders

#     except Exception as e:
#         logger.error(f"An error occurred: {e}", exc_info=True)
#         raise HTTPException(status_code=500, detail="Internal Server Error")



# def fetch_sales_orders_without_paginatiom(query):
#     collection = get_holdOrder_collection()
    
#     return list(collection.find(query))


# def serialize_document(doc):
#     """Convert MongoDB document to JSON serializable format"""
#     if isinstance(doc, ObjectId):
#         return str(doc)
#     if isinstance(doc, dict):
#         return {k: serialize_document(v) for k, v in doc.items()}
#     if isinstance(doc, list):
#         return [serialize_document(i) for i in doc]
#     return doc

@router.get("/approvals/paginated")
async def get_sales_orders_with_approvals_paginated(
    approvalStartDate: str = Query(..., description="Start date in dd-MM-yyyy"),
    approvalEndDate: str = Query(..., description="End date in dd-MM-yyyy"),
    approvalType: Optional[str] = Query(None, description="Type of approval (optional)"),
    saleOrderNo: Optional[str] = Query(None, description="Filter by sale order number"),
    customerNumber: Optional[str] = Query(None, description="Filter by customer number"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Number of records per page"),
    summary: str = Query("yes", description="Include summary yes/no"),
):
    """
    Fetch paginated sales orders filtered by approval date range,
    approvalType, saleOrderNo, customerNumber.
    Returns pagination + data + optional summary.
    """
    try:
        # Convert approval date range
        start_date = datetime.strptime(approvalStartDate, "%d-%m-%Y")
        end_date = datetime.strptime(approvalEndDate, "%d-%m-%Y")
        end_date = end_date.replace(hour=23, minute=59, second=59)

        # Build approval filter
        approval_filter = {
            "approvalDate": {"$gte": start_date, "$lte": end_date},
        }
        if approvalType:
            approval_filter["approvalType"] = {
                "$regex": f"^{approvalType}$",
                "$options": "i"
            }

        # Main query with approvalDetails
        query: dict = {"approvalDetails": {"$elemMatch": approval_filter}}

        # ✅ SaleOrderNo filter
        if saleOrderNo:
            query["saleOrderNo"] = {"$regex": saleOrderNo, "$options": "i"}

        # ✅ CustomerNumber filter
        if customerNumber:
            query["customerNumber"] = {"$regex": customerNumber, "$options": "i"}

        collection = get_holdOrder_collection()

        # Count
        total_records = collection.count_documents(query)
        total_pages = ceil(total_records / limit) if total_records > 0 else 1

        # Fetch paginated orders
        raw_orders = list(
            collection.find(query)
            .skip((page - 1) * limit)
            .limit(limit)
        )
        serialized_orders = [serialize_document_without_pagination(order) for order in raw_orders]

        # Summary (optional)
        summary_data = []
        if summary.lower() == "yes":
            summary_pipeline = [
                {"$unwind": "$approvalDetails"},
                {"$match": approval_filter},
                {
                    "$group": {
                        "_id": "$approvalDetails.approvalType",
                        "count": {"$sum": 1}
                    }
                },
                {"$project": {"approvalType": "$_id", "count": 1, "_id": 0}},
            ]
            summary_data = list(collection.aggregate(summary_pipeline))

        return {
            "pagination": {
                "page": page,
                "limit": limit,
                "total_records": total_records,
                "total_pages": total_pages,
            },
            "data": serialized_orders,
            "summary": summary_data,
        }

    except Exception as e:
        logger.error(f"Error in paginated approval query: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


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
    salesOrderIdLast5Digits: Optional[str] = None,
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
    chequeNumber: Optional[str] = None,  # ✅ NEW PARAM for cheque number
    eventDate: Optional[str] = None,  # ✅ NEW PARAM
    deliveryBranchName: Optional[str] = None,  # ✅ NEW PARAM
    isBoxItem: Optional[List[str]] = None,  # ✅ NEW PARAM
    totalBoxQty: Optional[List[float]] = None,  # ✅ NEW PARAM
    holdOrderNo: Optional[str] = None,  # ✅ NEW PARAM
):
    """
    Fetch sales orders based on query parameters without pagination.
    """
    try:
        logger.info("Received request to fetch sales orders without pagination.")
        query = {}
        approval_filter = {}
        cheque_filter = {}  # ✅ NEW: Filter for chequeDetails

        # Delivery date filters
        if deliveryStartDate and deliveryEndDate:
            start_date = datetime.strptime(deliveryStartDate, "%d-%m-%Y")
            end_date = datetime.strptime(deliveryEndDate, "%d-%m-%Y")
            end_date = end_date.replace(hour=23, minute=59, second=59)
            query["deliveryDate"] = {"$gte": start_date, "$lte": end_date}
        elif deliveryDate:
            specific_date = datetime.strptime(deliveryDate, "%d-%m-%Y")
            query["deliveryDate"] = specific_date

        # Approval filters
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

        # ✅ Cheque number filter
        if chequeNumber:
            cheque_filter["chequeNumber"] = {"$regex": f"^{chequeNumber}$", "$options": "i"}
            query["chequeDetails"] = {"$elemMatch": cheque_filter}

        # Customer filters
        if customerName:
            query["customerName"] = {"$regex": customerName, "$options": "i"}
        if customerNumber:
            query["customerNumber"] = {"$regex": customerNumber, "$options": "i"}
        if status:
            query["status"] = {"$regex": f"^{status}$", "$options": "i"}
        if branchName:
            query["branchName"] = {"$regex": branchName, "$options": "i"}

        # Sales order number filters
        if salesOrderLast5Digits:
            query["salesOrderId"] = {"$regex": f"{salesOrderLast5Digits}$", "$options": "i"}
        if saleOrderNo:
            if len(saleOrderNo) == 5 and saleOrderNo.isdigit():
                query["saleOrderNo"] = {"$regex": f"{saleOrderNo}$", "$options": "i"}
            else:
                query["saleOrderNo"] = {"$regex": saleOrderNo, "$options": "i"}

        # Payment and advance amount filters
        if paymentType:
            query["paymentType"] = {"$regex": paymentType, "$options": "i"}
        if minAdvanceAmount is not None:
            query["advanceAmount"] = {"$gte": minAdvanceAmount}

        # Credit customer filters
        if filterCreditCustomer:
            query["creditCustomerOrder"] = "yes"
        if filterCreditCustomerPreinvoice:
            query["creditCustomerOrder"] = "credit sales order pre invoiced"

        # ✅ Event date filter
        if eventDate:
            event_date = datetime.strptime(eventDate, "%d-%m-%Y")
            query["eventDate"] = event_date

        # ✅ Delivery branch name filter
        if deliveryBranchName:
            query["deliveryBranchName"] = {"$regex": deliveryBranchName, "$options": "i"}

        # ✅ isBoxItem filter
        if isBoxItem:
            query["isBoxItem"] = {"$in": isBoxItem}

        # ✅ totalBoxQty filter
        if totalBoxQty:
            query["totalBoxQty"] = {"$in": totalBoxQty}

        # ✅ holdOrderNo filter
        if holdOrderNo:
            query["holdOrderNo"] = {"$regex": f"^{holdOrderNo}$", "$options": "i"}

        logger.debug(f"Final query: {query}")

        # Fetch sales orders from the database
        raw_orders = fetch_sales_orders(query)

        # Post-filter by ObjectId last 5 characters
        if salesOrderIdLast5Digits:
            salesOrderIdLast5Digits = salesOrderIdLast5Digits.lower()
            raw_orders = [
                order for order in raw_orders
                if str(order["_id"])[-5:].lower() == salesOrderIdLast5Digits
            ]

        serialized_orders = [serialize_document_forget(order) for order in raw_orders]

        return serialized_orders

    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/{salesOrder_id}", response_model=SalesOrder)
async def get_salesOrder_by_id(salesOrder_id: str):
    salesOrder = get_holdOrder_collection().find_one({"_id": ObjectId(salesOrder_id)})
    if salesOrder:
        salesOrder["salesOrderId"] = str(salesOrder["_id"])
        return SalesOrder(**salesOrder)
    else:
        raise HTTPException(status_code=404, detail="SalesOrder not found")


@router.patch("/{salesOrder_id}")
async def patch_salesOrder(salesOrder_id: str, salesOrder_patch: SalesOrderPost):
    existing_salesOrder = get_holdOrder_collection().find_one({"_id": ObjectId(salesOrder_id)})
    if not existing_salesOrder:
        raise HTTPException(status_code=404, detail="salesOrder not found")

    # Convert the Pydantic model to a dictionary, excluding unset values
    updated_fields = salesOrder_patch.dict(exclude_unset=True)

    # Check if 'deliveryDate' exists and is in the correct format
    if "deliveryDate" in updated_fields:
        delivery_date_str = updated_fields["deliveryDate"]
        if isinstance(delivery_date_str, str):  # Ensure it's a string before converting
            updated_fields["deliveryDate"] = convert_to_date(delivery_date_str)

    # Update the document if there are changes
    if updated_fields:
        result = get_holdOrder_collection().update_one(
            {"_id": ObjectId(salesOrder_id)}, 
            {"$set": updated_fields}
        )
        if result.modified_count == 0:
            raise HTTPException(status_code=500, detail="Failed to update salesOrder")

    # Fetch and return the updated sales order
    updated_salesOrder = get_holdOrder_collection().find_one({"_id": ObjectId(salesOrder_id)})
    updated_salesOrder["_id"] = str(updated_salesOrder["_id"])
    return updated_salesOrder

@router.delete("/{salesOrder_id}")
async def delete_salesOrder(salesOrder_id: str):
    result = get_holdOrder_collection().delete_one({"_id": ObjectId(salesOrder_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="salesOrder not found")
    return {"message": "salesOrder deleted successfully"}



@router.patch("/patchapproval/{salesOrder_id}")
async def patch_salesOrder(salesOrder_id: str, salesOrder_patch: SalesOrderPost):
    existing_salesOrder = get_holdOrder_collection().find_one({"_id": ObjectId(salesOrder_id)})
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
        result = get_holdOrder_collection().update_one(
            {"_id": ObjectId(salesOrder_id)},
            {"$set": updated_fields}
        )
        if result.modified_count == 0:
            raise HTTPException(status_code=500, detail="Failed to update salesOrder")

    # Fetch and return the updated sales order
    updated_salesOrder = get_holdOrder_collection().find_one({"_id": ObjectId(salesOrder_id)})
    updated_salesOrder["_id"] = str(updated_salesOrder["_id"])
    return updated_salesOrder




 
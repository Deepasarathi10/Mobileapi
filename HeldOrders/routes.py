
from io import BytesIO
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Path, Query, logger
from bson import ObjectId
from .models import  SalesOrder, SalesOrderPost,HoldOrderPatch
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
    try:
        return datetime.strptime(date_str, "%d-%m-%Y")
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid date format: {date_str}. Please use dd-MM-yyyy."
        )

    
async def fetch_sales_orders(query: dict) -> List[dict]:
    try:
        collection = get_holdOrder_collection()
        cursor = collection.find(query)
        results = await cursor.to_list(length=None)
        logger.info(f"Retrieved {len(results)} records from MongoDB.")
        return results
    except Exception as e:
        logger.error(f"Error querying MongoDB: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching sales orders")
async def fetch_sales_orders_try(query: dict) -> List[dict]:
    try:
        # Get the async collection
        collection = get_holdOrder_collection()

        # Execute the query asynchronously
        logger.debug(f"Executing MongoDB async query: {query}")
        results = await collection.find(query).to_list(length=None)

        logger.info(f"Retrieved {len(results)} records from MongoDB asynchronously.")
        return results

    except Exception as e:
        logger.error(f"Error querying MongoDB asynchronously: {e}", exc_info=True)
        raise
def serialize_document_forget(order: dict):
    if isinstance(order["_id"], ObjectId):
        order["salesOrderId"] = str(order["_id"])
        del order["_id"]

    if order.get("deliveryDate"):
        order["deliveryDate"] = format_date_to_ddmmyyyy(order["deliveryDate"])

    if order.get("orderDate"):
        order["orderDate"] = format_date_to_ddmmyyyy_fororder(order["orderDate"])

    return order

def serialize_document_without_pagination(order: dict):
    if isinstance(order["_id"], ObjectId):
        order["salesOrderId"] = str(order["_id"])
        del order["_id"]

    if order.get("deliveryDate"):
        order["deliveryDate"] = format_date_to_ddmmyyyy(order["deliveryDate"])

    if order.get("orderDate"):
        order["orderDate"] = format_date_to_ddmmyyyy_fororder(order["orderDate"])

    return order

def format_date_to_ddmmyyyy(date):
    if isinstance(date, str):
        try:
            datetime.strptime(date, "%d-%m-%Y")
            return date
        except ValueError:
            raise ValueError(f"Invalid date format: {date}. Expected dd-mm-yyyy.")
    elif isinstance(date, datetime):
        return date.strftime("%d-%m-%Y")
    else:
        raise TypeError(f"Unsupported type for date: {type(date)}")

def format_date_to_ddmmyyyy_fororder(date):
    if isinstance(date, str) and "T" in date:
        return datetime.strptime(date[:10], "%Y-%m-%d").strftime("%d-%m-%Y")
    elif isinstance(date, datetime):
        return date.strftime("%d-%m-%Y")
    return date

async def get_next_sequence(prefix: str) -> str:
    """
    Async version to get the next sequence number for a given prefix.
    """
    counters_collection = get_counter_collection()  # Async collection
    try:
        result = await counters_collection.find_one_and_update(
            {"prefix": prefix},
            {"$inc": {"sequence": 1}},
            upsert=True,
            return_document=True  # Motor returns the updated document
        )
        sequence = result["sequence"]
        return f"{prefix}{str(sequence).zfill(4)}"
    except Exception as e:
        logger.error(f"Error generating sequence for prefix {prefix}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate sales order number")
# -----------------------
# Create Sales Order
# -----------------------
@router.post("/", response_model=str)
async def create_salesOrder(payload: dict):
    try:
        post_data = payload.get("data", payload)
        while isinstance(post_data, list) and len(post_data) > 0:
            post_data = post_data[0]

        if not isinstance(post_data, dict):
            raise HTTPException(status_code=400, detail="Data must be a JSON object")

        if "deliveryDate" in post_data and post_data["deliveryDate"]:
            post_data["deliveryDate"] = convert_to_date(post_data["deliveryDate"])

        collection = get_holdOrder_collection()
        result = await collection.insert_one(post_data)
        logger.info(f"Inserted document ID: {result.inserted_id}")
        return str(result.inserted_id)

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Server error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# -----------------------
# Get Sales Orders (Paginated)
# -----------------------
@router.get("/approvals/paginated")
async def get_sales_orders_with_approvals_paginated(
    approvalStartDate: str = Query(..., description="Start date in dd-MM-yyyy"),
    approvalEndDate: str = Query(..., description="End date in dd-MM-yyyy"),
    approvalType: Optional[str] = Query(None, description="Type of approval"),
    saleOrderNo: Optional[str] = Query(None),
    customerNumber: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    summary: str = Query("yes")
):
    try:
        start_date = datetime.strptime(approvalStartDate, "%d-%m-%Y")
        end_date = datetime.strptime(approvalEndDate, "%d-%m-%Y").replace(hour=23, minute=59, second=59)

        approval_filter = {"approvalDate": {"$gte": start_date, "$lte": end_date}}
        if approvalType:
            approval_filter["approvalType"] = {"$regex": f"^{approvalType}$", "$options": "i"}

        query: dict = {"approvalDetails": {"$elemMatch": approval_filter}}
        if saleOrderNo:
            query["saleOrderNo"] = {"$regex": saleOrderNo, "$options": "i"}
        if customerNumber:
            query["customerNumber"] = {"$regex": customerNumber, "$options": "i"}

        collection = get_holdOrder_collection()

        total_records = await collection.count_documents(query)
        total_pages = ceil(total_records / limit) if total_records > 0 else 1

        cursor = collection.find(query).skip((page - 1) * limit).limit(limit)
        raw_orders = [serialize_document_without_pagination(order) async for order in cursor]

        summary_data = []
        if summary.lower() == "yes":
            pipeline = [
                {"$unwind": "$approvalDetails"},
                {"$match": approval_filter},
                {"$group": {"_id": "$approvalDetails.approvalType", "count": {"$sum": 1}}},
                {"$project": {"approvalType": "$_id", "count": 1, "_id": 0}}
            ]
            cursor_summary = collection.aggregate(pipeline)
            summary_data = [doc async for doc in cursor_summary]

        return {
            "pagination": {
                "page": page,
                "limit": limit,
                "total_records": total_records,
                "total_pages": total_pages
            },
            "data": raw_orders,
            "summary": summary_data
        }

    except Exception as e:
        logger.error(f"Error in paginated approval query: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


# -----------------------
# Get Sales Orders (No Pagination)
# -----------------------
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
    chequeNumber: Optional[str] = None,
    eventDate: Optional[str] = None,
    deliveryBranchName: Optional[str] = None,
    isBoxItem: Optional[List[str]] = None,
    totalBoxQty: Optional[List[float]] = None,
    holdOrderNo: Optional[str] = None,
):
    try:
        query = {}
        approval_filter = {}
        cheque_filter = {}

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
        if chequeNumber:
            cheque_filter["chequeNumber"] = {"$regex": f"^{chequeNumber}$", "$options": "i"}
            query["chequeDetails"] = {"$elemMatch": cheque_filter}
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
            if len(saleOrderNo) == 5 and saleOrderNo.isdigit():
                query["saleOrderNo"] = {"$regex": f"{saleOrderNo}$", "$options": "i"}
            else:
                query["saleOrderNo"] = {"$regex": saleOrderNo, "$options": "i"}
        if paymentType:
            query["paymentType"] = {"$regex": paymentType, "$options": "i"}
        if minAdvanceAmount is not None:
            query["advanceAmount"] = {"$gte": minAdvanceAmount}
        if filterCreditCustomer:
            query["creditCustomerOrder"] = "yes"
        if filterCreditCustomerPreinvoice:
            query["creditCustomerOrder"] = "credit sales order pre invoiced"
        if eventDate:
            query["eventDate"] = datetime.strptime(eventDate, "%d-%m-%Y")
        if deliveryBranchName:
            query["deliveryBranchName"] = {"$regex": deliveryBranchName, "$options": "i"}
        if isBoxItem:
            query["isBoxItem"] = {"$in": isBoxItem}
        if totalBoxQty:
            query["totalBoxQty"] = {"$in": totalBoxQty}
        if holdOrderNo:
            query["holdOrderNo"] = {"$regex": f"^{holdOrderNo}$", "$options": "i"}

        logger.debug(f"Final query: {query}")
        collection = get_holdOrder_collection()
        cursor = collection.find(query)
        raw_orders = [serialize_document_forget(order) async for order in cursor]

        if salesOrderIdLast5Digits:
            raw_orders = [order for order in raw_orders if order["salesOrderId"][-5:].lower() == salesOrderIdLast5Digits.lower()]

        return raw_orders

    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


# -----------------------
# Get by ID
# -----------------------
@router.get("/{salesOrder_id}", response_model=SalesOrder)
async def get_salesOrder_by_id(salesOrder_id: str):
    collection = get_holdOrder_collection()
    salesOrder = await collection.find_one({"_id": ObjectId(salesOrder_id)})
    if salesOrder:
        salesOrder["salesOrderId"] = str(salesOrder["_id"])
        return SalesOrder(**salesOrder)
    raise HTTPException(status_code=404, detail="SalesOrder not found")


# -----------------------
# Patch Sales Order
# -----------------------
@router.patch("/{salesOrder_id}")
async def patch_salesOrder(salesOrder_id: str, salesOrder_patch: SalesOrderPost):
    collection = get_holdOrder_collection()
    existing_salesOrder = await collection.find_one({"_id": ObjectId(salesOrder_id)})
    if not existing_salesOrder:
        raise HTTPException(status_code=404, detail="salesOrder not found")

    updated_fields = salesOrder_patch.dict(exclude_unset=True)
    if "deliveryDate" in updated_fields:
        updated_fields["deliveryDate"] = convert_to_date(updated_fields["deliveryDate"])

    if updated_fields:
        result = await collection.update_one({"_id": ObjectId(salesOrder_id)}, {"$set": updated_fields})
        if result.modified_count == 0:
            raise HTTPException(status_code=500, detail="Failed to update salesOrder")

    updated_salesOrder = await collection.find_one({"_id": ObjectId(salesOrder_id)})
    updated_salesOrder["salesOrderId"] = str(updated_salesOrder["_id"])
    return updated_salesOrder

@router.patch("/holdOrder/{holdOrder_id}")
async def patch_hold_order(holdOrder_id: str, holdOrder_patch: HoldOrderPatch):
    collection = get_holdOrder_collection()

    # Find based on holdOrderId instead of _id
    existing_holdOrder = await collection.find_one({"holdOrderId": holdOrder_id})
    if not existing_holdOrder:
        raise HTTPException(status_code=404, detail="Hold Order not found")

    try:
        update_data = holdOrder_patch.dict(exclude_unset=True)
        result = await collection.update_one(
            {"holdOrderId": holdOrder_id},
            {"$set": update_data}
        )

        if result.modified_count == 0:
            raise HTTPException(status_code=400, detail="No changes made")

        return {"message": "Hold Order updated successfully"}
    except Exception as e:
        print("❌ PATCH ERROR:", e)
        raise HTTPException(status_code=500, detail="Failed to update Hold Order")
# -----------------------
# Delete Sales Order
# -----------------------
@router.delete("/{salesOrder_id}")
async def delete_salesOrder(salesOrder_id: str):
    collection = get_holdOrder_collection()
    result = await collection.delete_one({"_id": ObjectId(salesOrder_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="salesOrder not found")
    return {"message": "salesOrder deleted successfully"}


# -----------------------
# Patch Approval
# -----------------------
@router.patch("/patchapproval/{salesOrder_id}")
async def patch_salesOrder_approval(salesOrder_id: str, salesOrder_patch: SalesOrderPost):
    collection = get_holdOrder_collection()
    existing_salesOrder = await collection.find_one({"_id": ObjectId(salesOrder_id)})
    if not existing_salesOrder:
        raise HTTPException(status_code=404, detail="salesOrder not found")

    updated_fields = salesOrder_patch.dict(exclude_unset=True)
    if "deliveryDate" in updated_fields:
        updated_fields["deliveryDate"] = convert_to_date(updated_fields["deliveryDate"])

    if "approvalDetails" in updated_fields:
        new_approval = updated_fields["approvalDetails"][0]
        existing_approvals = existing_salesOrder.get("approvalDetails", [])
        if existing_approvals:
            existing_approvals[-1].update(new_approval)
            updated_fields["approvalDetails"] = existing_approvals
        else:
            updated_fields["approvalDetails"] = [new_approval]

    if updated_fields:
        result = await collection.update_one({"_id": ObjectId(salesOrder_id)}, {"$set": updated_fields})
        if result.modified_count == 0:
            raise HTTPException(status_code=500, detail="Failed to update salesOrder")

    updated_salesOrder = await collection.find_one({"_id": ObjectId(salesOrder_id)})
    updated_salesOrder["salesOrderId"] = str(updated_salesOrder["_id"])
    return updated_salesOrder
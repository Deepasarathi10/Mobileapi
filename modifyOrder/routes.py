from typing import List, Optional
from fastapi import APIRouter, Body, HTTPException, Query
from bson import ObjectId
from bson.errors import InvalidId
from pydantic import BaseModel
from datetime import datetime
import logging
from .models import Invoice, ModifyOrder, ModifyOrderPost
from .utils import get_invoice_collection, get_salesOrder_collection

router = APIRouter()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ------------------- HELPERS -------------------
def convert_to_date(date_str: str) -> datetime:
    try:
        return datetime.strptime(date_str, "%d-%m-%Y")
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid date format: {date_str}. Please use dd-MM-yyyy."
        )

def format_date_to_ddmmyyyy(date: datetime) -> str:
    return date.strftime("%d-%m-%Y")

def serialize_document(order: dict) -> dict:
    if "_id" in order and isinstance(order["_id"], ObjectId):
        order["salesOrderId"] = str(order["_id"])
        del order["_id"]

    if order.get("deliveryDate") and isinstance(order["deliveryDate"], datetime):
        order["deliveryDate"] = format_date_to_ddmmyyyy(order["deliveryDate"])
    return order

async def fetch_sales_orders(query: dict) -> List[dict]:
    try:
        collection = get_salesOrder_collection()
        results = await collection.find(query).to_list(length=None)
        logger.info(f"Retrieved {len(results)} records from MongoDB.")
        return results
    except Exception as e:
        logger.error(f"Error querying MongoDB: {e}", exc_info=True)
        raise

# ------------------- ROUTES -------------------

# Create Sales Order
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

        result = await get_salesOrder_collection().insert_one(post_data)
        return str(result.inserted_id)

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

# Get Sales Orders with filters
@router.get("/")
async def get_sales_orders(
    deliveryStartDate: Optional[str] = Query(None),
    deliveryEndDate: Optional[str] = Query(None),
    deliveryDate: Optional[str] = Query(None),
    customerNumber: Optional[str] = None,
    customerName: Optional[str] = None,
    orderDate: Optional[str] = None,
    paymentType: Optional[str] = None,
    minAdvanceAmount: Optional[float] = None,
    salesOrderLast5Digits: Optional[str] = None,
    filterCreditCustomer: Optional[bool] = Query(False, alias="filter-credit-customer"),
    filterCreditCustomerPreinvoice: Optional[bool] = Query(False, alias="filter-credit-customer-preinvoice")
):
    try:
        query = {}

        if deliveryStartDate and deliveryEndDate:
            start_date = datetime.strptime(deliveryStartDate, "%d-%m-%Y")
            end_date = datetime.strptime(deliveryEndDate, "%d-%m-%Y")
            end_date = end_date.replace(hour=23, minute=59, second=59)
            query["deliveryDate"] = {"$gte": start_date, "$lte": end_date}
        elif deliveryDate:
            specific_date = datetime.strptime(deliveryDate, "%d-%m-%Y")
            query["deliveryDate"] = specific_date

        if customerName:
            query["customerName"] = {"$regex": customerName, "$options": "i"}
        if customerNumber:
            query["customerNumber"] = {"$regex": customerNumber, "$options": "i"}
        if salesOrderLast5Digits:
            query["salesOrderId"] = {"$regex": f"{salesOrderLast5Digits}$", "$options": "i"}
        if filterCreditCustomer:
            query["creditCustomerOrder"] = "yes"
        if filterCreditCustomerPreinvoice:
            query["creditCustomerOrder"] = "credit sales order pre invoiced"

        raw_orders = await fetch_sales_orders(query)
        serialized_orders = [serialize_document(order) for order in raw_orders]
        return serialized_orders

    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")

# Get Sales Order by ID
@router.get("/{salesOrder_id}", response_model=ModifyOrder)
async def get_salesOrder_by_id(salesOrder_id: str):
    salesOrder = await get_salesOrder_collection().find_one({"_id": ObjectId(salesOrder_id)})
    if salesOrder:
        salesOrder["salesOrderId"] = str(salesOrder["_id"])
        return ModifyOrder(**salesOrder)
    else:
        raise HTTPException(status_code=404, detail="SalesOrder not found")

# Patch Sales Order
@router.patch("/{salesOrder_id}")
async def patch_salesOrder(salesOrder_id: str, salesOrder_patch: ModifyOrderPost):
    existing_salesOrder = await get_salesOrder_collection().find_one({"_id": ObjectId(salesOrder_id)})
    if not existing_salesOrder:
        raise HTTPException(status_code=404, detail="salesOrder not found")

    updated_fields = {key: value for key, value in salesOrder_patch.dict(exclude_unset=True).items() if value is not None}
    if updated_fields:
        result = await get_salesOrder_collection().update_one({"_id": ObjectId(salesOrder_id)}, {"$set": updated_fields})
        if result.modified_count == 0:
            raise HTTPException(status_code=500, detail="Failed to update salesOrder")

    updated_salesOrder = await get_salesOrder_collection().find_one({"_id": ObjectId(salesOrder_id)})
    updated_salesOrder["_id"] = str(updated_salesOrder["_id"])
    return updated_salesOrder

# Delete Sales Order
@router.delete("/{salesOrder_id}")
async def delete_salesOrder(salesOrder_id: str):
    result = await get_salesOrder_collection().delete_one({"_id": ObjectId(salesOrder_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="salesOrder not found")
    return {"message": "salesOrder deleted successfully"}

# Filter by today's order date
@router.get("/filter-by-order-date-today/", response_model=List[ModifyOrder])
async def filter_by_order_date_today():
    current_date = datetime.now().strftime("%d-%m-%Y")
    query = {"orderDate": {"$eq": current_date}}

    salesOrders = await get_salesOrder_collection().find(query).to_list(length=None)
    if not salesOrders:
        raise HTTPException(status_code=404, detail="No orders found for today.")

    result = []
    for salesOrder in salesOrders:
        salesOrder["salesOrderId"] = str(salesOrder["_id"])
        result.append(ModifyOrder(**salesOrder))
    return result

# Sales Orders with advance amount filter
@router.get("/soadvancedtotalcash", response_model=List[ModifyOrder])
async def get_sales_orders_by_advance(
    orderDate: Optional[str] = None,
    paymentType: Optional[str] = None,
    minAdvanceAmount: Optional[float] = None,
):
    query = {}
    if orderDate:
        query["orderDate"] = orderDate
    if paymentType:
        query["paymentType"] = paymentType
    if minAdvanceAmount is not None:
        query["advanceAmount"] = {"$gt": minAdvanceAmount}

    salesOrders = await get_salesOrder_collection().find(query).to_list(length=None)
    if not salesOrders:
        raise HTTPException(status_code=404, detail="No sales orders found for the given criteria.")

    return [ModifyOrder(**{**order, "salesOrderId": str(order["_id"])}) for order in salesOrders]

# Create Invoice from Sales Order
@router.patch("/create_invoice/{salesOrder_id}")
async def create_invoice_from_sales_order(salesOrder_id: str):
    sales_order_collection = get_salesOrder_collection()
    sales_order = await sales_order_collection.find_one({"_id": ObjectId(salesOrder_id)})
    if not sales_order:
        raise HTTPException(status_code=404, detail="Sales Order not found")

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
        paymentType=sales_order.get("paymentType"),
        cash=sales_order.get("cash"),
        card=sales_order.get("card"),
        upi=sales_order.get("upi"),
        others=sales_order.get("others"),
        invoiceDate=datetime.now().strftime("%d-%m-%Y"),
        invoiceTime=datetime.now().strftime("%H:%M:%S"),
        shiftNumber=sales_order.get("shiftNumber"),
        shiftId=sales_order.get("shiftId"),
        invoiceNo="INV" + str(ObjectId()),
        customCharge=sales_order.get("customCharge"),
        discountAmount=sales_order.get("discountAmount"),
        discountPercentage=sales_order.get("discountPercentage"),
        user=sales_order.get("user"),
    )

    invoice_collection = get_invoice_collection()
    invoice_result = await invoice_collection.insert_one(invoice_data.dict())

    update_result = await sales_order_collection.update_one(
        {"_id": ObjectId(salesOrder_id)},
        {"$set": {"status": "SalesOrder Completed", "invoiceDate": datetime.now().strftime("%d-%m-%Y")}}
    )

    if update_result.modified_count == 0:
        raise HTTPException(status_code=500, detail="Failed to update the sales order status")

    return {"message": "Sales Order status updated and Invoice created successfully", "invoiceId": str(invoice_result.inserted_id)}

# Patch multiple credit sales orders (pre-invoice)
@router.patch("/crsopreinvoice/")
async def patch_multiple_credit_sales_orders_pre_invoiced(salesOrder_ids: List[str]):
    updated_sales_orders = []
    for salesOrder_id in salesOrder_ids:
        try:
            object_id = ObjectId(salesOrder_id)
        except InvalidId as e:
            raise HTTPException(status_code=400, detail=f"Invalid salesOrder_id: {e}")

        existing_sales_order = await get_salesOrder_collection().find_one({"_id": object_id})
        if not existing_sales_order:
            raise HTTPException(status_code=404, detail=f"Sales order not found for ID: {salesOrder_id}")

        result = await get_salesOrder_collection().update_one(
            {"_id": object_id}, {"$set": {"creditCustomerOrder": "credit sales order pre invoiced"}}
        )

        if result.modified_count == 0:
            raise HTTPException(status_code=500, detail=f"Failed to update sales order for ID: {salesOrder_id}")

        updated_sales_order = await get_salesOrder_collection().find_one({"_id": object_id})
        updated_sales_order["_id"] = str(updated_sales_order["_id"])
        updated_sales_orders.append(updated_sales_order)

    return {"message": "Sales orders updated successfully", "salesOrders": updated_sales_orders}

# Patch multiple credit sales orders (invoiced)
@router.patch("/crsoinvoice/")
async def patch_multiple_credit_sales_orders_invoiced(salesOrder_ids: List[str]):
    updated_sales_orders = []
    for salesOrder_id in salesOrder_ids:
        try:
            object_id = ObjectId(salesOrder_id)
        except InvalidId as e:
            raise HTTPException(status_code=400, detail=f"Invalid salesOrder_id: {e}")

        existing_sales_order = await get_salesOrder_collection().find_one({"_id": object_id})
        if not existing_sales_order:
            raise HTTPException(status_code=404, detail=f"Sales order not found for ID: {salesOrder_id}")

        result = await get_salesOrder_collection().update_one(
            {"_id": object_id}, {"$set": {"creditCustomerOrder": "credit sales order invoiced"}}
        )

        if result.modified_count == 0:
            raise HTTPException(status_code=500, detail=f"Failed to update sales order for ID: {salesOrder_id}")

        updated_sales_order = await get_salesOrder_collection().find_one({"_id": object_id})
        updated_sales_order["_id"] = str(updated_sales_order["_id"])
        updated_sales_orders.append(updated_sales_order)

    return {"message": "Sales orders updated successfully", "salesOrders": updated_sales_orders}

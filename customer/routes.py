from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from bson import ObjectId
from .models import Customer, CustomerPost, CustomerPatch
from .utils import get_customer_collection

router = APIRouter()

@router.post("/", response_model=Customer)
async def create_customer(customer: CustomerPost):
    """
    Create a new customer.
    """
    new_customer = customer.dict()
    result = get_customer_collection().insert_one(new_customer)
    new_customer['customerId'] = str(result.inserted_id)
    return Customer(**new_customer)

@router.get("/by-customer", response_model=List[Customer])
async def get_customers(
    customerPhoneNumber: Optional[str] = Query(None, description="Filter by customer phone number")
):
    """
    Get all customers or filter by exact customerPhoneNumber.
    """
    print("📌 Incoming request to GET /customers")
    print(f"➡️ Query param customerPhoneNumber = {customerPhoneNumber}")

    query = {}
    if customerPhoneNumber:
        query["customerPhoneNumber"] = customerPhoneNumber.strip()
        print(f"🔍 Applying filter: {query}")
    else:
        print("⚠️ No phone number filter applied, returning all customers")

    collection = get_customer_collection()
    print("✅ Connected to MongoDB collection")

    customers = list(collection.find(query))
    print(f"📊 Number of customers found = {len(customers)}")

    # Print each customer raw document (Mongo format)
    for idx, cust in enumerate(customers, start=1):
        print(f"  {idx}. Mongo Document = {cust}")

    result = [
        Customer(
            customerId=str(cust["_id"]),
            customerName=cust.get("customerName", ""),
            customerPhoneNumber=cust.get("customerPhoneNumber", ""),
            status=cust.get("status", "")
        )
        for cust in customers
    ]

    # Print each formatted response object
    for idx, cust in enumerate(result, start=1):
        print(f"  {idx}. Response Customer = {cust.dict()}")

    return result
@router.get("/", response_model=List[Customer])
async def get_all_customers():
    """
    Get all customers.
    """
    customers = list(get_customer_collection().find())
    return [Customer(**cust, customerId=str(cust["_id"])) for cust in customers]

@router.get("/{customer_id}", response_model=Customer)
async def get_customer_by_id(customer_id: str):
    """
    Get a customer by ID.
    """
    customer = get_customer_collection().find_one({"_id": ObjectId(customer_id)})
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return Customer(**customer, customerId=str(customer["_id"]))

@router.patch("/{customer_id}", response_model=Customer)
async def update_customer(customer_id: str, customer_patch: CustomerPatch):
    """
    Update an existing customer.
    """
    updated_fields = {key: value for key, value in customer_patch.dict(exclude_unset=True).items() if value is not None}
    if updated_fields:
        result = get_customer_collection().update_one(
            {"_id": ObjectId(customer_id)}, {"$set": updated_fields}
        )
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Customer not found")
    updated_customer = get_customer_collection().find_one({"_id": ObjectId(customer_id)})
    return Customer(**updated_customer, customerId=str(updated_customer["_id"]))

@router.delete("/{customer_id}")
async def delete_customer(customer_id: str):
    """
    Delete a customer by ID.
    """
    result = get_customer_collection().delete_one({"_id": ObjectId(customer_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Customer not found")
    return {"message": "Customer deleted successfully"}

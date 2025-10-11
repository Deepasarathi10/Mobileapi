from fastapi import APIRouter, HTTPException,status
from typing import List
from bson import ObjectId

from Branchwiseitem.routes import reduce_system_stock, update_system_stock
from .models import Invoice, InvoiceCreate, InvoiceUpdate
from .utils import get_invoice_collection

router = APIRouter()


def serialize_dict(item) -> dict:
    
    return {**{i: str(item[i]) for i in item if i == '_id'}, **{i: item[i] for i in item if i != '_id'}}

@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_invoices(invoice: dict):
    print("🚀 [create_invoices] API called")
    print(f"📥 Incoming invoice data: {invoice}")

    # Step 1: Add system fields
    invoice["invoiceId"] = str(ObjectId())
    invoice["status"] = "active"
    print(f"🆔 Assigned invoiceId: {invoice['invoiceId']}")
    print(f"⚙️ Invoice data with system fields: {invoice}")

    # Step 2: Insert invoice into DB
    try:
        result = await get_invoice_collection().insert_one(invoice)
        if not result.inserted_id:
            raise HTTPException(status_code=500, detail="Error creating invoice")
        print(f"✅ Invoice inserted into DB with _id: {result.inserted_id}")
    except Exception as e:
        print(f"🔥 Database insert error: {e}")
        raise HTTPException(status_code=500, detail="Database insert failed")

    # Step 3: Reduce system stock
    try:
        item_codes = invoice.get("varianceitemCode", [])
        variance_names = invoice.get("varianceName", [])
        qtys = invoice.get("qty", [])
        alias_name = invoice.get("aliasName")

        print(f"🧾 Preparing to reduce stock → Codes: {item_codes}, Names: {variance_names}, Qty: {qtys}, Branch: {alias_name}")

        # Only reduce stock if all required data is present
        if item_codes and variance_names and qtys and alias_name:
            stock_result = await reduce_system_stock(
                variance_item_codes=item_codes,
                variance_names=variance_names,
                qtys=qtys,
                alias_name=alias_name
            )
            print(f"✅ Stock reduction result: {stock_result}")
        else:
            print("⚠️ Missing data for stock reduction. Skipping stock update.")

    except Exception as e:
        print(f"⚠️ Stock reduction error: {e}")

    # Step 4: Prepare safe response (convert _id if present)
    if "_id" in invoice:
        invoice["_id"] = str(invoice["_id"])
    print("📤 Returning created invoice data.")
    return invoice



@router.get('/', response_model=List[Invoice])
async def get_invoices():
    invoices = [serialize_dict(invoice) for invoice in await get_invoice_collection().find().to_list(1000)]
    return invoices
    
@router.get('/{invoice_id}', response_model=Invoice)
async def get_invoices(invoice_id: str):
    invoice = await get_invoice_collection().find_one({'invoiceId': invoice_id})
    if invoice:
        return serialize_dict(invoice)
    raise HTTPException(status_code=404, detail="invoices invoice not found")

@router.patch('/{invoice_id}', response_model=Invoice)
async def update_invoices(invoice_id: str, invoice: InvoiceUpdate):
    print(f"Updating invoices invoice with ID: {invoice_id}")  # Log the ID
    result = await get_invoice_collection().update_one({'invoiceId': invoice_id}, {'$set': invoice.dict(exclude_unset=True)})
    if result.modified_count == 1:
        return serialize_dict(await get_invoice_collection().find_one({'invoiceId': invoice_id}))
    raise HTTPException(status_code=404, detail="invoices invoice not found")

@router.patch('/deactivate/{invoice_id}', response_model=Invoice)
async def deactivate_invoices(invoice_id: str):
    print(f"Deactivating invoices invoice with ID: {invoice_id}")  # Log the ID
    result = await get_invoice_collection().update_one({'invoiceId': invoice_id}, {'$set': {'status': 'inactive'}})
    if result.modified_count == 1:
        return serialize_dict(await get_invoice_collection().find_one({'invoiceId': invoice_id}))
    raise HTTPException(status_code=404, detail="invoices invoice not found")

@router.patch('/activate/{invoice_id}', response_model=Invoice)
async def activate_invoices(invoice_id: str):
    result = await get_invoice_collection().update_one({'invoiceId': invoice_id}, {'$set': {'status': 'active'}})
    if result.modified_count == 1:
        return serialize_dict(await get_invoice_collection().find_one({'invoiceId': invoice_id}))
    raise HTTPException(status_code=404, detail="invoices invoice not found")

@router.delete('/{invoice_id}')
async def delete_invoices(invoice_id: str):
    result = await get_invoice_collection().delete_one({'invoiceId': invoice_id})
    if result.deleted_count == 1:
        return {"message": "invoices invoice deleted"}
    raise HTTPException(status_code=404, detail="invoices invoice not found")

from fastapi import APIRouter, HTTPException,status
from typing import List
from bson import ObjectId

from Branchwiseitem.routes import reduce_system_stock, update_system_stock
from .models import Invoice, InvoiceCreate, InvoiceUpdate
from .utils import get_invoice_collection

router = APIRouter()


def serialize_dict(item) -> dict:
    
    return {**{i: str(item[i]) for i in item if i == '_id'}, **{i: item[i] for i in item if i != '_id'}}

@router.post('/', response_model=Invoice, status_code=status.HTTP_201_CREATED)
async def create_invoices(invoice: InvoiceCreate):
    print("🚀 [create_invoices] API called")

    # Step 1️⃣: Convert invoice model to dict
    invoice_dict = invoice.model_dump()
    print(f"📦 [Step 1] Raw invoice data: {invoice_dict}")

    # Step 2️⃣: Add system fields
    invoice_dict['invoiceId'] = str(ObjectId())
    invoice_dict['status'] = 'active'
    print(f"🆔 [Step 2] Assigned invoiceId: {invoice_dict['invoiceId']} and status: active")

    # Step 3️⃣: Insert invoice into database
    try:
        result = await get_invoice_collection().insert_one(invoice_dict)
        if not result.inserted_id:
            raise HTTPException(status_code=500, detail="Error creating invoice")
        print(f"✅ [Step 3] Invoice successfully inserted with _id: {result.inserted_id}")
    except Exception as db_err:
        print(f"🔥 [DB ERROR] Failed to insert invoice: {db_err}")
        raise HTTPException(status_code=500, detail="Database insert failed")

    # Step 4️⃣: Prepare data for stock reduction
    try:
        print("🔍 [Step 4] Preparing stock reduction data...")

        items = invoice_dict.get('items', [])
        if not items:
            print("⚠️ [Step 4] No items found in invoice, skipping stock update.")
            return invoice_dict

        variance_names = [item.get('varianceName') for item in items]
        branches = [invoice_dict.get('branchName')] * len(variance_names)  # Use branchName (not aliasName)
        stock_updates = [item.get('qty', 0) for item in items]  # Deduct by invoice quantity

        print(f"🧾 [Step 4] Variance names: {variance_names}")
        print(f"🏪 [Step 4] Branches: {branches}")
        print(f"📉 [Step 4] Quantities to deduct: {stock_updates}")

        # Step 5️⃣: Call internal reduce_system_stock function
        print("⚙️ [Step 5] Calling reduce_system_stock...")
        update_result = await reduce_system_stock(
            variance_names=variance_names,
            branches=branches,
            stock_updates=stock_updates
        )

        print("✅ [Step 5] Stock reduction completed successfully.")
        print(f"🪣 [Step 5 Result] {update_result}")

    except Exception as e:
        print(f"⚠️ [ERROR] Error while updating system stock: {e}")

    # Step 6️⃣: Return final invoice response
    print("📤 [Step 6] Returning created invoice data.")
    return invoice_dict

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

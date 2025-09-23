from fastapi import APIRouter, HTTPException,status
from typing import List
from bson import ObjectId
from .models import Invoice, InvoiceCreate, InvoiceUpdate
from .utils import get_invoice_collection

router = APIRouter()


def serialize_dict(item) -> dict:
    
    return {**{i: str(item[i]) for i in item if i == '_id'}, **{i: item[i] for i in item if i != '_id'}}

@router.post('/', response_model=Invoice,status_code=status.HTTP_201_CREATED)
async def create_invoices(invoice: InvoiceCreate):
    invoice_dict = invoice.model_dump()
    invoice_dict['invoiceId'] = str(ObjectId())
    invoice_dict['status'] = 'active'  # Set default status to active
    result = await get_invoice_collection().insert_one(invoice_dict)
    if result.inserted_id:
        return invoice_dict
    raise HTTPException(status_code=500, detail="Error creating invoices invoice")

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

from fastapi import APIRouter, HTTPException, status
from typing import List
from bson import ObjectId
from .models import CreditBill, CreditBillPost
from .utils import get_collection

router = APIRouter()
collection = get_collection('creditbill')


def serialize_dict(item) -> dict:
    """
    Helper function to serialize MongoDB documents into dictionaries with stringified `_id`.
    """
    return {**{i: str(item[i]) for i in item if i == '_id'}, **{i: item[i] for i in item if i != '_id'}}


@router.post('/', response_model=CreditBill, status_code=status.HTTP_201_CREATED)
async def create_credit_bill(credit_bill: CreditBillPost):
    """
    Create a new credit bill. Defaults status to 'active'.
    """
    credit_bill_dict = credit_bill.model_dump()
    credit_bill_dict['creditBillId'] = str(ObjectId())
    credit_bill_dict['status'] = 'active'  # Default status to active
    result = await collection.insert_one(credit_bill_dict)
    if result.inserted_id:
        return credit_bill_dict
    raise HTTPException(status_code=500, detail="Error creating credit bill")


@router.get('/', response_model=List[CreditBill])
async def get_credit_bills():
    """
    Get all credit bills.
    """
    credit_bills = [serialize_dict(bill) for bill in await collection.find().to_list(1000)]
    return credit_bills


@router.get('/{credit_bill_id}', response_model=CreditBill)
async def get_credit_bill_by_id(credit_bill_id: str):
    """
    Get a credit bill by its ID.
    """
    credit_bill = await collection.find_one({'creditBillId': credit_bill_id})
    if credit_bill:
        return serialize_dict(credit_bill)
    raise HTTPException(status_code=404, detail="Credit bill not found")


@router.patch('/{credit_bill_id}', response_model=CreditBill)
async def update_credit_bill(credit_bill_id: str, credit_bill: CreditBillPost):
    """
    Update an existing credit bill.
    """
    updated_fields = credit_bill.model_dump(exclude_unset=True)
    result = await collection.update_one({'creditBillId': credit_bill_id}, {'$set': updated_fields})
    if result.modified_count == 1:
        return serialize_dict(await collection.find_one({'creditBillId': credit_bill_id}))
    raise HTTPException(status_code=404, detail="Credit bill not found")


@router.delete('/{credit_bill_id}')
async def delete_credit_bill(credit_bill_id: str):
    """
    Delete a credit bill by its ID.
    """
    result = await collection.delete_one({'creditBillId': credit_bill_id})
    if result.deleted_count == 1:
        return {"message": "Credit bill deleted successfully"}
    raise HTTPException(status_code=404, detail="Credit bill not found")

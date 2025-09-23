
import logging
from datetime import datetime
from typing import List
from bson import ObjectId
from fastapi import APIRouter, HTTPException, status
from Payment.utils import get_payment_collection
from Payment.models import PaymentPost, Payment

router = APIRouter()

## Get All Payments (LIFO Order)
@router.get("/", response_model=List[Payment])
async def get_all_payment():
    try:
        # Fetch payments sorted by createdDate in descending order (LIFO)
        payments = list(get_payment_collection().find().sort("createdDate", -1))

        payment_store = []
        for payment_data in payments:
            payment_data["paymentTypeId"] = str(payment_data["_id"])  # Convert ObjectId to str
            del payment_data["_id"]  # Remove _id to match Pydantic model
            payment_store.append(Payment(**payment_data))  # Create Payment object

        return payment_store
    except Exception as e:
        logging.error(f"Error occurred while fetching payments: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

## Create a new Payment
@router.post("/", response_model=str, status_code=status.HTTP_201_CREATED)
async def create_payment(payment_data: PaymentPost):
    try:
        new_payment = payment_data.dict()
        
        # Automatically set createdDate
        new_payment["createdDate"] = datetime.utcnow()
        new_payment["editStatus"] = True

        result = get_payment_collection().insert_one(new_payment)
        return str(result.inserted_id)

    except Exception as e:
        logging.error(f"Error occurred: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    

    

## Get a specific Payment by ID
@router.get("/{payment_id}", response_model=Payment)
async def get_payment_by_id(payment_id: str):
    try:
        payment = get_payment_collection().find_one({"_id": ObjectId(payment_id)})
        if payment:
            payment["paymentTypeId"] = str(payment["_id"])
            return Payment(**payment)
        else:
            raise HTTPException(status_code=404, detail="Payment not found")
    except Exception as e:
        logging.error(f"Error occurred while fetching payment by ID: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

## Patch (Update) a Payment
@router.patch("/{payment_id}", response_model=Payment)
async def patch_payment(payment_id: str, payment_patch: PaymentPost):
    try:
        existing_payment = get_payment_collection().find_one({"_id": ObjectId(payment_id)})
        if not existing_payment:
            raise HTTPException(status_code=404, detail="Payment not found")

        updated_fields = {
            key: value for key, value in payment_patch.dict(exclude_unset=True).items() if value is not None
        }

        # Automatically update updatedDate
        updated_fields["updatedDate"] = datetime.utcnow()

        if updated_fields:
            result = get_payment_collection().update_one(
                {"_id": ObjectId(payment_id)}, {"$set": updated_fields}
            )
            if result.modified_count == 0:
                raise HTTPException(status_code=500, detail="Failed to update payment")

        updated_payment = get_payment_collection().find_one({"_id": ObjectId(payment_id)})
        updated_payment["paymentTypeId"] = str(updated_payment["_id"])
        return Payment(**updated_payment)

    except Exception as e:
        logging.error(f"Error occurred while patching payment: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

# ## Delete a Payment
# @router.delete("/{payment_id}")
# async def delete_payment(payment_id: str):
#     try:
#         result = get_payment_collection().delete_one({"_id": ObjectId(payment_id)})
#         if result.deleted_count == 0:
#             raise HTTPException(status_code=404, detail="Payment not found")
#         return {"message": "Payment deleted successfully"}
#     except Exception as e:
#         logging.error(f"Error occurred while deleting payment: {e}")
#         raise HTTPException(status_code=500, detail="Internal Server Error")
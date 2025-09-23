from fastapi import APIRouter, HTTPException, status
from typing import List
from bson import ObjectId
from .models import SalesReturn, SalesReturnPost
from .utils import get_collection

router = APIRouter()

# Use the correct collection
collection = get_collection('salesreturn')


@router.post("/", response_model=str)
async def create_sales_return(sales_return: SalesReturnPost):
    new_sales_return = sales_return.dict(by_alias=True)
    result = await collection.insert_one(new_sales_return)
    return str(result.inserted_id)


def convert_to_string_or_empty(data):
    if isinstance(data, list):
        return [str(value) if value is not None else "" for value in data]
    elif isinstance(data, (int, float)):
        return str(data)
    else:
        return str(data) if data is not None else ""


@router.get("/", response_model=List[SalesReturn])
async def get_all_sales_returns():
    sales_returns = await collection.find().to_list(length=None)
    formatted_sales_returns = []
    for sales_return in sales_returns:
        formatted_sales_return = {
            key: convert_to_string_or_empty(value) for key, value in sales_return.items()
        }
        formatted_sales_return["salesReturnId"] = str(formatted_sales_return["_id"])
        formatted_sales_returns.append(SalesReturn(**formatted_sales_return))
    return formatted_sales_returns


@router.get("/{sales_return_id}", response_model=SalesReturn)
async def get_sales_return_by_id(sales_return_id: str):
    sales_return = await collection.find_one({"_id": ObjectId(sales_return_id)})
    if sales_return:
        formatted_sales_return = {
            key: convert_to_string_or_empty(value) for key, value in sales_return.items()
        }
        formatted_sales_return["salesReturnId"] = str(formatted_sales_return["_id"])
        return SalesReturn(**formatted_sales_return)
    else:
        raise HTTPException(status_code=404, detail="Sales return not found")


@router.patch("/{sales_return_id}", response_model=SalesReturn)
async def update_sales_return(sales_return_id: str, sales_return_patch: SalesReturnPost):
    existing_sales_return = await collection.find_one({"_id": ObjectId(sales_return_id)})
    if not existing_sales_return:
        raise HTTPException(status_code=404, detail="Sales return not found")

    updated_fields = sales_return_patch.dict(exclude_unset=True, by_alias=True)
    for key, value in updated_fields.items():
        updated_fields[key] = convert_to_string_or_empty(value)

    if updated_fields:
        result = await collection.update_one(
            {"_id": ObjectId(sales_return_id)},
            {"$set": updated_fields}
        )
        if result.modified_count == 0:
            raise HTTPException(status_code=500, detail="Failed to update sales return")

    # Fetch the updated sales return
    updated_sales_return = await collection.find_one({"_id": ObjectId(sales_return_id)})
    updated_sales_return["salesReturnId"] = str(updated_sales_return["_id"])
    return SalesReturn(**updated_sales_return)


@router.delete("/{sales_return_id}", response_model=dict)
async def delete_sales_return(sales_return_id: str):
    result = await collection.delete_one({"_id": ObjectId(sales_return_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Sales return not found")
    return {"message": "Sales return deleted successfully"}

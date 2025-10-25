from fastapi import APIRouter, HTTPException
from typing import Any, Dict, List, Optional
from bson import ObjectId
from .models import Diningorder, DiningorderCreate, DiningorderUpdate
from .utils import get_collection

from Branchwiseitem.routes import reduce_system_stock


router = APIRouter()
collection = get_collection('orders')

def serialize_dict(item) -> dict:
    return {**{i: str(item[i]) for i in item if i == '_id'}, **{i: item[i] for i in item if i != '_id'}}

@router.post('/', response_model=Diningorder)
async def create_orders(order: DiningorderCreate):
    order_dict = order.dict()
    order_dict['orderId'] = str(ObjectId())
    order_dict['status'] = 'active'

    result = await collection.insert_one(order_dict)
    if not result.inserted_id:
        raise HTTPException(status_code=500, detail="Error creating order")

    try:
        order_type = order_dict.get("orderType", "").strip().lower()

        if order_type == "dine in":
            variance_codes = order_dict.get("varianceItemCodes", [])
            variance_names = order_dict.get("varianceNames", [])
            qtys = order_dict.get("quantities", [])
            alias_name = order_dict.get("branchAlias")

            if variance_codes and variance_names and qtys:
                await reduce_system_stock(
                    variance_item_codes=variance_codes,
                    variance_names=variance_names,
                    qtys=qtys,
                    alias_name=alias_name
                )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during stock reduction: {str(e)}")

    return order_dict



@router.get('/', response_model=List[Diningorder])
async def get_orders():
    orders = [serialize_dict(order) for order in await collection.find().to_list()]
    return orders



@router.get('/{order_id}', response_model=Diningorder)
async def get_orders(order_id: str):
    order = await collection.find_one({'orderId': order_id})
    if order:
        return serialize_dict(order)
    raise HTTPException(status_code=404, detail="orders order not found")


@router.get('/by-branch-date/', response_model=List[Diningorder])
async def get_orders_by_branch_and_date(
    branchName: str,
    date: str
):
    """
    Get orders by branch name and date.
    """
    try:
        # Find orders by branchName and date
        orders = await collection.find({
            'branchName': branchName,
            'date': date
        }).to_list(1000)

        if not orders:
            raise HTTPException(status_code=404, detail="No orders found for the given branch and date")

        # Serialize the orders before returning
        return [serialize_dict(order) for order in orders]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.patch('/{order_id}', response_model=Diningorder)
async def update_orders(order_id: str, order: DiningorderUpdate):
    print(f"Updating orders order with ID: {order_id}")  # Log the ID
    result = await collection.update_one({'orderId': order_id}, {'$set': order.dict(exclude_unset=True)})
    if result.modified_count == 1:
        return serialize_dict(await collection.find_one({'orderId': order_id}))
    raise HTTPException(status_code=404, detail="orders order not found")




@router.delete('/{order_id}')
async def delete_orders(order_id: str):
    result = await collection.delete_one({'orderId': order_id})
    if result.deleted_count == 1:
        return {"message": "orders order deleted"}
    raise HTTPException(status_code=404, detail="orders order not found")


@router.patch('/patch-status/{seathiveOrderId}', response_model=List[Diningorder])
async def patch_status_by_seathiveOrderId(
    seathiveOrderId: str,
    status: str,
    # orderRemark: Optional[str] = None,  # Optional order remark
    preinvoiceTime: Optional[str] = None  # ✅ Optional preinvoiceTime
):
    """
    Patch the status, remark, and preinvoiceTime of all orders with the same seathiveOrderId.
    """
    print(f"Patching status for orders with seathiveOrderId: {seathiveOrderId}")  # Log the ID

    # Find all orders with the same seathiveOrderId
    orders = await collection.find({'seathiveOrderId': seathiveOrderId}).to_list(1000)

    if not orders:
        raise HTTPException(status_code=404, detail="Orders with seathiveOrderId not found")

    # ✅ Create update data dynamically
    update_data = {'status': status}
    
    # if orderRemark is not None:
    #     update_data['orderRemark'] = orderRemark

    if preinvoiceTime is not None:
        update_data['preinvoiceTime'] = preinvoiceTime  # ✅ Add preinvoiceTime if provided

    # ✅ Update all matching orders
    result = await collection.update_many(
        {'seathiveOrderId': seathiveOrderId},
        {'$set': update_data}
    )

    if result.modified_count > 0:
        # Return updated orders
        updated_orders = [
            serialize_dict(order) for order in await collection.find({'seathiveOrderId': seathiveOrderId}).to_list(1000)
        ]
        return updated_orders

    raise HTTPException(status_code=404, detail="Orders with seathiveOrderId not found for update")



@router.patch('/patch-fields/{hiveOrderId}', response_model=Diningorder)
async def patch_fields_by_hiveOrderId(hiveOrderId: str, fields: Dict[str, Any]):
    """
    Patch specific fields of an order using hiveOrderId.
    """
    if not fields:
        raise HTTPException(status_code=400, detail="No fields provided for update")

    # Retrieve the existing order
    order = await collection.find_one({'hiveOrderId': hiveOrderId})
    if not order:
        raise HTTPException(status_code=404, detail="Order with hiveOrderId not found")

    # Update only the provided fields
    print(f"Patching fields for order with hiveOrderId: {hiveOrderId}, Fields: {fields}")  # Log the ID and fields
    result = await collection.update_one({'hiveOrderId': hiveOrderId}, {'$set': fields})
    if result.modified_count == 1:
        return serialize_dict(await collection.find_one({'hiveOrderId': hiveOrderId}))
    raise HTTPException(status_code=404, detail="Order with hiveOrderId not found for update")
 


@router.patch('/patch-table-seat/{seathiveOrderId}', response_model=List[Diningorder])
async def patch_table_and_seat_by_seathiveOrderId(
    seathiveOrderId: str,
    table: str,
    seat: str
):
    """
    Update the `table` and `seat` fields for all orders with the given `seathiveOrderId`.
    """
    print(f"Patching table and seat for seathiveOrderId: {seathiveOrderId}, Table: {table}, Seat: {seat}")

    # Find matching orders
    orders = await collection.find({'seathiveOrderId': seathiveOrderId}).to_list(1000)
    if not orders:
        print(f"No orders found with seathiveOrderId: {seathiveOrderId}")
        raise HTTPException(status_code=404, detail="Orders with seathiveOrderId not found")

    # Perform update
    update_data = {'table': table, 'seat': seat}
    result = await collection.update_many({'seathiveOrderId': seathiveOrderId}, {'$set': update_data})

    if result.modified_count > 0:
        updated_orders = [serialize_dict(order) for order in await collection.find({'seathiveOrderId': seathiveOrderId}).to_list(1000)]
        return updated_orders

    raise HTTPException(status_code=404, detail="Orders with seathiveOrderId not found for update")


# @router.patch('/patch-addon/{hiveOrderId}', response_model=Diningorder)
# async def patch_addon(
#     hiveOrderId: str, 
#     varianceName: str, 
#     addOnData: Dict[str, Any]
# ):
#     """
#     Patch or add an add-on for a specific variance in an order.
#     If the add-on already exists, update its quantity. Otherwise, add it as a new add-on.
#     """
#     # Retrieve the order
#     order = await collection.find_one({'hiveOrderId': hiveOrderId})
#     if not order:
#         raise HTTPException(status_code=404, detail="Order with hiveOrderId not found")

#     # Extract existing add-ons
#     addOns = order.get('addOns', [])
    
#     # Check if the add-on already exists
#     existing_addon = next(
#         (
#             addOn for addOn in addOns 
#             if addOn['varianceName'] == varianceName and addOn['addOnName'] == addOnData['addOnName']
#         ),
#         None
#     )

#     if existing_addon:
#         # Update the quantity of the existing add-on
#         existing_addon['quantity'] = addOnData.get('quantity', existing_addon['quantity'])
#         existing_addon['price'] = addOnData.get('price', existing_addon['price'])  # Update price if provided
#     else:
#         # Add the new add-on
#         addOns.append({
#             'varianceName': varianceName,
#             'addOnName': addOnData['addOnName'],
#             'quantity': addOnData.get('quantity', 0),  # Default quantity to 1 if not provided
#             'price': addOnData.get('price', 0),  # Default price to 0 if not provided
#         })

#     # Update the addOns field in the database
#     result = await collection.update_one(
#         {'hiveOrderId': hiveOrderId},
#         {'$set': {'addOns': addOns}}
#     )

#     if result.modified_count == 1:
#         # Return the updated order
#         updated_order = await collection.find_one({'hiveOrderId': hiveOrderId})
#         return serialize_dict(updated_order)

#     raise HTTPException(status_code=500, detail="Failed to update add-on")

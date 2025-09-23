from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status
from bson import ObjectId
from pymongo import ReturnDocument
from .models import Configs, deliveryOrder, deliveryOrderPost
from .utils import get_delivery_order_collection

router = APIRouter()

def ensure_single_enabled_order(collection, enabled_order_id: Optional[str] = None):
    """
    Ensures only the specified order is enabled (or none if enabled_order_id is None)
    - disables all other enabled orders
    - Updates their updatedDate
    """
    # Build filter to find orders to disable
    disabled_filter = {"status": "enabled"}
    if enabled_order_id:
        disabled_filter["_id"] = {"$ne": ObjectId(enabled_order_id)}
    
    # Disable all matching orders
    collection.update_many(
        disabled_filter,
        {
            "$set": {
                "status": "disabled",
                "updatedDate": datetime.utcnow().isoformat()
            }
        }
    )
    #post the delivery order 
@router.post("/delivery-orders", response_model=deliveryOrder)
async def create_delivery_order(order: deliveryOrderPost):
    order_data = order.dict()
    now = datetime.utcnow()
    
    order_data["createdDate"] = now
    order_data["updatedDate"] = now

    # Generate unique configId and timestamps for each config
    if order_data.get("configures"):
        for config in order_data["configures"]:
            config["configId"] = str(ObjectId())
            config["createdDate"] = now
            config["updatedDate"] = now

    # Insert into MongoDB
            collection = get_delivery_order_collection()
            result = collection.insert_one(order_data)

    # Return with MongoDB-generated ID as deliveryOrderId
    return {
        "deliveryOrderId": str(result.inserted_id),
        **order_data
    }
#Get all the delivery orders
@router.get("/", response_model=List[deliveryOrder])
async def get_all_delivery_orders():
    collection = get_delivery_order_collection()
    orders = list(collection.find().sort("createdDate", -1))  # Newest first
    
    if not orders:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No delivery orders found"
        )
    
    # Convert MongoDB ObjectId to string for response
    for order in orders:
        order["deliveryOrderId"] = str(order["_id"])  # Assign MongoDB `_id` to `deliveryOrderId`
        order["configures"] = [
            Configs(**config) if isinstance(config, dict) else Configs(configId=str(config)) 
            for config in order.get("configures", [])
        ]
        order.pop("_id")

    return [deliveryOrder(**order) for order in orders]


#Edit delivery order by order id as well as and config id
@router.patch("/delivery-orders/{order_id}/configs/{config_id}", response_model=deliveryOrder)
async def update_config_in_order(order_id: str, config_id: str, updated_data: Configs):
    collection = get_delivery_order_collection()

    # Step 1: Validate ObjectId
    try:
        object_id = ObjectId(order_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid delivery order ID format")

    # Step 2: Prepare updated fields
    updated_fields = {f"configures.$.{k}": v for k, v in updated_data.dict(exclude_unset=True).items()}
    updated_fields["configures.$.updatedDate"] = datetime.utcnow()  # Always update this

    # Step 3: Update config inside configures array
    result = collection.find_one_and_update(
        {"_id": object_id, "configures.configId": config_id},
        {"$set": updated_fields},
        return_document=ReturnDocument.AFTER
    )

    if not result:
        raise HTTPException(status_code=404, detail="Config or Delivery Order not found")

    # Convert ObjectId for response
    result["deliveryOrderId"] = str(result["_id"])

    return deliveryOrder(**result)



#when i had two or more configure adding configure
@router.patch("/delivery-orders/{order_id}/configs", response_model=deliveryOrder)
async def add_config_to_order(order_id: str, new_config: Configs):
    collection = get_delivery_order_collection()

    try:
        object_id = ObjectId(order_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid order ID format")

    # Generate new configId and timestamps
    new_config.configId = str(ObjectId())
    new_config.createdDate = datetime.utcnow()
    new_config.updatedDate = datetime.utcnow()

    # Push new config to `configures` array
    result = collection.find_one_and_update(
        {"_id": object_id},
        {
            "$push": {"configures": new_config.dict()},
            "$set": {"updatedDate": datetime.utcnow()}  # Update the order timestamp
        },
        return_document=True  # Return updated document
    )

    if not result:
        raise HTTPException(status_code=404, detail="Delivery order not found")

    # Convert MongoDB ObjectId to string for response
    result["deliveryOrderId"] = str(result["_id"])
    return deliveryOrder(**result)



@router.patch("/activate/{order_id}", response_model=deliveryOrder)
async def enabled_order(order_id: str):
    collection = get_delivery_order_collection()

    # Ensure the order_id is a valid ObjectId
    try:
        object_id = ObjectId(order_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid order ID format: {e}"
        )

    # Debug: Check if the order exists before proceeding
    existing_order = collection.find_one({"_id": object_id})
    if not existing_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    # Debug: Log the current order before making changes
    print(f"Found order to activate: {existing_order}")

    # Ensure only one enabled order by disabling all others
    ensure_single_enabled_order(collection, order_id)

    # Now, attempt to enable the specified order
    updated_order = collection.find_one_and_update(
        {"_id": object_id},
        {
            "$set": {
                "status": "enabled",
                "updatedDate": datetime.utcnow().isoformat()
            }
        },
        return_document=ReturnDocument.AFTER
    )

    # Check if the order was successfully updated
    if not updated_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found or failed to update"
        )

    # Convert the ObjectId to string for the response
    updated_order["deliveryOrderId"] = str(updated_order["_id"])

    # Debug: Log the updated order to ensure it's correct
    print(f"Updated order after enabling: {updated_order}")

    # Return the updated delivery order
    return deliveryOrder(**updated_order)

@router.patch("/disabled/{order_id}")
async def disabled_order(order_id: str):
    collection = get_delivery_order_collection()

    try:
        object_id = ObjectId(order_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid order ID format: {e}"
        )

    result = collection.update_one(
        {"_id": object_id},
        {
            "$set": {
                "status": "disabled",
                "updatedDate": datetime.utcnow().isoformat()
            }
        }
    )

    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found or already disabled"
        )

    return {"message": "Order disabled successfully"}

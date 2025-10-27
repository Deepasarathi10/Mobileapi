from fastapi import APIRouter, HTTPException, status
from bson import ObjectId
from bson.errors import InvalidId
from typing import List
from warehouseItems.utils import get_collection
from warehouseItems.models import WarehouseItemPost, WarehouseItemPatch, WarehouseStock

router = APIRouter()

# ------------------- Helper -------------------
def format_warehouse_item(item: dict):
    system_stock = item.get("system_stock", [])

    return {
        "warehouseItemId": str(item.get("_id", "")),
        "varianceName": item.get("varianceName") or "",
        "variance_Uom": item.get("variance_Uom") or "",
        "varianceitemCode": item.get("varianceitemCode") or "",
        "status": item.get("status") or "",
        "system_stock": system_stock,
        "subcategory": item.get("subcategory") or "",
        "variance_Defaultprice": item.get("variance_Defaultprice") or 0,
        "netPrice": item.get("netPrice") or 0,
        "qr_code": item.get("qr_code") or "",
        "selfLife": item.get("selfLife") or 0,
        "reorderLevel": item.get("reorderLevel") or 0,
        "itemName": item.get("itemName") or "",
        "tax": item.get("tax") or "",
        "hsnCode": item.get("hsnCode") or "",
        "plateItems": item.get("plateItems") if item.get("plateItems") is not None else True,
    }

# ------------------- Auto-fix old string warehouses -------------------
async def fix_old_warehouse_entries():
    collection = get_collection("warehouseitem")
    async for item in collection.find({}):
        wh = item.get("warehouseName")
        stock = item.get("stock")
        updates = {}

        # Fix warehouseName if it's a string
        if wh and isinstance(wh, str):
            updates["system_stock"] = [{"warehouseName": wh, "stock": stock if stock else 0}]
        # Fix stock if it's a number but warehouseName is missing
        elif stock and isinstance(stock, (int, float)):
            updates["system_stock"] = [{"warehouseName": "Default Warehouse", "stock": stock}]

        if updates:
            # Remove old fields
            unset = {}
            if "warehouseName" in item:
                unset["warehouseName"] = ""
            if "stock" in item:
                unset["stock"] = ""

            await collection.update_one({"_id": item["_id"]}, {"$set": updates, "$unset": unset})

# ------------------- CREATE -------------------
@router.post("/", response_model=str, status_code=status.HTTP_201_CREATED)
async def create_warehouse_item(item: WarehouseItemPost):
    collection = get_collection("warehouseitem")
    item_data = item.dict(exclude_unset=True)

    # Ensure system_stock is list
    system_stock = item_data.get("system_stock") or []
    if not isinstance(system_stock, list):
        raise HTTPException(status_code=400, detail="system_stock must be a list of warehouse stocks")
    item_data["system_stock"] = system_stock

    result = await collection.insert_one(item_data)
    return str(result.inserted_id)

# ------------------- GET ALL -------------------
@router.get("/")
async def get_warehouse_items():
    collection = get_collection("warehouseitem")
    items = await collection.find({}).to_list(length=None)
    return [format_warehouse_item(item) for item in items]

# ------------------- GET BY ID -------------------
@router.get("/{item_id}")
async def get_warehouse_item(item_id: str):
    collection = get_collection("warehouseitem")
    try:
        obj_id = ObjectId(item_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid item ID")

    item = await collection.find_one({"_id": obj_id})
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    return format_warehouse_item(item)

# ------------------- PATCH (UPDATE) -------------------
@router.patch("/{item_id}")
async def update_warehouse_item(item_id: str, patch: WarehouseItemPatch):
    collection = get_collection("warehouseitem")
    try:
        obj_id = ObjectId(item_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid item ID")

    update_data = patch.dict(exclude_unset=True)

    if not update_data:
        raise HTTPException(status_code=400, detail="No data provided for update")

    # Only system_stock is updated
    if "system_stock" in update_data:
        if not isinstance(update_data["system_stock"], list):
            raise HTTPException(status_code=400, detail="system_stock must be a list")

    result = await collection.update_one({"_id": obj_id}, {"$set": update_data})

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")

    updated_item = await collection.find_one({"_id": obj_id})
    return format_warehouse_item(updated_item)

# ------------------- ADJUST STOCK -------------------
async def adjust_warehouse_item_stock(
    variance_item_code: str,
    variance_name: str,
    warehouse_name: str,
    qty: int
):
    """
    Adjust stock for a single warehouse.
    qty > 0 → increase stock
    qty < 0 → reduce stock (but not below 0)
    """
    collection = get_collection("warehouseitem")
    item = await collection.find_one({"varianceitemCode": variance_item_code})
    if not item:
        raise HTTPException(status_code=404, detail=f"Item not found: {variance_item_code}")

    system_stock = item.get("system_stock", [])
    stock_entry = next((s for s in system_stock if s["warehouseName"] == warehouse_name), None)

    if not stock_entry:
        if qty < 0:
            raise HTTPException(status_code=400, detail=f"No stock entry for warehouse {warehouse_name}")
        stock_entry = {"warehouseName": warehouse_name, "stock": qty}
        system_stock.append(stock_entry)
    else:
        stock_entry["stock"] = max(stock_entry.get("stock", 0) + qty, 0)

    await collection.update_one({"_id": item["_id"]}, {"$set": {"system_stock": system_stock}})
    return {"varianceitemCode": variance_item_code, "varianceName": variance_name, "newStock": stock_entry["stock"]}

# ------------------- DELETE -------------------
@router.delete("/{item_id}")
async def delete_warehouse_item(item_id: str):
    collection = get_collection("warehouseitem")
    try:
        obj_id = ObjectId(item_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid item ID")

    result = await collection.delete_one({"_id": obj_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")

    return {"message": "Warehouse item deleted successfully"}

from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import APIRouter, HTTPException, status
from .models import Variance, VarianceCreate
from .utils import get_variences_collection
from bson import ObjectId
from typing import List

router = APIRouter()

mongo_client = AsyncIOMotorClient(
    "mongodb://admin:YenE580nOOUE6cDhQERP@194.233.78.90:27017/admin?appName=mongosh+2.1.1&authSource=admin&authMechanism=SCRAM-SHA-256&replicaSet=yenerp-cluster"
)
db = mongo_client["admin2"]
branchwise_items_collection = db["branchwiseitem"]


def get_database(db_name="admin2"):
    return mongo_client[db_name]



@router.post("/", response_model=str, status_code=status.HTTP_201_CREATED)
async def create_variance(variance: VarianceCreate):
    collection = get_variences_collection()
    result = await collection.insert_one(variance.dict())
    return str(result.inserted_id)




@router.get("/{varianceid}", response_model=Variance)
async def get_variance_by_id(varianceid: str):
    collection = get_variences_collection()
    variance = await collection.find_one({"_id": ObjectId(varianceid)})
    if variance:
        return Variance(**variance, varianceid=str(variance["_id"]))
    else:
        raise HTTPException(status_code=404, detail="Variance not found")


@router.patch("/{varianceid}", response_model=Variance)
async def update_variance(varianceid: str, update: VarianceCreate):
    collection = get_variences_collection()
    result = await collection.update_one(
        {"_id": ObjectId(varianceid)}, {"$set": update.dict(exclude_unset=True)}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Variance not found")
    return update.dict()


@router.delete("/{varianceid}")
async def delete_variance(varianceid: str):
    collection = get_variences_collection()
    result = await collection.delete_one({"_id": ObjectId(varianceid)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Variance not found")
    return {"message": "Variance deleted successfully"}


@router.get("/")
async def get_all_branchwise_items():
    try:
        # Fetch branchwise items
        cursor = branchwise_items_collection.find({}, {"_id": False})
        items = await cursor.to_list(length=None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Process and clean data
    result = []
    for item in items:
        # Clean the item and only return the specified fields
        cleaned_item = {
            "itemName": item.get("itemName", ""),
            "varianceitemCode": item.get("varianceitemCode", ""),
            "varianceName": item.get("varianceName", ""),
            "variance_Defaultprice": item.get("variance_Defaultprice", 0),
            "variance_Uom": item.get("variance_Uom", ""),
            "category": item.get("category", ""),
            "subCategory": item.get("itemName", ""),
            "selfLife": item.get("selfLife", 0),
            "tax": item.get("tax", 0),
            "hsnCode": item.get("hsnCode", 0),
            "stockItem": item.get("stockItems", None),  
            "plateItems": item.get("plateItems", None),  
            "type": item.get("type", None),  

        }

        result.append(cleaned_item)

    if not result:
        raise HTTPException(status_code=404, detail="No items found")

    return result

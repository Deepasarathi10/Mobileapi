from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import APIRouter, HTTPException, status
from .models import Variance, VarianceCreate,WebInfoUpdate
from .utils import get_collection
from bson import ObjectId
from typing import List

router = APIRouter()

mongo_client = AsyncIOMotorClient(
    "mongodb://admin:YenE580nOOUE6cDhQERP@194.233.78.90:27017/admin?appName=mongosh+2.1.1&authSource=admin&authMechanism=SCRAM-SHA-256&replicaSet=yenerp-cluster"
)
db = mongo_client["reactfluttertest"]
branchwise_items_collection = db["branchwiseitem"]


def get_database(db_name="reactfluttertest"):
    return mongo_client[db_name]


def get_collection(collection_name):
    db = get_database()
    return db[collection_name]


@router.post("/", response_model=str, status_code=status.HTTP_201_CREATED)
async def create_variance(variance: VarianceCreate):
    collection = get_collection("variances")
    result = await collection.insert_one(variance.dict())
    return str(result.inserted_id)


# @router.get("/", response_model=List[Variance])
# async def get_all_variances():
#     collection = get_collection("variances")
#     variances = await collection.find().to_list(None)
#     return [Variance(**variance, varianceid=str(variance["_id"])) for variance in variances]


@router.get("/{varianceid}", response_model=Variance)
async def get_variance_by_id(varianceid: str):
    collection = get_collection("variances")
    variance = await collection.find_one({"_id": ObjectId(varianceid)})
    if variance:
        return Variance(**variance, varianceid=str(variance["_id"]))
    else:
        raise HTTPException(status_code=404, detail="Variance not found")


@router.patch("/{varianceid}", response_model=Variance)
async def update_variance(varianceid: str, update: VarianceCreate):
    collection = get_collection("variances")
    result = await collection.update_one(
        {"_id": ObjectId(varianceid)}, {"$set": update.dict(exclude_unset=True)}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Variance not found")
    return update.dict()


@router.delete("/{varianceid}")
async def delete_variance(varianceid: str):
    collection = get_collection("variances")
    result = await collection.delete_one({"_id": ObjectId(varianceid)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Variance not found")
    return {"message": "Variance deleted successfully"}


@router.get("/")
async def get_all_branchwise_items():
    try:
        # Fetch branchwise items
        cursor = branchwise_items_collection.find({})
        items = await cursor.to_list(length=None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Process and clean data
    result = []
    for item in items:
        # Safely extract '_id' field using .get() with a default value if '_id' is not present
        variance_id = str(item.get("_id", ""))

        # Clean the item and only return the specified fields
        cleaned_item = {
            "varianceId": variance_id,
            "itemName": item.get("itemName", ""),
            "varianceitemCode": item.get("varianceitemCode", ""),
            "varianceName": item.get("varianceName", ""),
            "variance_Defaultprice": item.get("variance_Defaultprice", 0),
            "variance_Uom": item.get("variance_Uom", ""),
            "category": item.get("category", ""),
            "subCategory": item.get("subCategory", ""),  # Updated to use the correct field
            "selfLife": item.get("selfLife", 0),
            "tax": item.get("tax", 0),
            "hsnCode": item.get("hsnCode", 0),
            "webName": item.get("webName", ""),
            "webImage": item.get("webImage", ""),
            "webStatus": item.get("webStatus", "")
        }

        result.append(cleaned_item)

    if not result:
        raise HTTPException(status_code=404, detail="No items found")

    return result

@router.patch("/update-web/{varianceid}", response_model=dict)
async def update_web_info(varianceid: str, update: WebInfoUpdate):
    collection = get_collection("branchwiseitem")
    update_data = update.dict(exclude_none=True)
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No data provided for update")

    result = await collection.update_one(
        {"_id": ObjectId(varianceid)}, {"$set": update_data}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Item not found or no update made")

    return {"message": "Item updated successfully", "updated_fields": update_data}
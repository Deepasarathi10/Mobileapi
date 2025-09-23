from fastapi import APIRouter, HTTPException,UploadFile, File,status
from items.models import Item, ItemPost
from items.utils import get_collection
from bson import ObjectId,Optional
from typing import List
from fastapi.responses import FileResponse , StreamingResponse
import io
router = APIRouter()
item_collection = get_collection("reactfluttertest", "items")
itemphotos_collection = get_collection("reactfluttertest", "itemphotos")

@router.post("/", response_model=str,status_code=status.HTTP_201_CREATED)
async def create_item(item: ItemPost):
    item_collection = get_collection(db_name="reactfluttertest", collection_name="items")
    result = await item_collection.insert_one(item.dict())
    return str(result.inserted_id)

@router.get("/", response_model=List[Item])
async def get_all_items():
    item_collection = get_collection(db_name="reactfluttertest", collection_name="items")
    items = await item_collection.find().to_list(1000)
    return [Item(**item, itemid=str(item["_id"])) for item in items]

@router.get("/{itemid}", response_model=Item)
async def get_item_by_id(itemid: str):
    item_collection = get_collection(db_name="reactfluttertest", collection_name="items")
    item = await item_collection.find_one({"_id": ObjectId(itemid)})
    if item:
        return Item(**item, itemid=str(item["_id"]))
    else:
        raise HTTPException(status_code=404, detail="Item not found")

@router.patch("/{itemid}", response_model=Item)
async def update_item(itemid: str, item: ItemPost):
    item_collection = get_collection(db_name="reactfluttertest", collection_name="items")
    result = await item_collection.update_one({"_id": ObjectId(itemid)}, {"$set": item.dict(exclude_unset=True)})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    return item.dict()

@router.delete("/{itemid}")
async def delete_item(itemid: str):
    item_collection = get_collection(db_name="reactfluttertest", collection_name="items")
    result = await item_collection.delete_one({"_id": ObjectId(itemid)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"message": "Item deleted successfully"}

@router.post("/", response_model=str)
async def create_item(item: ItemPost):
    result = await item_collection.insert_one(item.dict())
    return str(result.inserted_id)

# Similarly, update all other route handlers to use the correctly initialized collections

@router.post("/item/upload", response_model=dict)
async def upload_photo(file: UploadFile = File(...), custom_id: Optional[str] = None):
    contents = await file.read()
    if not custom_id:
        custom_id = str(ObjectId())
    result = await itemphotos_collection.insert_one({
        "_id": custom_id,
        "filename": file.filename,
        "content": contents
    })
    return {"filename": file.filename, "id": custom_id}

@router.get("/item/view/{photo_id}", response_class=StreamingResponse)
async def get_photo(photo_id: str):
    photo_document = await itemphotos_collection.find_one({"_id": photo_id})
    if photo_document:
        content = photo_document["content"]
        return StreamingResponse(io.BytesIO(content), media_type="image/jpeg")
    else:
        raise HTTPException(status_code=404, detail="Photo not found")
    
    
    
@router.patch("/item/update/{photo_id}", response_model=dict)
async def update_photo(photo_id: str, file: UploadFile = File(...)):
    contents = await file.read()
    result = await itemphotos_collection.update_one(
        {"_id": photo_id},
        {"$set": {
            "filename": file.filename,
            "content": contents
        }}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Photo not found")
    
    return {"message": "Photo updated successfully", "filename": file.filename}
    
    
    
@router.delete("/item/delete/{photo_id}", response_model=dict)
async def delete_photo(photo_id: str):
    result = await itemphotos_collection.delete_one({"_id": photo_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Photo not found")
    return {"message": "Photo deleted successfully"}
    
from fastapi import APIRouter, HTTPException
from bson import ObjectId
from datetime import datetime
from typing import List
from SFGitems.utils import get_sfgItems_collection
from fgsummary.utils import get_sfgtofgdata_collection
from sfgtofg.models import (
    ConversionRequest,
    FGItems,
    ConversionDetails,
    CustomConversionResponse
)
from sfgtofg.utils import get_fgitems_collection, get_conversion_details_collection

router = APIRouter()
BRANCH = "Aranmanai"


@router.post("/sfg-to-fg", response_model=list[CustomConversionResponse])
async def create_split_conversion(req: ConversionRequest):
    fg_collection = get_fgitems_collection()
    conv_collection = get_conversion_details_collection()
    sfg_collection = get_sfgItems_collection()
    summary_collection = get_sfgtofgdata_collection()

    now = datetime.now()
    results = []

    for item in req.items:
        conv_data = ConversionDetails(
            itemName=item.itemName,
            branchName=[BRANCH],
            currentStock=[req.currentStock],
            dateTime=now,
        )

        sfg_doc = await sfg_collection.find_one({"sfgName": item.itemName}) or {}
        category = sfg_doc.get("fgCategory", "")

        fg_data = FGItems(
            itemName=item.itemName,
            branchName=BRANCH,
            availableStock=item.availableStock,
            fgCategory=category,
        )

        await conv_collection.insert_one(conv_data.model_dump())
        await fg_collection.insert_one(fg_data.model_dump())

        # also write to FG summary collection
        await summary_collection.insert_one({
            "itemName": fg_data.itemName,
            "availableStock": fg_data.availableStock,
            "branch": fg_data.branchName,  # keep "branch"
            "dateTime": now,
            "fgCategory": fg_data.fgCategory,
        })

        results.append(CustomConversionResponse(
            conversionDetails=conv_data,
            fgItems=fg_data
        ))

    return results


@router.get("/sfg-to-fg/conversion-details", response_model=List[ConversionDetails])
async def get_all_conversion_details_route():
    collection = get_conversion_details_collection()
    docs = collection.find()

    results = []
    async for doc in docs:
        doc.pop("_id", None)
        results.append(ConversionDetails(**doc))

    return results


@router.get("/sfg-to-fg/fg-items", response_model=List[FGItems])
async def get_all_fg_items_route():
    collection = get_fgitems_collection()
    docs = collection.find()

    results = []
    async for doc in docs:
        doc.pop("_id", None)
        results.append(FGItems(**doc))

    return results


@router.get("/sfg-to-fg/fg-items/{id}", response_model=FGItems)
async def get_fg_item_by_id(id: str):
    collection = get_fgitems_collection()
    doc = await collection.find_one({"_id": ObjectId(id)})
    if not doc:
        raise HTTPException(status_code=404, detail="FG item not found")

    doc.pop("_id", None)
    return FGItems(**doc)


@router.get("/sfg-to-fg/conversion-details/{id}", response_model=ConversionDetails)
async def get_conversion_detail_by_id(id: str):
    collection = get_conversion_details_collection()
    doc = await collection.find_one({"_id": ObjectId(id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Conversion detail not found")

    doc.pop("_id", None)
    return ConversionDetails(**doc)


@router.patch("/sfgitems/{name}")
async def update_stock(name: str, payload: dict):
    sfg_collection = get_sfgItems_collection()

    new_qty = payload.get("stockQty")
    if new_qty is None:
        raise HTTPException(status_code=400, detail="stockQty is required")

    result = await sfg_collection.update_one(
        {"sfgName": name},
        {"$set": {"stockQty": new_qty}}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail=f"SFG item '{name}' not found")

    return {"message": "Stock updated", "item": name, "newStock": new_qty}

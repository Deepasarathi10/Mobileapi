from fastapi import APIRouter, HTTPException
from typing import List
from bson import ObjectId
from promotionalOffer.models import PromotionalOffer, PromotionalOfferCreate, PromotionalOfferUpdate
from promotionalOffer.utils import get_collection

router = APIRouter()
collection = get_collection('promotionaloffer')

@router.post('/', response_model=PromotionalOffer)
async def create_promotional_offer(offer: PromotionalOfferCreate):
    offer_dict = offer.dict()
    offer_dict['promotionalOfferId'] = str(ObjectId())
    offer_dict['status'] = 'active'
    result = await collection.insert_one(offer_dict)
    if result.inserted_id:
        return offer_dict
    raise HTTPException(status_code=500, detail="Error creating promotional offer")

@router.get('/', response_model=List[PromotionalOffer])
async def get_promotional_offers():
    offers = await collection.find().to_list(1000)
    return offers

@router.get('/{offer_id}', response_model=PromotionalOffer)
async def get_promotional_offer(offer_id: str):
    offer = await collection.find_one({'promotionalOfferId': offer_id})
    if offer:
        return offer
    raise HTTPException(status_code=404, detail="Promotional offer not found")

@router.patch('/{offer_id}', response_model=PromotionalOffer)
async def update_promotional_offer(offer_id: str, offer: PromotionalOfferUpdate):
    result = await collection.update_one({'promotionalOfferId': offer_id}, {'$set': offer.dict(exclude_unset=True)})
    if result.modified_count == 1:
        updated_offer = await collection.find_one({'promotionalOfferId': offer_id})
        return updated_offer
    raise HTTPException(status_code=404, detail="Promotional offer not found")

@router.patch('/deactivate/{offer_id}', response_model=PromotionalOffer)
async def deactivate_promotional_offer(offer_id: str):
    result = await collection.update_one({'promotionalOfferId': offer_id}, {'$set': {'status': 'inactive'}})
    if result.modified_count == 1:
        updated_offer = await collection.find_one({'promotionalOfferId': offer_id})
        return updated_offer
    raise HTTPException(status_code=404, detail="Promotional offer not found")

@router.patch('/activate/{offer_id}', response_model=PromotionalOffer)
async def activate_promotional_offer(offer_id: str):
    result = await collection.update_one({'promotionalOfferId': offer_id}, {'$set': {'status': 'active'}})
    if result.modified_count == 1:
        updated_offer = await collection.find_one({'promotionalOfferId': offer_id})
        return updated_offer
    raise HTTPException(status_code=404, detail="Promotional offer not found")

@router.delete('/{offer_id}')
async def delete_promotional_offer(offer_id: str):
    result = await collection.delete_one({'promotionalOfferId': offer_id})
    if result.deleted_count == 1:
        return {"message": "Promotional offer deleted"}
    raise HTTPException(status_code=404, detail="Promotional offer not found")

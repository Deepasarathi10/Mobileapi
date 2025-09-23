from pydantic import BaseModel
from typing import List, Optional


class PromotionalOffer(BaseModel):
    promotionalOfferId: Optional[str]
    appTypes: List[str]
    offerName: Optional[str]
    locations: List[str]
    startDate: Optional[str]
    endDate: Optional[str]
    fromTime: Optional[str]
    toTime: Optional[str]
    weekdays: List[str]
    selectionType: Optional[str]
    itemName: Optional[List[str]]  # Changed to Optional
    varianceName: Optional[List[str]]  # Changed to Optional
    category: Optional[List[str]]  # Changed to Optional
    subcategory: Optional[List[str]]  # Changed to Optional
    configuration: Optional[str]
    discountValue: Optional[str]
    orderValue: Optional[str]
    orderDiscountValue: Optional[str]
    customers: Optional[List[str]]  # Changed to Optional
    image: Optional[str]
    selectionType1: Optional[str]
    selectionType2: Optional[str]
    itemName1: Optional[List[str]]  # Changed to Optional
    itemName2: Optional[List[str]]  # Changed to Optional
    varianceName1: Optional[List[str]]  # Changed to Optional
    varianceName2: Optional[List[str]]  # Changed to Optional
    category1: Optional[List[str]]  # Changed to Optional
    category2: Optional[List[str]]  # Changed to Optional
    subcategory1: Optional[List[str]]  # Changed to Optional
    subcategory2: Optional[List[str]]  # Changed to Optional
    buy: Optional[int]
    get: Optional[int]
    offerType: Optional[str]
    status: Optional[str]
    freeoffer: Optional[str]
    discountOffer: Optional[str]


class PromotionalOfferCreate(BaseModel):
    appTypes: List[str]
    offerName: Optional[str]
    locations: List[str]
    startDate: Optional[str]
    endDate: Optional[str]
    fromTime: Optional[str]
    toTime: Optional[str]
    weekdays: List[str]
    selectionType: Optional[str]
    itemName: List[str]
    varianceName: List[str]
    category: List[str]
    subcategory: List[str]
    configuration: Optional[str]
    discountValue: Optional[str]
    orderValue: Optional[str]
    orderDiscountValue: Optional[str]
    customers: List[str]
    image: Optional[str]
    selectionType1: Optional[str]
    selectionType2: Optional[str]
    itemName1: List[str]
    itemName2: List[str]
    varianceName1: List[str]
    varianceName2: List[str]
    category1: List[str]
    category2: List[str]
    subcategory1: List[str]
    subcategory2: List[str]
    buy: Optional[int]
    get: Optional[int]
    offerType: Optional[str]  # New field added
    status: Optional[str]
    freeoffer: Optional[str]
    discountOffer: Optional[str]

class PromotionalOfferUpdate(BaseModel):
    appTypes: Optional[List[str]]
    offerName: Optional[str]
    locations: Optional[List[str]]
    startDate: Optional[str]
    endDate: Optional[str]
    fromTime: Optional[str]
    toTime: Optional[str]
    weekdays: Optional[List[str]]
    selectionType: Optional[str]
    itemName: Optional[List[str]]
    varianceName: Optional[List[str]]
    category: Optional[List[str]]
    subcategory: Optional[List[str]]
    configuration: Optional[str]
    discountValue: Optional[str]
    orderValue: Optional[str]
    orderDiscountValue: Optional[str]
    customers: Optional[List[str]]
    image: Optional[str]
    selectionType1: Optional[str]
    selectionType2: Optional[str]
    itemName1: Optional[List[str]]
    itemName2: Optional[List[str]]
    varianceName1: Optional[List[str]]
    varianceName2: Optional[List[str]]
    category1: Optional[List[str]]
    category2: Optional[List[str]]
    subcategory1: Optional[List[str]]
    subcategory2: Optional[List[str]]
    buy: Optional[int]
    get: Optional[int]
    offerType: Optional[str] 
    status: Optional[str]
    freeoffer: Optional[str]
    discountOffer: Optional[str] 

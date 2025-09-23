import re
from pydantic import BaseModel, validator
from typing import List, Optional, Union

# Variance Model
class Variance(BaseModel):
    kg: Optional[Union[int, str]] = None
    price: Optional[float] = None
    qrcode: Optional[str] = None
    offer: Optional[Union[int, str]] = None
    finalPrice: Optional[float] = None


    @validator("offer", pre=True)
    def validate_offer(cls, value):
        """ Convert offer percentage if given as string (e.g., "10%") """
        if isinstance(value, str) and "%" in value:
            match = re.search(r"(\d+(\.\d+)?)%", value)
            return float(match.group(1)) if match else None
        return float(value) if isinstance(value, (int, float)) else None

    @validator("finalPrice", pre=True, always=True)
    def calculate_final_price(cls, value, values):
        """ Automatically calculate final price after applying the offer """
        price = values.get("price")
        offer = values.get("offer", 0)

        if price is not None and offer is not None:
            return round(price - (price * offer / 100), 2)
        return price


# Birthday Cake Item Model
class BirthdayCakeItem(BaseModel):
    birthdayCakeId: Optional[str] = None
    itemCode: Optional[str] = None
    category: Optional[str] = None
    subCategory: Optional[str] = None
    appItemName: Optional[str] = None
    variant: Optional[Union[str, int]] = None  # Changed from int to str
    itemName: Optional[str] = None
    flavour: List[str] = []
    tax: Optional[float] = None  # Float instead of int
    
    pricefor1kg: Optional[float] = None  # Float instead of int
    finalPrice: Optional[float] = None  # Float instead of int
    
    hsnCode: Optional[int] = None
    type: Optional[str] = None
    description: Optional[str] = None
    stockQuantity: Optional[int] = None
    # offer: Optional[float] = None  # Float instead of int
    variances: List[Variance] = []
    # image: Optional[str] = None
    status: Optional[str] = None


# Model for POST requests
class BirthdayCakeItemPost(BaseModel):
    itemCode: Optional[str] = None
    category: Optional[str] = None
    subCategory: Optional[str] = None
    appItemName: Optional[str] = None
    itemName: Optional[str] = None
    variant: Optional[Union[str, int]] = None # Changed from int to str
    flavour: List[str] = []
    tax: Optional[float] = None  # Float instead of int
    
    pricefor1kg: Optional[float] = None  # Float instead of int
    finalPrice: Optional[float] = None  # Float instead of int
    hsnCode: Optional[int] = None
    type: Optional[str] = None
    description: Optional[str] = None
    stockQuantity: Optional[int] = None
    # offer: Optional[float] = None  # Float instead of int
    variances: List[Variance] = [] 
    # image: Optional[str] = None
    status: Optional[str] = None

from pydantic import BaseModel, Field
from typing import Any, Optional

class County(BaseModel):
    countyId: Optional[str] = Field(default=None, alias="countyId")
    county: Optional[str] = Field(..., alias="COUNTRY")
    postalCode:  Optional[Any] = Field(..., alias="POSTAL_CODE")
    city: Optional[str] = Field(default=None, alias="CITY")
    state: Optional[str] = Field(default=None, alias="STATE")
    district:Optional[str]=Field(default=None,alias='DISTRICT')
    shortState: Optional[Any] = Field(default=None, alias="SHORT_STATE")
    fullCounty: Optional[str] = Field(default=None, alias="COUNTY")
    shortCounty: Optional[int] = Field(default=None, alias="SHORT_COUNTY")
    community: Optional[str] = Field(default=None, alias="COMMUNITY")
    latitude: Optional[float] = Field(default=None, alias="LATITUDE")
    longitude: Optional[float] = Field(default=None, alias="LONGITUDE")
    accuracy: Optional[int] = Field(default=None, alias="ACCURACY")

class CountyPost(BaseModel):
    county: str = Field(..., alias="COUNTRY")
    postalCode: str = Field(..., alias="POSTAL_CODE")
    city: Optional[str] = Field(default=None, alias="CITY")
    state: Optional[str] = Field(default=None, alias="STATE")
    district:Optional[str]=Field(default=None,alias='DISTRICT')
    shortState: Optional[int] = Field(default=None, alias="SHORT_STATE")
    fullCounty: Optional[str] = Field(default=None, alias="COUNTY")
    shortCounty: Optional[int] = Field(default=None, alias="SHORT_COUNTY")
    community: Optional[str] = Field(default=None, alias="COMMUNITY")
    latitude: Optional[float] = Field(default=None, alias="LATITUDE")
    longitude: Optional[float] = Field(default=None, alias="LONGITUDE")
    accuracy: Optional[int] = Field(default=None, alias="ACCURACY")



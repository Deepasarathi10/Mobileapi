
from pydantic import BaseModel

class CurrencyPreference(BaseModel):
    countryName: str
    symbol: str
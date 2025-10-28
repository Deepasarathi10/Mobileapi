from pydantic import BaseModel,Field
from typing import Optional
from datetime import datetime,date as d,time

class Cake(BaseModel):
    cakeId: Optional[int] = None
    date: Optional[d] = None

    # def to_mongo(self):
    #     dct = self.dict(exclude_none=True)
    #     # convert `date` (if present) to datetime
    #     if "date" in dct and isinstance(dct["date"], d):
    #         d = dct["date"]
    #         dct["date"] = datetime.combine(d, time.min)
    #     return dct
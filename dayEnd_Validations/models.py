from pydantic import BaseModel,Field
from typing import Optional 

class DayEndValidation(BaseModel):
    dayEndId:Optional[str]=None
    branchName:Optional[str]=None
    soApprovalsStatus:Optional[str]=None
    soPendings:Optional[int]=None
    soDeliveryStatus:Optional[str]=None
    soDeliveryPendings:Optional[int]=None
    dispatchStatus:Optional[str]=None
    dispatchPendings:Optional[int]=None
    itemTransferStatus:Optional[str]=None
    itemTransferPendings:Optional[int]=None
    storeDispatchStatus:Optional[str]=None
    storeDispatchPendings:Optional[int]=None
    shiftStatus:Optional[str]=None
    
class DayEndValidationPost(BaseModel):
    branchName:Optional[str]=None
    saleOrdersApprovals:Optional[str]=None
    soApprovalsStatus:Optional[str]=None
    soPendings:Optional[int]=None
    soDeliveryStatus:Optional[str]=None
    soDeliveryPendings:Optional[int]=None
    dispatchStatus:Optional[str]=None
    dispatchPendings:Optional[int]=None
    itemTransferStatus:Optional[str]=None
    itemTransferPendings:Optional[int]=None
    storeDispatchStatus:Optional[str]=None
    storeDispatchPendings:Optional[int]=None   
    shiftStatus:Optional[str]=None
# routers/customer_device.py
from fastapi import APIRouter, HTTPException, Depends, status
from pymongo.errors import DuplicateKeyError
from .models import CustomerDeviceData
from .utils import get_customerDevice_collection, next_counter

router = APIRouter()

@router.post("/", response_model=CustomerDeviceData,
             status_code=status.HTTP_201_CREATED)
async def create_customer_device(
    device_data: CustomerDeviceData,
    collection = Depends(get_customerDevice_collection)
):
    # 1️⃣  Use Android fingerprint (or iOS identifier) as a stable key
    fingerprint = device_data.details.get("fingerprint")
    if not fingerprint:
        raise HTTPException(400, "details.fingerprint is required for uniqueness")

    # 2️⃣  Dedup – is this fingerprint already registered?
    existing =  collection.find_one({"details.fingerprint": fingerprint})
    if existing:
        return CustomerDeviceData(**existing)      # 200 OK (FastAPI auto-changes)

    # 3️⃣  New device → generate next customerAppN
    db = collection.database                       # grab the db from the collection
    seq =  next_counter(db, "customer_app")   # e.g. 1, 2, 3…
    device_data.app_label = f"customerApp{seq}"

    try:
         collection.insert_one(device_data.dict(by_alias=True))
    except DuplicateKeyError:
        # Extremely rare race: another insert beat us; return that one
        existing =  collection.find_one({"details.fingerprint": fingerprint})
        return CustomerDeviceData(**existing)
    except Exception as exc:
        print(f"Insert failed → {exc!r}")
        raise HTTPException(500, f"Insert failed: {exc}")

    return device_data                              # 201 Created

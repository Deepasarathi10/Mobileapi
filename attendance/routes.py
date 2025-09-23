from typing import List
from fastapi import APIRouter, HTTPException
from bson import ObjectId
import orjson
from attendance.models import Attendance, AttendancePut
from attendance.utils import attendance_collection
from fastapi import APIRouter, status

router = APIRouter()

# Function to convert values to strings or empty values
def convert_to_string_or_empty(data):
    if isinstance(data, list):
        return [str(value) if value is not None and value != "" else None for value in data]
    elif isinstance(data, (int, float)):
        return str(data)
    else:
        return str(data) if data is not None and data != "" else None

@router.post("/", response_model=dict,status_code=status.HTTP_201_CREATED)
async def create_attendance(attendance: AttendancePut):
    attendance_data = attendance.model_dump()
    result = attendance_collection().insert_one(attendance_data)  # Call the function to get the collection
    if result.acknowledged:
        return {"id": str(result.inserted_id)}
    else:
        raise HTTPException(
            status_code=500, detail="Failed to insert attendance record"
        )

@router.get("/", response_model=List[Attendance])
async def get_all_attendance():
    attendance_records = []
    for attendance in attendance_collection().find():  # Call the function to get the collection
        for key, value in attendance.items():
            attendance[key] = convert_to_string_or_empty(value)

        attendance_record = attendance.copy()
        attendance_record["id"] = str(attendance_record.pop("_id"))
        attendance_records.append(Attendance(**attendance_record))

    return orjson.loads(
        orjson.dumps([attendance.dict() for attendance in attendance_records])
    )

@router.get("/{attendance_id}", response_model=Attendance)
async def get_attendance_record(attendance_id: str):
    attendance_record = attendance_collection().find_one({"_id": ObjectId(attendance_id)})  # Call the function to get the collection
    if attendance_record:
        for key, value in attendance_record.items():
            attendance_record[key] = convert_to_string_or_empty(value)

        attendance_record["_id"] = str(attendance_record["_id"])
        attendance_record["id"] = attendance_record.pop("_id")
        return Attendance(**attendance_record)
    else:
        raise HTTPException(status_code=404, detail="Attendance record not found")

@router.patch("/{attendance_id}", response_model=Attendance)
async def patch_attendance_record(attendance_id: str, attendance_patch: AttendancePut):
    updated_fields = attendance_patch.model_dump(exclude_unset=True)

    if not updated_fields:
        raise HTTPException(status_code=400, detail="No fields provided for update")

    updated_attendance = attendance_collection().find_one_and_update(  # Call the function to get the collection
        {"_id": ObjectId(attendance_id)},
        {"$set": updated_fields},
        return_document=True,
    )

    if updated_attendance:
        updated_attendance["_id"] = str(updated_attendance["_id"])
        return Attendance(**updated_attendance)

    raise HTTPException(status_code=404, detail="Attendance record not found")

@router.delete("/{attendance_id}", response_model=dict)
async def delete_attendance_record(attendance_id: str):
    result = attendance_collection().delete_one({"_id": ObjectId(attendance_id)})  # Call the function to get the collection
    if result.deleted_count == 1:
        return {"message": "Attendance record deleted successfully"}
    raise HTTPException(status_code=404, detail="Attendance record not found")







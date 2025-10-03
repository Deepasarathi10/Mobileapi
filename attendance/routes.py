from typing import List
from fastapi import APIRouter, HTTPException, status
from bson import ObjectId
import orjson
from pymongo import ReturnDocument
from attendance.models import Attendance, AttendancePut
from attendance.utils import attendance_collection

router = APIRouter()


# Function to convert values to strings or empty values
def convert_to_string_or_empty(data):
    if isinstance(data, list):
        return [str(value) if value is not None and value != "" else None for value in data]
    elif isinstance(data, (int, float)):
        return str(data)
    else:
        return str(data) if data is not None and data != "" else None


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_attendance(attendance: AttendancePut):
    attendance_data = attendance.model_dump()
    result = await attendance_collection().insert_one(attendance_data)
    if result.inserted_id:
        return {"id": str(result.inserted_id)}
    else:
        raise HTTPException(status_code=500, detail="Failed to insert attendance record")


@router.get("/", response_model=List[Attendance])
async def get_all_attendance():
    attendance_records = []
    cursor = attendance_collection().find()
    docs = await cursor.to_list(length=None)

    for attendance in docs:
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
    attendance_record = await attendance_collection().find_one({"_id": ObjectId(attendance_id)})
    if attendance_record:
        for key, value in attendance_record.items():
            attendance_record[key] = convert_to_string_or_empty(value)

        attendance_record["id"] = str(attendance_record.pop("_id"))
        return Attendance(**attendance_record)
    else:
        raise HTTPException(status_code=404, detail="Attendance record not found")


@router.patch("/{attendance_id}", response_model=Attendance)
async def patch_attendance_record(attendance_id: str, attendance_patch: AttendancePut):
    updated_fields = attendance_patch.model_dump(exclude_unset=True)

    if not updated_fields:
        raise HTTPException(status_code=400, detail="No fields provided for update")

    updated_attendance = await attendance_collection().find_one_and_update(
        {"_id": ObjectId(attendance_id)},
        {"$set": updated_fields},
        return_document=ReturnDocument.AFTER,
    )

    if updated_attendance:
        updated_attendance["id"] = str(updated_attendance.pop("_id"))
        return Attendance(**updated_attendance)

    raise HTTPException(status_code=404, detail="Attendance record not found")


@router.delete("/{attendance_id}", response_model=dict)
async def delete_attendance_record(attendance_id: str):
    result = await attendance_collection().delete_one({"_id": ObjectId(attendance_id)})
    if result.deleted_count == 1:
        return {"message": "Attendance record deleted successfully"}
    raise HTTPException(status_code=404, detail="Attendance record not found")

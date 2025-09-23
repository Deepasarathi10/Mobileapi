from pydantic import BaseModel, Field
from typing import Optional

class Employee(BaseModel):
    employeeId: Optional[str] = None  # Define _id field explicitly
    employeeNumber: Optional[str] = None
    firstName: Optional[str] = None
    lastname: Optional[str] = None  # Define _id field explicitly
    email: Optional[str] = None
    phoneNumber: Optional[str] = None 
    dateOfBirth: Optional[str] = None  # Define _id field explicitly
    gender: Optional[str] = None
    address: Optional[str] = None
    position: Optional[str] = None  # Define _id field explicitly
    department: Optional[str] = None
    dateOfHire: Optional[str] = None
    employmentType: Optional[str] = None  # Define _id field explicitly
    salary: Optional[str] = None
    reportingManager: Optional[str] = None
    employeeStatus: Optional[str] = None  # Define _id field explicitly
    emergencyContact: Optional[str] = None
    weekOff: Optional[str] = None
    totalSalary: Optional[str] = None  # Define _id field explicitly
    salaryConfiguration: Optional[str] = None
    pf: Optional[str] = None
    esi: Optional[str] = None  # Define _id field explicitly
    bonusEligible: Optional[str] = None
    shift: Optional[str] = None
    bankName: Optional[str] = None
    ifscCode: Optional[str] = None  # Define _id field explicitly
    bankAccountNumber: Optional[str] = None
    
   
class EmployeePost(BaseModel):
    employeeNumber: Optional[str] = None
    firstName: Optional[str] = None
    lastname: Optional[str] = None  # Define _id field explicitly
    email: Optional[str] = None
    phoneNumber: Optional[str] = None 
    dateOfBirth: Optional[str] = None  # Define _id field explicitly
    gender: Optional[str] = None
    address: Optional[str] = None
    position: Optional[str] = None  # Define _id field explicitly
    department: Optional[str] = None
    dateOfHire: Optional[str] = None
    employmentType: Optional[str] = None  # Define _id field explicitly
    salary: Optional[str] = None
    reportingManager: Optional[str] = None
    employeeStatus: Optional[str] = None  # Define _id field explicitly
    emergencyContact: Optional[str] = None
    weekOff: Optional[str] = None
    totalSalary: Optional[str] = None  # Define _id field explicitly
    salaryConfiguration: Optional[str] = None
    pf: Optional[str] = None
    esi: Optional[str] = None  # Define _id field explicitly
    bonusEligible: Optional[str] = None
    shift: Optional[str] = None
    bankName: Optional[str] = None
    ifscCode: Optional[str] = None  # Define _id field explicitly
    bankAccountNumber: Optional[str] = None
    
    
class EmployeeSearch(BaseModel):
   
    employeeNumber: Optional[str] = None
    firstName: Optional[str] = None
   
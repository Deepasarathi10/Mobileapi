# models.py
from pydantic import BaseModel, EmailStr

class UserRegistration(BaseModel):
    username: str
    yourname:str
    organizationname:str
    phonenumber:int
    email: EmailStr
    password: str

class EmailConfirmation(BaseModel):
    email: EmailStr
    confirmation_code: str

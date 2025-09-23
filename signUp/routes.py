# main.py
from fastapi import APIRouter, FastAPI, HTTPException
from signUp.models import EmailConfirmation,UserRegistration
from signUp.utils import get_db_collection, generate_confirmation_code, send_confirmation_email
router = APIRouter()

# Route for user registration
@router.post("/register")
async def register_user(user: UserRegistration):
    collection = get_db_collection()

    # Check if the user email is already in the database
    if collection.find_one({"email": user.email}):
        raise HTTPException(status_code=400, detail="Email already in use")

    # Generate a confirmation code
    confirmation_code = generate_confirmation_code()

    # Send the confirmation email asynchronously
    await send_confirmation_email(user.email, confirmation_code)

    # Store the user's data in MongoDB with status 'pending'
    user_data = {
        "username": user.username,
        "yourname":user.yourname,
        "organizationname":user.organizationname,
        "phonenumber":user.phonenumber,
        "email": user.email,
        "password": user.password,  # In real cases, hash the password
        "status": "pending",
        "confirmation_code": confirmation_code
    }

    collection.insert_one(user_data)

    return {"message": "Registration successful. Please check your email for the confirmation code."}

# Route for email confirmation
@router.post("/confirm_email")
async def confirm_email(data: EmailConfirmation):
    collection = get_db_collection()

    # Find the user by email
    user = collection.find_one({"email": data.email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Verify the confirmation code
    if user['confirmation_code'] == data.confirmation_code:
        collection.update_one({"email": data.email}, {"$set": {"status": "confirmed"}})
        return {"message": "Email confirmed successfully!"}
    else:
        raise HTTPException(status_code=400, detail="Invalid confirmation code")
    
@router.get("/login")
async def login_user(email: str, password: str):
    collection = get_db_collection()

    # Find the user by email
    db_user = collection.find_one({"email": email})
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if the password matches (plaintext comparison for demo purposes)
    if db_user["password"] != password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Check if the email has been confirmed
    if db_user["status"] != "confirmed":
        raise HTTPException(status_code=403, detail="Email not confirmed")

    return {"message": "Login successful!", "username": db_user["username"]}

@router.get("/checkstatus")
async def check_signup_status(email: str):
    collection = get_db_collection()

    # Find the user by email
    db_user = collection.find_one({"email": email})
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if the user's email is confirmed
    if db_user["status"] != "confirmed":
        raise HTTPException(status_code=403, detail="Email not confirmed")

    return {"message": "User is signed up and email is confirmed"}

@router.get("/get_user_data")
async def get_user_data(email: str):
    collection = get_db_collection()

    # Find the user by email
    db_user = collection.find_one({"email": email})
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Return user data (excluding sensitive information like password)
    user_data = {
        "username": db_user["username"],
        "yourname": db_user["yourname"],
        "organizationname": db_user["organizationname"],
        "phonenumber": db_user["phonenumber"],
        "email": db_user["email"],
        "status": db_user["status"]
    }

    return {"user_data": user_data}
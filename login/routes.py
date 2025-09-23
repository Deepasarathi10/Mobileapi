import logging
from fastapi import APIRouter, Depends, HTTPException
from .models import User, Token
from .utils import authenticate_user, create_access_token, get_password_hash, purchaseusers_collection

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/create_user")
async def create_user(user: User):
    # Hash the password before storing it
    hashed_password = get_password_hash(user.password)

    # Check if the user already exists
    existing_user = purchaseusers_collection.find_one({"username": user.username})
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    # Insert new user into the database
    new_user = {"username": user.username, "hashed_password": hashed_password}
    purchaseusers_collection.insert_one(new_user)

    return {"msg": "User created successfully"}

@router.post("/", response_model=Token)
async def login(user: User):
    try:
        db_user = authenticate_user(user.username, user.password)
        if not db_user:
            logger.warning(f"Login failed for user: {user.username}")
            raise HTTPException(status_code=400, detail="Incorrect username or password")

        access_token = create_access_token(data={"sub": user.username})
        return {"access_token": access_token, "token_type": "bearer"}
    except Exception as e:
        logger.error(f"Internal server error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

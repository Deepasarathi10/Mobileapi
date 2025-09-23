from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import requests
import jwt
from typing import Optional
import datetime

router = APIRouter()

# Define the structure for the payload
class PaymentRequest(BaseModel):
    mercid: str
    orderid: str
    amount: str
    order_date: str
    currency: str
    ru: str
    additional_info: Optional[dict] = None
    itemcode: str
    device: dict
    jwt_token: str  # Add the JWT token as a string field

class GSTDetails(BaseModel):
    gstin_registered: bool
    gstin_number: Optional[str] = None

# Secret key for signing JWT tokens
SECRET_KEY = "gLvxRYJYlUyTOszXZAopo6Esvp3Cb3dS"

# Route to handle the POST request to BillDesk API
@router.post("/payment/process")
async def process_payment(payment_request: PaymentRequest):
    try:
        # Decode the JWT token and verify
        decoded_payload = jwt.decode(payment_request.jwt_token, SECRET_KEY, algorithms=["HS256"])
        
        # Use the decoded payload to forward to BillDesk API or to log it
        # Example: extracting information from the decoded payload
        print(f"Decoded Payload: {decoded_payload}")
        
        # Example API call to BillDesk (you can adjust headers and URL as needed)
        url = "https://api.billdesk.com/payments/ve1_2/orders/create"
        headers = {
            "Content-Type": "application/jose",
            "Accept": "application/jose",
            "bd-timestamp": datetime.datetime.now().strftime("%Y%m%d%H%M%S"),
            "bd-traceid": payment_request.orderid
        }

        response = requests.post(url, headers=headers, data=payment_request.jwt_token)

        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Failed to send data to BillDesk API")

        return {"message": "Payment processed successfully", "response": response.text}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing payment: {str(e)}")

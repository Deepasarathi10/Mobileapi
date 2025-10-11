from datetime import datetime 
import hashlib
import hmac
import json
from typing import Dict
import urllib
from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
import requests
from requests.auth import HTTPBasicAuth
import razorpay
from .utils import get_payment_collection

router = APIRouter()

RAZORPAY_KEY_ID = "rzp_live_R6lA4ZV2bwPFPL"
RAZORPAY_KEY_SECRET = "I8PPeqlraTzLcCrLcgRtXBBK"

# @router.post("/create_qr/")
# def create_qr(price: float):
#     url = "https://api.razorpay.com/v1/payments/qr_codes"

#     payload = {
#         "type": "upi_qr",
#         "name": f"Order ₹{price}",
#         "usage": "single_use",
#         "fixed_amount": True,
#         "payment_amount": int(price * 100),  # in paise
#         "description": f"Unique QR for order ₹{price}"
#     }

#     response = requests.post(
#         url,
#         auth=HTTPBasicAuth(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET),
#         json=payload
#     )

#     # Debug info
#     print("Status:", response.status_code)
#     print("Response text:", response.text)

#     try:
#         return response.json()
#     except ValueError:
#         return {"error": "Invalid JSON from Razorpay", "text": response.text}


# @router.post("/webhook/razorpay")
# async def razorpay_webhook(request: Request):
#     payload = await request.body()
#     data = json.loads(payload)

#     if data["event"] == "payment.captured":
#         payment_id = data["payload"]["payment"]["entity"]["id"]
#         amount = data["payload"]["payment"]["entity"]["amount"] / 100
#         status = data["payload"]["payment"]["entity"]["status"]

#         # You can match this payment to your order and update DB
#         return {"message": "Payment captured", "payment_id": payment_id, "amount": amount}

#     return {"message": "Event ignored"}

import uuid

active_connections = {}

# ------------------ QR CREATION ------------------
@router.post("/create_qr/")
async def create_qr(price: float):
    qr_id = str(uuid.uuid4())

    payload = {
        "type": "upi_qr",
        "name": f"Order ₹{price}",
        "usage": "single_use",
        "fixed_amount": True,
        "payment_amount": int(price * 100),
        "description": f"Unique QR for order ₹{price}",
        "notes": {"qr_id": qr_id}
    }

    response = requests.post(
        "https://api.razorpay.com/v1/payments/qr_codes",
        auth=HTTPBasicAuth(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET),
        json=payload
    )

    data = response.json()
    return {"qr_id": qr_id, **data}


# ------------------ WEBSOCKET ------------------
@router.websocket("/ws/{qr_id}")
async def websocket_endpoint(websocket: WebSocket, qr_id: str):
    await websocket.accept()
    active_connections[qr_id] = websocket
    print(f"✅ WebSocket connected for QR: {qr_id}")
    try:
        while True:
            await websocket.receive_text()  # keeps connection alive
    except WebSocketDisconnect:
        active_connections.pop(qr_id, None)
        print(f"❌ WebSocket disconnected for QR: {qr_id}")


# ------------------ WEBHOOK ------------------
@router.post("/webhook")
async def razorpay_webhook(request: Request):
    payload = await request.body()
    data = json.loads(payload)
    payments = get_payment_collection()

    if data["event"] == "payment.captured":
        payment = data["payload"]["payment"]["entity"]
        amount = payment["amount"] / 100
        payment_id = payment["id"]

        # ------------------ QR Payment ------------------
        qr_id = payment.get("notes", {}).get("qr_id")
        if qr_id:
            await payments.insert_one({
                "qr_id": qr_id,
                "status": "success",
                "payment_id": payment_id,
                "price": amount,
                "method": "qr",
                "payment_data": payment,
                "created_at": datetime.utcnow()
            })

            # Notify frontend
            if qr_id in active_connections:
                ws = active_connections[qr_id]
                await ws.send_json({
                    "status": "success",
                    "payment_id": payment_id,
                    "amount": amount
                })
                print(f"✅ QR Payment success notified to {qr_id}")

        # ------------------ Card Payment ------------------
        order_id = payment.get("order_id")
        if order_id:
            await payments.insert_one({
                "order_id": order_id,
                "status": "success",
                "payment_id": payment_id,
                "price": amount,
                "method": "card",
                "payment_data": payment,
                "created_at": datetime.utcnow()
            })
        return {"message": "Payment captured"}

    elif data["event"] == "payment.failed":
        payment = data["payload"]["payment"]["entity"]
        qr_id = payment.get("notes", {}).get("qr_id")
        if qr_id:
            await payments.insert_one({
                "qr_id": qr_id,
                "status": "failed",
                "payment_data": payment,
                "method": "qr",
                "created_at": datetime.utcnow()
            })
            if qr_id in active_connections:
                ws = active_connections[qr_id]
                await ws.send_json({
                    "status": "failed",
                    "reason": payment.get("error_reason", "Unknown")
                })
        return {"message": "Payment failed"}

    return {"message": "Event ignored"}


# ------------------ CARD ORDER CREATION ------------------
@router.post("/create_order/")
async def create_order(price: float):
    url = "https://api.razorpay.com/v1/orders"
    payload = {
        "amount": int(price * 100),
        "currency": "INR",
        "payment_capture": 1,
    }

    response = requests.post(
        url,
        auth=HTTPBasicAuth(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET),
        json=payload
    )

    data = response.json()
    return data


# ------------------ PAYMENT VERIFICATION ------------------
@router.post("/verify_payment")
async def verify_payment(request: Request):
    data = await request.json()
    order_id = data["order_id"]
    payment_id = data["payment_id"]
    signature = data["signature"]

    generated_signature = hmac.new(
        bytes(RAZORPAY_KEY_SECRET, "utf-8"),
        bytes(f"{order_id}|{payment_id}", "utf-8"),
        hashlib.sha256
    ).hexdigest()

    payments = get_payment_collection()

    if generated_signature == signature:
        # ✅ Update existing record or insert
        await payments.update_one(
            {"order_id": order_id},
            {"$set": {
                "status": "success",
                "payment_id": payment_id,
                "method": "card",
                "verified_at": datetime.utcnow()
            }},
            upsert=True
        )
        return {"status": "success"}
    else:
        await payments.update_one(
            {"order_id": order_id},
            {"$set": {
                "status": "failed",
                "payment_id": payment_id,
                "method": "card",
                "verified_at": datetime.utcnow()
            }},
            upsert=True
        )
        return {"status": "failed"}

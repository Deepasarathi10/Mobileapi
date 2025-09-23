# utils.py
from pymongo import MongoClient
from smtplib import SMTP

import random
import string
import asyncio
from smtplib import SMTP_SSL
from email.mime.text import MIMEText
# MongoDB connection
def get_db_collection():
    client = MongoClient("mongodb://admin:YenE580nOOUE6cDhQERP@194.233.78.90:27017/admin?appName=mongosh+2.1.1&authSource=admin&authMechanism=SCRAM-SHA-256&replicaSet=yenerp-cluster")
    db = client["reactfluttertest"]
    return db['signup']

# Function to generate a random confirmation code
def generate_confirmation_code():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=6))

# Function to send a confirmation email asynchronously
async def send_confirmation_email(user_email: str, confirmation_code: str):
    # HTML content for the email body
    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f4f4;">
        <div style="max-width: 600px; margin: 20px auto; padding: 20px; background-color: #ffffff; border: 1px solid #dddddd; border-radius: 8px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);">
            <h2 style="text-align: center; color: #333333; margin-bottom: 20px;">Email Confirmation</h2>
            <p style="font-size: 16px; color: #555555; text-align: center;">
                Thank you for signing up! Please use the following confirmation code to verify your email:
            </p>
            <div style="text-align: center; margin: 30px 0;">
                <span style="display: inline-block; background-color: #007BFF; color: #ffffff; padding: 10px 20px; font-size: 24px; font-weight: bold; border-radius: 5px;">
                    {confirmation_code}
                </span>
            </div>
            <p style="font-size: 14px; color: #777777; text-align: center; margin-top: 20px;">
                If you didn't request this email, please ignore it.
            </p>
            <p style="font-size: 12px; color: #aaaaaa; text-align: center;">
                © 2024 Your Company Name. All rights reserved.
            </p>
        </div>
      </body>
    </html>
    """

    # Use MIMEText with 'html' subtype
    msg = MIMEText(html_content, 'html')
    msg['Subject'] = 'Email Confirmation'
    msg['From'] = 'support@ngxcorp.com'  # Your sender email address
    msg['To'] = user_email

    try:
        # Use SMTP_SSL for secure port 465
        with SMTP_SSL("ngxcorp.com", 465) as server:
            server.login("support@ngxcorp.com", "Mummy@@33")  # Correct credentials
            server.sendmail(msg['From'], [msg['To']], msg.as_string())
        print(f"Confirmation email sent to {user_email}")
    except Exception as e:
        print(f"Error sending email: {e}")
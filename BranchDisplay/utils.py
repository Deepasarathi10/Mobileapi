import logging
from pymongo import MongoClient
from datetime import datetime

def get_branch_report():
    client = MongoClient("mongodb://admin:YenE580nOOUE6cDhQERP@194.233.78.90:27017/admin?appName=mongosh+2.1.1&authSource=admin&authMechanism=SCRAM-SHA-256&replicaSet=yenerp-cluster")
    db = client["admin"]
    return db["branchDisplay"]


# async def fetch_actual_current_date() -> datetime:
#     """Fetch the actual current date and time."""
#     try:
#         logging.info("Fetching actual current date.")
#         current_date = datetime.utcnow()  # Replace with actual fetching if needed
#         logging.info(f"Current date fetched: {current_date}")
#         return current_date
#     except Exception as e:
#         logging.error(f"Could not fetch the actual current date: {e}")
#         raise ValueError("Could not fetch the actual current date") from e
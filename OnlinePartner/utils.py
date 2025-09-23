

from pymongo import MongoClient
from datetime import datetime

# MongoDB connection and database getter
def get_db():
    client = MongoClient("mongodb://admin:YenE580nOOUE6cDhQERP@194.233.78.90:27017/admin?appName=mongosh+2.1.1&authSource=admin&authMechanism=SCRAM-SHA-256&replicaSet=yenerp-cluster")
    return client["reactfluttertest"]

# Getter for the master collection
def get_online_partners_collection():
    return get_db()['onlinePartnerMaster']

# Function to create a partner and a collection named after partnerName
def create_partner_and_collection(partner_data: dict):
    db = get_db()
    collection = db['onlinePartnerMaster']

    # Add timestamps
    partner_data['createdDate'] = datetime.utcnow()
    partner_data['updatedDate'] = datetime.utcnow()

    # Insert into master collection
    result = collection.insert_one(partner_data)

    # Create new collection with sanitized partner name
    partner_name = partner_data.get("partnerName")
    if partner_name:
        collection_name = partner_name.replace(" ", "_").lower()
        db.create_collection(collection_name)
    else:
        raise ValueError("partnerName is required to create a collection.")

    return str(result.inserted_id)













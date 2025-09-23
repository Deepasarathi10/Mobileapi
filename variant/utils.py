from pymongo import MongoClient
from bson import ObjectId

# MongoDB connection and collection getter for item groups
def get_variant_collection():
    client = MongoClient("mongodb://admin:YenE580nOOUE6cDhQERP@194.233.78.90:27017/admin?appName=mongosh+2.1.1&authSource=admin&authMechanism=SCRAM-SHA-256&replicaSet=yenerp-cluster")
    db = client["reactfluttertest"]  # Adjust database name as per your MongoDB setup
    return db['variant']  

# Utility function to convert data to strings or None
def convert_to_string_or_none(data):
    if isinstance(data, list):
        return [convert_to_string_or_none(value) for value in data]
    elif isinstance(data, dict):
        return {key: convert_to_string_or_none(value) for key, value in data.items()}
    elif isinstance(data, (int, float)):
        return str(data)
    else:
        return None if data == "" else str(data)

from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

# MongoDB connection and collection getter for item groups
def get_employee_collection():
    client = AsyncIOMotorClient("mongodb://admin:YenE580nOOUE6cDhQERP@194.233.78.90:27017/admin?appName=mongosh+2.1.1&authSource=admin&authMechanism=SCRAM-SHA-256&replicaSet=yenerp-cluster")
    db = client["master"]  # Adjust database name as per your MongoDB setup
    return db['employee']  


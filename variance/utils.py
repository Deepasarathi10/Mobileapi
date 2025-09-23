from motor.motor_asyncio import AsyncIOMotorClient

mongo_client = AsyncIOMotorClient("mongodb://admin:YenE580nOOUE6cDhQERP@194.233.78.90:27017/admin?appName=mongosh+2.1.1&authSource=admin&authMechanism=SCRAM-SHA-256&replicaSet=yenerp-cluster")

def get_database(db_name="reactfluttertest"):
    return mongo_client[db_name]

def get_collection(db_name, collection_name):
    db = get_database(db_name)
    return db[collection_name]

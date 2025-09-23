from motor.motor_asyncio import AsyncIOMotorClient 

def get_database():
    client = AsyncIOMotorClient('mongodb://admin:YenE580nOOUE6cDhQERP@194.233.78.90:27017/admin?appName=mongosh+2.1.1&authSource=admin&authMechanism=SCRAM-SHA-256&replicaSet=yenerp-cluster')
    db = client['reactfluttertest']
    return db

def get_collection(collection_name: str):
    db = get_database()
    return db[collection_name]

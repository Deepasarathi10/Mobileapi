from motor.motor_asyncio import AsyncIOMotorClient

mongo_client = AsyncIOMotorClient(
    "mongodb://admin:YenE580nOOUE6cDhQERP@194.233.78.90:27017/admin?appName=mongosh+2.1.1&authSource=admin&authMechanism=SCRAM-SHA-256&replicaSet=yenerp-cluster"
)

DEFAULT_DB_NAME = "reactfluttertest"
DEFAULT_COLLECTION_NAME = "vehicles"

def get_database(db_name: str = DEFAULT_DB_NAME):
    return mongo_client[db_name]

def get_vehicle_collection():
    db = get_database()
    return db[DEFAULT_COLLECTION_NAME]

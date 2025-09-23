from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient

def getmeters():

   client =MongoClient("mongodb://admin:YenE580nOOUE6cDhQERP@194.233.78.90:27017/admin?appName=mongosh+2.1.1&authSource=admin&authMechanism=SCRAM-SHA-256&replicaSet=yenerp-cluster")
   database = client['dailyactivities']
   return database["ebMaster"]


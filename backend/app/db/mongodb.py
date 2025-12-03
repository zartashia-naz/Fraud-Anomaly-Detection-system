from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ReturnDocument
from fastapi import Depends
from app.core.config import settings

class MongoDB:
    client: AsyncIOMotorClient = None

mongodb = MongoDB()

async def get_database():
    return mongodb.client[settings.MONGO_DB_NAME]

async def connect_to_mongo():
    mongodb.client = AsyncIOMotorClient(settings.MONGO_URI)
    print("📌 Connected to MongoDB")

async def close_mongo_connection():
    mongodb.client.close()
    print("❌ MongoDB Connection Closed")

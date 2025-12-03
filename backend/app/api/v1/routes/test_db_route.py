from fastapi import APIRouter
from app.db.mongodb import get_database

router = APIRouter()

@router.get("/test-mongo")
async def test_mongo():
    try:
        db = await get_database()

        # Correct Motor async usage
        collections = await db.list_collection_names()

        return {
            "status": "success",
            "message": "Connected to MongoDB!",
            "collections": collections
        }

    except Exception as e:
        return {
            "status": "failed",
            "error": str(e)
        }

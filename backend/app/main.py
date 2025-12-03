from fastapi import FastAPI
from app.db.mongodb import connect_to_mongo, close_mongo_connection

# Import all routers
from app.api.v1.routes.test_db_route import router as test_db_router

app = FastAPI(title="LinkLock Fraud Detection System")

# Include Routers
app.include_router(test_db_router, prefix="/api/v1")

# Startup & Shutdown Events
@app.on_event("startup")
async def startup_db():
    await connect_to_mongo()

@app.on_event("shutdown")
async def shutdown_db():
    await close_mongo_connection()

@app.get("/")
def home():
    return {"message": "Backend is running!"}


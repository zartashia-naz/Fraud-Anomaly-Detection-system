from fastapi import FastAPI
from app.db.mongodb import connect_to_mongo, close_mongo_connection
from app.core.config import settings
from app.api.v1.routes.auth_route import router as auth_router
from app.api.v1.routes.transaction_route import router as transaction_router

app = FastAPI(title=settings.PROJECT_NAME)

app.include_router(auth_router, prefix="/api/v1/auth")
app.include_router(transaction_router, prefix="/api/v1")


@app.on_event("startup")
async def startup_event():
    await connect_to_mongo()

@app.on_event("shutdown")
async def shutdown_event():
    await close_mongo_connection()

@app.get("/")
def root():
    return {"message": "Backend running"}

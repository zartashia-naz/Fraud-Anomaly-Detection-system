# main.py

from fastapi import FastAPI
from app.db.mongodb import connect_to_mongo, close_mongo_connection, get_client
from app.core.config import settings

from app.api.v1.routes.auth_route import router as auth_router
from app.api.v1.routes.transaction_route import router as transaction_router
from app.api.v1.routes.login_log_route import router as LoginLogRouter
from app.api.v1.routes.test_dsa_routes import router as DSA_TEST_ROUTER
from app.api.v1.routes.test_db_route import router as test_db_router

from app.core.dsa.mongo_dsa import MongoDSA
from app.services.anomaly_worker import persist_anomalies_loop

import asyncio
from fastapi.middleware.cors import CORSMiddleware

# ---------------------------------------------------------------------
# CREATE FASTAPI APP (only ONCE)
# ---------------------------------------------------------------------

# Create FastAPI app
app = FastAPI(
    title="Fraud Detection System API",
    description="Real-time fraud and anomaly detection system for login and transactions",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# ---------------------------------------------------------------------
# ROUTES (include BEFORE middleware for proper wrapping)
# ---------------------------------------------------------------------

app.include_router(test_db_router)
app.include_router(LoginLogRouter, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1/auth")
app.include_router(transaction_router, prefix="/api/v1")
app.include_router(DSA_TEST_ROUTER, prefix="/api/v1")

# ---------------------------------------------------------------------
# CORS CONFIG (ADD AFTER ROUTERS - KEY FIX)
# ---------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],  # React app
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],  # Expose all custom headers (e.g., for anomalies)
)

# ---------------------------------------------------------------------
# STARTUP
# ---------------------------------------------------------------------

# Database Events
@app.on_event("startup")
async def startup_event():
    """Initialize database connection on startup"""
    logger.info("🚀 Starting Fraud Detection API...")
    await connect_to_mongo()
    logger.info("✅ Database connected successfully")


    client = get_client()
    db = client[settings.MONGO_DB_NAME]

    mongo_dsa = MongoDSA(db)
    await mongo_dsa.ensure_indexes()

    loop = asyncio.get_event_loop()
    loop.create_task(persist_anomalies_loop(db))

# ---------------------------------------------------------------------
# SHUTDOWN
# ---------------------------------------------------------------------

@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection on shutdown"""
    logger.info("🛑 Shutting down Fraud Detection API...")
    await close_mongo_connection()
    logger.info("✅ Database connection closed")

# ---------------------------------------------------------------------
# ROOT
# ---------------------------------------------------------------------

@app.get("/")
def root():
    return {"message": "Backend running"}

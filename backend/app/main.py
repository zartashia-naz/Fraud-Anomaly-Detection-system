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

app = FastAPI(title=settings.PROJECT_NAME)

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

@app.on_event("startup")
async def startup_event():
    await connect_to_mongo()

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
    await close_mongo_connection()

# ---------------------------------------------------------------------
# ROOT
# ---------------------------------------------------------------------

@app.get("/")
def root():
    return {"message": "Backend running"}
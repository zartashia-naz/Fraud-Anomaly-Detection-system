# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware

# from app.db.mongodb import connect_to_mongo, close_mongo_connection
# from app.core.config import settings
# from app.api.v1.routes.auth_route import router as auth_router
# from app.api.v1.routes.transaction_route import router as transaction_router
# from app.api.v1.routes.login_log_route import router as LoginLogRouter


# app = FastAPI(title=settings.PROJECT_NAME)

# # -------------------------
# #        ADD CORS
# # -------------------------
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=[
#         "http://localhost:8080",
#         "http://127.0.0.1:8080",
#     ],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )
# # -------------------------

# app.include_router(LoginLogRouter, prefix="/api/v1")
# app.include_router(auth_router, prefix="/api/v1/auth")
# app.include_router(transaction_router, prefix="/api/v1")


# @app.on_event("startup")
# async def startup_event():
#     await connect_to_mongo()

# @app.on_event("shutdown")
# async def shutdown_event():
#     await close_mongo_connection()

# @app.get("/")
# def root():
#     return {"message": "Backend running"}



# ============CLAUDE CODE BELOW===============



# backend/app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.routes import auth_route, user_routes, login_log_route
from app.db.mongodb import connect_to_mongo, close_mongo_connection
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Fraud Detection System API",
    description="Real-time fraud and anomaly detection system for login and transactions",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite default
        "http://localhost:3000",  # React default
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Database Events
@app.on_event("startup")
async def startup_event():
    """Initialize database connection on startup"""
    logger.info("🚀 Starting Fraud Detection API...")
    await connect_to_mongo()
    logger.info("✅ Database connected successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection on shutdown"""
    logger.info("🛑 Shutting down Fraud Detection API...")
    await close_mongo_connection()
    logger.info("✅ Database connection closed")


# Health Check
@app.get("/", tags=["Health"])
async def root():
    """Root endpoint - API health check"""
    return {
        "message": "Fraud Detection System API",
        "status": "running",
        "version": "1.0.0",
        "docs": "/api/docs"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Detailed health check endpoint"""
    return {
        "status": "healthy",
        "database": "connected",
        "api": "operational"
    }


# API Routes
app.include_router(
    auth_route.router,
    prefix="/api/v1/auth",
    tags=["Authentication"]
)

app.include_router(
    login_log_route.router,
    prefix="/api/v1",
    tags=["Login Logs"]
)

# Uncomment when you create these routes
# app.include_router(
#     user_routes.router,
#     prefix="/api/v1/user",
#     tags=["User"]
# )

# app.include_router(
#     transaction_routes.router,
#     prefix="/api/v1/transactions",
#     tags=["Transactions"]
# )

# app.include_router(
#     anomaly_routes.router,
#     prefix="/api/v1/anomaly",
#     tags=["Anomaly Detection"]
# )

# app.include_router(
#     admin_routes.router,
#     prefix="/api/v1/admin",
#     tags=["Admin"]
# )


# Exception Handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Custom 404 handler"""
    return {
        "error": "Not Found",
        "message": f"The endpoint {request.url.path} does not exist",
        "status_code": 404
    }


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Custom 500 handler"""
    logger.error(f"Internal server error: {exc}")
    return {
        "error": "Internal Server Error",
        "message": "An unexpected error occurred. Please try again later.",
        "status_code": 500
    }


# Development Info
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
 )

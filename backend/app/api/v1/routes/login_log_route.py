# from fastapi import APIRouter, Depends, Request, HTTPException
# from app.schemas.login_log_schema import LoginLogCreate, LoginLogResponse
# from app.db.models.login_log_model import LoginLogModel
# from app.utils.ip_utils import get_client_ip
# from app.utils.geoip_utils import get_location_from_ip
# from app.core.auth import get_current_user
# from app.db.mongodb import get_database
# from datetime import datetime
# from bson import ObjectId

# router = APIRouter(prefix="/login-logs", tags=["Login Logs"])


# @router.post("/", response_model=LoginLogResponse)
# async def create_login_log(
#     request: Request,
#     data: LoginLogCreate,
#     current_user=Depends(get_current_user),
#     db=Depends(get_database)
# ):
#     # Extract from JWT
#     user_id = current_user["id"]
#     email = current_user.get("email")   # <-- FIX: fetch email

#     # IP & location
#     ip_address = get_client_ip(request)
#     location = get_location_from_ip(ip_address)

#     # Find last login
#     last_log = await db.login_logs.find_one(
#         {"user_id": user_id},
#         sort=[("_id", -1)]
#     )
#     previous_login_time = last_log["login_time"] if last_log else None

#     # Count login attempts
#     login_attempts = await db.login_logs.count_documents({"user_id": user_id})

#     # Create log entry
#     log = LoginLogModel(
#         user_id=user_id,
#         email=email,   # <-- FIXED
#         device_id=data.device_id or "unknown-device",
#         ip_address=ip_address,
#         location=location,
#         login_attempts=login_attempts + 1,
#         previous_login_time=previous_login_time
#     )

#     result = await db.login_logs.insert_one(log.model_dump())

#     return LoginLogResponse(
#         id=str(result.inserted_id),
#         **log.model_dump()
#     )


# ============CLAUDE CODE BELOW===============


# backend/app/api/v1/routes/login_logs_route.py

from fastapi import APIRouter, Depends, HTTPException, Query
from app.core.auth import get_current_user
from app.db.mongodb import get_database
from typing import List, Optional
from datetime import datetime, timedelta
from bson import ObjectId

router = APIRouter(prefix="/login-logs", tags=["Login Logs"])


@router.get("/my-logs")
async def get_my_login_logs(
    limit: int = Query(default=50, le=100),
    skip: int = Query(default=0, ge=0),
    current_user=Depends(get_current_user),
    db=Depends(get_database)
):
    """
    Get current user's login history
    """
    user_id = current_user["id"]
    
    # Get logs
    logs_cursor = db.login_logs.find(
        {"user_id": user_id}
    ).sort("login_time", -1).skip(skip).limit(limit)
    
    logs = await logs_cursor.to_list(length=limit)
    
    # Convert ObjectId to string
    for log in logs:
        log["_id"] = str(log["_id"])
    
    # Get total count
    total = await db.login_logs.count_documents({"user_id": user_id})
    
    return {
        "logs": logs,
        "total": total,
        "limit": limit,
        "skip": skip
    }


@router.get("/my-devices")
async def get_my_devices(
    current_user=Depends(get_current_user),
    db=Depends(get_database)
):
    """
    Get list of devices user has logged in from
    """
    user_id = current_user["id"]
    
    # Aggregate unique devices
    pipeline = [
        {"$match": {"user_id": user_id, "status": "success"}},
        {"$sort": {"login_time": -1}},
        {
            "$group": {
                "_id": "$device_id",
                "device_name": {"$first": "$device_name"},
                "device_info": {"$first": "$device_info"},
                "last_used": {"$first": "$login_time"},
                "first_used": {"$last": "$login_time"},
                "login_count": {"$sum": 1},
                "locations": {"$addToSet": "$location.city"}
            }
        },
        {"$sort": {"last_used": -1}}
    ]
    
    devices = await db.login_logs.aggregate(pipeline).to_list(length=100)
    
    return {
        "devices": devices,
        "total": len(devices)
    }


@router.get("/suspicious-activity")
async def get_suspicious_activity(
    days: int = Query(default=30, le=90),
    current_user=Depends(get_current_user),
    db=Depends(get_database)
):
    """
    Get suspicious login attempts
    """
    user_id = current_user["id"]
    since = datetime.utcnow() - timedelta(days=days)
    
    # Find failed attempts or high-risk logins
    suspicious = await db.login_logs.find({
        "user_id": user_id,
        "login_time": {"$gte": since},
        "$or": [
            {"status": "failed"},
            {"is_anomaly": True},
            {"risk_score": {"$gte": 50}}
        ]
    }).sort("login_time", -1).to_list(length=100)
    
    # Convert ObjectId
    for log in suspicious:
        log["_id"] = str(log["_id"])
    
    return {
        "suspicious_logins": suspicious,
        "count": len(suspicious)
    }


@router.get("/stats")
async def get_login_stats(
    current_user=Depends(get_current_user),
    db=Depends(get_database)
):
    """
    Get login statistics
    """
    user_id = current_user["id"]
    
    # Total logins
    total_logins = await db.login_logs.count_documents({"user_id": user_id})
    
    # Failed attempts (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    failed_logins = await db.login_logs.count_documents({
        "user_id": user_id,
        "status": "failed",
        "login_time": {"$gte": thirty_days_ago}
    })
    
    # Unique devices
    devices = await db.login_logs.distinct("device_id", {"user_id": user_id})
    
    # Unique locations
    locations = await db.login_logs.distinct("location.city", {
        "user_id": user_id,
        "location.city": {"$ne": None}
    })
    
    # Last login
    last_login = await db.login_logs.find_one(
        {"user_id": user_id, "status": "success"},
        sort=[("login_time", -1)]
    )
    
    return {
        "total_logins": total_logins,
        "failed_attempts_30d": failed_logins,
        "unique_devices": len(devices),
        "unique_locations": len(locations),
        "last_login": {
            "time": last_login["login_time"] if last_login else None,
            "device": last_login.get("device_name") if last_login else None,
            "location": last_login.get("location", {}).get("city") if last_login else None
        } if last_login else None
    }


# ========== ADMIN ENDPOINTS (Optional) ==========

@router.get("/all", dependencies=[Depends(get_current_user)])
async def get_all_login_logs(
    limit: int = Query(default=100, le=500),
    skip: int = Query(default=0, ge=0),
    db=Depends(get_database)
):
    """
    Admin endpoint: Get all login logs
    TODO: Add admin role check
    """
    logs = await db.login_logs.find().sort("login_time", -1).skip(skip).limit(limit).to_list(length=limit)
    
    for log in logs:
        log["_id"] = str(log["_id"])
    
    total = await db.login_logs.count_documents({})
    
    return {
        "logs": logs,
        "total": total,
        "limit": limit,
        "skip": skip
    }
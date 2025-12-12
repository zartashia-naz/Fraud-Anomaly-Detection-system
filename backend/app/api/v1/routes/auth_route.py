# app/api/v1/routes/auth_route.py
from fastapi import APIRouter, HTTPException, Depends, Request
from app.schemas.user_schema import UserSignup, UserLogin, TokenResponse
from app.core.security import hash_password, verify_password, create_access_token
from app.db.mongodb import get_database
from datetime import datetime
from bson import ObjectId

# redis utilities
from app.core.dsa.redis_dsa import (
    record_login_attempt,
    set_last_ip,
    set_last_device,
    push_recent_login
)

from app.db.models.login_log_model import LoginLogModel
from app.utils.ip_utils import get_client_ip
from app.utils.geoip_utils import get_location_from_ip

router = APIRouter()

@router.post("/signup")
async def signup(user: UserSignup, db=Depends(get_database)):
    existing_user = await db["users"].find_one({"email": user.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    user_data = user.model_dump()
    user_data["password"] = hash_password(user.password)

    result = await db["users"].insert_one(user_data)

    return {
        "status": "success",
        "message": "User registered successfully",
        "user_id": str(result.inserted_id)
    }


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: UserLogin,
    request: Request,
    db=Depends(get_database)
):
    # find user
    user = await db["users"].find_one({"email": credentials.email})
    if not user:
        raise HTTPException(status_code=400, detail="Invalid email or password")

    if not verify_password(credentials.password, user["password"]):
        raise HTTPException(status_code=400, detail="Invalid email or password")

    # create token
    user_id = str(user["_id"])
    token = create_access_token({"id": user_id, "email": user["email"]})

    # -----------------------
    # LOG LOGIN ACTIVITY
    # -----------------------
    email = user["email"]
    ip_addr = get_client_ip(request)
    location = get_location_from_ip(ip_addr)

    # redis tracking
    record_login_attempt(user_id)
    set_last_ip(user_id, ip_addr)
    set_last_device(user_id, "unknown-device")

    # last login
    last_log = await db.login_logs.find_one({"user_id": user_id}, sort=[("_id", -1)])
    prev_login_time = last_log["login_time"] if last_log else None

    total_logs = await db.login_logs.count_documents({"user_id": user_id})

    # create model
    log = LoginLogModel(
        user_id=user_id,
        email=email,
        device_id="unknown-device",
        ip_address=ip_addr,
        location=location,
        previous_login_time=prev_login_time,
        login_attempts=total_logs + 1
    )

    # convert to dict with safe JSON
    log_dict = log.model_dump()
    log_dict["login_time"] = log_dict["login_time"].isoformat()
    if log_dict.get("previous_login_time"):
        log_dict["previous_login_time"] = log_dict["previous_login_time"].isoformat()

    # save in Mongo
    result = await db.login_logs.insert_one(log_dict)
    log_dict["_id"] = str(result.inserted_id)  # FIX: convert ObjectId to string

    # save in Redis
    push_recent_login(user_id, log_dict)

    # -----------------------
    # END LOGGING
    # -----------------------

    return TokenResponse(access_token=token)

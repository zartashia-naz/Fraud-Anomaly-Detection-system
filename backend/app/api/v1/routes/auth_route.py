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
    
    new_user = user.model_dump(by_alias=False)
    new_user["password"] = hash_password(user.password)
    new_user["created_at"] = datetime.utcnow()
    new_user["status"] = "active"
    
    result = await db["users"].insert_one(new_user)
    
    return {
        "status": "success",
        "message": "Account created successfully",
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
        # Log failed attempt
        await _create_login_log(
            db=db,
            email=credentials.email,
            user_id=None,
            request=request,
            device_data=credentials.device_data,
            status="failed"
        )
        raise HTTPException(status_code=400, detail="Invalid email or password")
    
    if not verify_password(credentials.password, user["password"]):
        # Log failed attempt
        await _create_login_log(
            db=db,
            email=user["email"],
            user_id=str(user["_id"]),
            request=request,
            device_data=credentials.device_data,
            status="failed"
        )
        raise HTTPException(status_code=400, detail="Invalid email or password")
    
    # ========== 2. CREATE SUCCESS LOGIN LOG ==========
    log_id = await _create_login_log(
        db=db,
        email=user["email"],
        user_id=str(user["_id"]),
        request=request,
        device_data=credentials.device_data,
        status="success"
    )
    
    print(f"✅ Login successful - User: {user['email']}, Log ID: {log_id}")
    
    # ========== 3. CREATE ACCESS TOKEN ==========
    token = create_access_token({
        "id": str(user["_id"]),
        "email": user["email"]
    })
    
    # ========== 4. RETURN RESPONSE ==========
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        requires_2fa=False,  # Will be determined in Phase 2
        risk_score=0  # Will be calculated in Phase 2
    )

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

async def _create_login_log(
    db,
    email: str,
    user_id: str | None,
    request: Request,
    device_data: dict | None,
    status: str = "success"
) -> str:
    """
    Helper function to create login log entry
    Returns: log_id as string
    """
    
    # Get IP address
    ip_address = get_client_ip(request)
    
    # Get geolocation
    location = await get_geolocation(ip_address)
    
    # Parse device information
    device_info = parse_device_info(device_data or {})
    device_id = device_info["device_id"]
    
    # Get previous successful login (only if user exists)
    previous_login_time = None
    total_logins = 0
    
    if user_id:
        previous_login = await db.login_logs.find_one(
            {"user_id": user_id, "status": "success"},
            sort=[("login_time", -1)]
        )
        previous_login_time = previous_login["login_time"] if previous_login else None
        total_logins = await db.login_logs.count_documents({"user_id": user_id})
    
    # Create login log entry
    login_log = {
        "user_id": user_id,
        "email": email,
        "device_id": device_id,
        "device_name": device_info["device_name"],
        "device_info": device_info,
        "ip_address": ip_address,
        "login_time": datetime.utcnow(),
        "previous_login_time": previous_login_time,
        "login_attempts": total_logins + 1,
        "location": location,
        "status": status,  # success, failed, blocked
        "is_anomaly": False,  # Will be updated in Phase 2
        "risk_score": 0,  # Will be calculated in Phase 2
    }
    
    # Insert log
    result = await db.login_logs.insert_one(login_log)
    
    return str(result.inserted_id)
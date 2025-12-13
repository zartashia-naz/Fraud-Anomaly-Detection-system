# from fastapi import APIRouter, HTTPException, Depends
# from app.schemas.user_schema import UserSignup, UserLogin, TokenResponse
# from app.core.security import hash_password, verify_password, create_access_token
# from app.db.mongodb import get_database

# router = APIRouter()

# @router.post("/signup")
# async def signup(user: UserSignup, db=Depends(get_database)):

#     exists = await db["users"].find_one({"email": user.email})
#     if exists:
#         raise HTTPException(status_code=400, detail="Email already registered")

#     new_user = user.model_dump(by_alias=False)
#     new_user["password"] = hash_password(user.password)

#     result = await db["users"].insert_one(new_user)

#     return {
#         "status": "success",
#         "message": "Account created successfully",
#         "user_id": str(result.inserted_id)
#     }


# @router.post("/login", response_model=TokenResponse)
# async def login(credentials: UserLogin, db=Depends(get_database)):

#     user = await db["users"].find_one({"email": credentials.email})
#     if not user:
#         raise HTTPException(status_code=400, detail="Invalid email or password")

#     if not verify_password(credentials.password, user["password"]):
#         raise HTTPException(status_code=400, detail="Invalid email or password")

#     token = create_access_token({"id": str(user["_id"]), "email": user["email"]})

#     return TokenResponse(access_token=token)


# =============CLUDE CODE BELOW=================

# backend/app/api/v1/routes/auth_routes.py

# backend/app/api/v1/routes/auth_routes.py

from fastapi import APIRouter, HTTPException, Depends, Request
from app.schemas.user_schema import UserSignup, UserLogin, TokenResponse
from app.core.security import hash_password, verify_password, create_access_token
from app.db.mongodb import get_database
from app.utils.device_utils import parse_device_info, generate_device_fingerprint
from app.utils.ip_utils import get_client_ip, get_geolocation
from datetime import datetime
from bson import ObjectId

router = APIRouter()

@router.post("/signup")
async def signup(user: UserSignup, db=Depends(get_database)):
    exists = await db["users"].find_one({"email": user.email})
    if exists:
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
    """
    Login endpoint with automatic device fingerprinting and login logging
    """
    
    # ========== 1. VERIFY CREDENTIALS ==========
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
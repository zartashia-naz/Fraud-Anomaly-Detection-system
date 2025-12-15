# from fastapi import APIRouter, Depends, Request, HTTPException
# from app.schemas.login_log_schema import LoginLogCreate, LoginLogResponse
# from app.db.models.login_log_model import LoginLogModel
# from app.utils.ip_utils import get_client_ip
# from app.utils.geoip_utils import get_location_from_ip
# from app.core.auth import get_current_user
# from app.db.mongodb import get_database
# from datetime import datetime

# router = APIRouter(prefix="/login-logs", tags=["Login Logs"])


# # -----------------------------
# # POST → store new login record
# # -----------------------------
# @router.post("/", response_model=LoginLogResponse)
# async def create_login_log(
#     request: Request,
#     data: LoginLogCreate,
#     current_user=Depends(get_current_user),
#     db=Depends(get_database)
# ):

#     user_id = current_user["id"]   # ← extracted from JWT

#     # Get IP & location
#     ip_address = get_client_ip(request)
#     location = get_location_from_ip(ip_address)

#     # Find last login
#     last_log = await db.login_logs.find_one(
#         {"user_id": user_id},
#         sort=[("_id", -1)]
#     )
#     previous_login_time = last_log["login_time"] if last_log else None

#     # Count login attempts today
#     login_attempts = await db.login_logs.count_documents({"user_id": user_id})

#     # Create model
#     log = LoginLogModel(
#         user_id=user_id,
#         device_id=data.device_id,
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







# app/api/v1/routes/login_log_route.py
from fastapi import APIRouter, Depends, Request, HTTPException
from app.schemas.login_log_schema import LoginLogCreate, LoginLogResponse
from app.db.models.login_log_model import LoginLogModel
from app.utils.ip_utils import get_client_ip
from app.utils.geoip_utils import get_location_from_ip
from app.core.auth import get_current_user
from app.db.mongodb import get_database
from datetime import datetime
from bson import ObjectId

# Redis DSA imports
from app.core.dsa.redis_dsa import (
    push_recent_login,
    record_login_attempt,
    set_last_ip,
    set_last_device
)

router = APIRouter(prefix="/login-logs", tags=["Login Logs"])


@router.post("/", response_model=LoginLogResponse)
async def create_login_log(
    request: Request,
    data: LoginLogCreate,
    current_user=Depends(get_current_user),
    db=Depends(get_database)
):

    user_id = current_user["id"]
    email = current_user.get("email")

    # --- IP + Location ---
    ip_address = get_client_ip(request)
    location = get_location_from_ip(ip_address)

    # --- Redis: Sliding Window Login Attempts ---
    attempts_in_last_minute = record_login_attempt(user_id)

    # --- Redis: Quick Access ---
    set_last_ip(user_id, ip_address)
    set_last_device(user_id, data.device_id or "unknown-device")

    # --- Find last login in Mongo ---
    last_log = await db.login_logs.find_one(
        {"user_id": user_id},
        sort=[("_id", -1)]
    )

    previous_login_time = last_log["login_time"] if last_log else None

    # Total log count
    login_attempts = await db.login_logs.count_documents({"user_id": user_id})

    # --- Create Login Log Object ---
    log = LoginLogModel(
        user_id=user_id,
        email=email,
        device_id=data.device_id or "unknown-device",
        ip_address=ip_address,
        location=location,
        login_attempts=login_attempts + 1,
        previous_login_time=previous_login_time
    )

    # Insert into MongoDB
    result = await db.login_logs.insert_one(log.model_dump())

    # --- Write to Redis Recent Login Queue ---
    push_recent_login(user_id, log.model_dump())

    return LoginLogResponse(
        id=str(result.inserted_id),
        **log.model_dump()
    )






# =======================================================================


# from fastapi import APIRouter, Depends, Request, HTTPException
# from datetime import datetime
# from app.db.mongodb import get_database
# from app.schemas.login_log_schema import LoginLogCreate
# from app.core.auth import get_current_user
# from app.utils.ip_utils import get_client_ip
# from app.utils.geoip_utils import get_location_from_ip

# router = APIRouter(prefix="/login-logs", tags=["Login Logs"])


# @router.post("/")
# async def create_login_log(
#     request: Request,
#     data: LoginLogCreate,
#     current_user: dict = Depends(get_current_user),
#     db=Depends(get_database)
# ):

#     user_id = current_user["id"]
#     email = current_user["email"]

#     # Fetch IP
#     client_ip = get_client_ip(request)

#     # Fetch location from IP
#     location = get_location_from_ip(client_ip)

#     # Fetch previous login log
#     last_log = await db.login_logs.find_one(
#         {"user_id": user_id},
#         sort=[("_id", -1)]
#     )

#     previous_login_time = last_log["login_time"] if last_log else None

#     # Count login attempts today
#     today = datetime.utcnow().date()
#     login_attempts = await db.login_logs.count_documents({
#         "user_id": user_id,
#         "login_time": {"$gte": datetime(today.year, today.month, today.day)}
#     })

#     # Create new login log
#     log_doc = {
#         "user_id": user_id,
#         "email": email,
#         "device_id": data.device_id,
#         "ip_address": client_ip,
#         "location": location,
#         "login_time": datetime.utcnow(),
#         "previous_login_time": previous_login_time,
#         "login_attempts": login_attempts + 1,
#         "is_anomaly": False
#     }

#     result = await db.login_logs.insert_one(log_doc)

#     return {
#         "message": "Login log saved successfully",
#         "log_id": str(result.inserted_id),
#         "data": log_doc
#     }

# from fastapi import APIRouter, Depends, Request
# from app.db.mongodb import get_database
# from app.schemas.login_log_schema import LoginLogCreate
# from app.core.auth import get_current_user   # <-- JWT
# from app.utils.ip_utils import get_client_ip
# from app.utils.geoip_utils import get_location_from_ip
# from app.utils.device_utils import get_device_id
# from datetime import datetime

# # Import anomaly handler
# # from app.routes.anomaly_routes import handle_anomaly

# router = APIRouter(prefix="/login-logs", tags=["Login Logs"])

# @router.post("/")
# async def create_login_log(
#     request: Request,
#     payload: LoginLogCreate,
#     db=Depends(get_database),
#     current_user=Depends(get_current_user)   # <-- Extract from token
# ):
#     user_id = str(current_user["_id"])
#     email = current_user["email"]

#     # 1) Auto fetch device ID
#     device_id = payload.device_id or get_device_id(request)

#     # 2) Auto fetch IP and location
#     ip_address = get_client_ip(request)
#     location = get_location_from_ip(ip_address)

#     # 3) Get previous login
#     last_login = await db.login_logs.find_one(
#         {"user_id": user_id}, sort=[("_id", -1)]
#     )
#     previous_login_time = last_login["login_time"] if last_login else None

#     # 4) Count login attempts
#     login_attempts = await db.login_logs.count_documents({"user_id": user_id})

#     # 5) Build login log object
#     log_data = {
#         "user_id": user_id,
#         "email": email,
#         "device_id": device_id,
#         "ip_address": ip_address,
#         "location": location,
#         "login_time": datetime.utcnow(),
#         "previous_login_time": previous_login_time,
#         "login_attempts": login_attempts,
#         "is_anomaly": False
#     }

#     # --- Fake ML prediction for now ---
#     prediction = False   # later model gives real value

#     # 6) Send to anomaly handler
#     # await handle_anomaly({
#     #     "is_anomaly": prediction,
#     #     "event_type": "login",
#     #     "event_data": log_data
#     # }, db)

#     # 7) Save log
#     await db.login_logs.insert_one(log_data)

#     return {
#         "message": "Login log saved",
#         "is_anomaly": prediction,
#         "data": log_data
#     }

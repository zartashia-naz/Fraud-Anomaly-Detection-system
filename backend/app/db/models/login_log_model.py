# from datetime import datetime
# from typing import Optional
# from pydantic import BaseModel, Field

# class LoginLogModel(BaseModel):
#     user_id: str
#     email: Optional[str] = None
#     device_id: str
#     ip_address: str
#     login_time: datetime = Field(default_factory=datetime.utcnow)
#     previous_login_time: Optional[datetime] = None
#     login_attempts: int = 1
#     location: Optional[dict] = None
#     is_anomaly: bool = False

#     class Config:
#         from_attributes = True



# =============CLAUDE CODE BELOW===============

# backend/app/db/models/login_logs_model.py

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class LoginLogModel(BaseModel):
    """
    Model for login log entries
    Stores comprehensive login attempt information
    """
    user_id: Optional[str] = None  # None for failed attempts where user doesn't exist
    email: str
    device_id: str
    device_name: Optional[str] = None
    device_info: Optional[Dict[str, Any]] = None  # Full device fingerprint data
    ip_address: str
    login_time: datetime = Field(default_factory=datetime.utcnow)
    previous_login_time: Optional[datetime] = None
    login_attempts: int = 1
    location: Optional[Dict[str, Any]] = None
    status: str = "success"  # success, failed, blocked
    is_anomaly: bool = False
    risk_score: int = 0  # 0-100 risk score (Phase 2)
    rule_based_score: Optional[int] = None  # Phase 2
    ml_score: Optional[int] = None  # Phase 2
    rule_reasons: Optional[Dict[str, Any]] = None  # Phase 2
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "user_id": "6932f0839e3c414dc16273a0",
                "email": "user@example.com",
                "device_id": "device-a1b2c3d4e5f6g7h8",
                "device_name": "Chrome on Windows",
                "device_info": {
                    "browser": {"name": "Chrome", "version": "120.0.0"},
                    "os": {"name": "Windows", "version": "10"}
                },
                "ip_address": "192.168.1.1",
                "login_time": "2025-12-13T10:30:00",
                "previous_login_time": "2025-12-12T09:15:00",
                "login_attempts": 5,
                "location": {
                    "country": "Pakistan",
                    "city": "Lahore",
                    "latitude": 31.5204,
                    "longitude": 74.3587
                },
                "status": "success",
                "is_anomaly": False,
                "risk_score": 15
            }
        }
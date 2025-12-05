# from pydantic import BaseModel
# from datetime import datetime
# from typing import Optional

# class LoginLogCreate(BaseModel):
#     email: str
#     device_id: str

# class LoginLogResponse(BaseModel):
#     user_id: str
#     email: str
#     device_id: str
#     ip_address: str
#     location: dict
#     login_time: datetime
#     previous_login_time: Optional[datetime] = None
#     login_attempts: int
#     is_anomaly: bool = False





from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict

class LoginLogCreate(BaseModel):
    device_id: Optional[str] = None
    login_status: str = "success"


class LoginLogResponse(BaseModel):
    id: str
    user_id: str
    email: Optional[str] = None
    device_id: str
    ip_address: str
    location: Dict
    login_time: datetime
    previous_login_time: Optional[datetime] = None
    login_attempts: int
    is_anomaly: bool = False

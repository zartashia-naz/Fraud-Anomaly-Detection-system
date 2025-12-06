from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class LoginLogModel(BaseModel):
    user_id: str
    email: Optional[str] = None
    device_id: str
    ip_address: str
    login_time: datetime = Field(default_factory=datetime.utcnow)
    previous_login_time: Optional[datetime] = None
    login_attempts: int = 1
    location: Optional[dict] = None
    is_anomaly: bool = False

    class Config:
        from_attributes = True

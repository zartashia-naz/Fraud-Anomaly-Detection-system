from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class TransactionModel(BaseModel):
    user_id: str
    amount: float

    # NEW FIELDS YOU REQUESTED
    category: str
    ip: str
    device_id: str

    # Auto-fetched fields
    transaction_date: datetime = Field(default_factory=datetime.utcnow)
    location: Optional[Dict[str, Any]] = None
    merchant_id: Optional[str] = None
    transaction_duration: Optional[float] = None
    previous_transaction_date: Optional[datetime] = None
    description: Optional[str] = None

    is_anomaly: Optional[bool] = False

    class Config:
        from_attributes = True


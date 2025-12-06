from fastapi import APIRouter, Depends, Request
from app.db.mongodb import get_database
from app.schemas.transaction_schema import TransactionCreate
from app.db.models.transaction_model import TransactionModel
from app.utils.geoip_utils import get_location_from_ip
from app.utils.ip_utils import get_client_ip
from datetime import datetime

# Import anomaly handler
from app.api.v1.routes.anomaly_route import handle_anomaly

router = APIRouter(prefix="/transactions", tags=["Transactions"])

@router.post("/")
async def create_transaction(request: Request, data: TransactionCreate, db=Depends(get_database)):

    user_id = "12345"  # replace with JWT later

    # Get IP & Location
    client_ip = get_client_ip(request)
    location = get_location_from_ip(client_ip)

    # Last transaction
    last_txn = await db.transactions.find_one({"user_id": user_id}, sort=[("_id", -1)])
    previous_txn_date = last_txn["transaction_date"] if last_txn else None

    # Calculate duration
    transaction_duration = (
        (datetime.utcnow() - previous_txn_date).total_seconds()
        if previous_txn_date else None
    )

    merchant_id = f"M-{client_ip.replace('.', '')}"

    # Build transaction dict
    txn = TransactionModel(
        user_id=user_id,
        amount=data.amount,
        transaction_type=data.transaction_type,
        channel=data.channel,
        location=location,
        merchant_id=merchant_id,
        transaction_duration=transaction_duration,
        previous_transaction_date=previous_txn_date
    )

    # ML prediction placeholder
    prediction = True

    # Send to anomaly handler
    await handle_anomaly({
        "is_anomaly": prediction,
        "event_type": "transaction",
        "event_data": txn.dict()
    }, db)

    return {
        "message": "Transaction processed",
        "is_anomaly": prediction,
        "data": txn
    }

from fastapi import APIRouter, Depends, Request
from app.db.mongodb import get_database
from app.schemas.transaction_schema import TransactionCreate
from app.db.models.transaction_model import TransactionModel
from app.utils.geoip_utils import get_location_from_ip
from app.utils.ip_utils import get_client_ip
from datetime import datetime

router = APIRouter(prefix="/transactions", tags=["Transactions"])

@router.post("/")
async def create_transaction(request: Request, data: TransactionCreate, db=Depends(get_database)):

    user_id = "12345"   # You will replace later after JWT auth

    # 1) Get IP → Location
    client_ip = get_client_ip(request)
    location = get_location_from_ip(client_ip)

    # 2) Fetch previous transaction
    last_txn = await db.transactions.find_one({"user_id": user_id}, sort=[("_id", -1)])

    previous_txn_date = last_txn["transaction_date"] if last_txn else None

    # 3) Auto calculate transaction duration
    transaction_duration = (
        (datetime.utcnow() - previous_txn_date).total_seconds()
        if previous_txn_date else None
    )

    # 4) Auto-generate merchant ID
    merchant_id = f"M-{client_ip.replace('.', '')}"

    # 5) Create transaction object
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

    # 6) Save into MongoDB
    result = await db.transactions.insert_one(txn.dict())

    return {
        "message": "Transaction stored successfully",
        "transaction_id": str(result.inserted_id),
        "data": txn
    }
